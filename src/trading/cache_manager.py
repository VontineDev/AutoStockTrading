"""
백테스팅 결과 캐싱 시스템
우선순위 2: 캐싱 시스템 구축
"""

import sqlite3
import json
import hashlib
import pickle
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """캐시 설정"""

    db_path: str = "data/backtest_cache.db"
    max_age_hours: int = 24  # 24시간 후 만료
    max_cache_size_mb: int = 500  # 500MB 최대 캐시 크기
    cleanup_interval_hours: int = 6  # 6시간마다 정리
    enable_memory_cache: bool = True
    memory_cache_size: int = 1000  # 메모리 캐시 최대 항목 수


class BacktestCacheManager:
    """백테스팅 결과 캐싱 관리자"""

    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.db_path = Path(self.config.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 메모리 캐시 (LRU 방식)
        self.memory_cache = {}
        self.memory_cache_usage = {}  # 사용 시간 추적
        self.cache_lock = threading.Lock()

        # 성능 통계
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_saves": 0,
            "cache_cleanups": 0,
            "memory_cache_hits": 0,
            "db_cache_hits": 0,
            "total_requests": 0,
        }

        # 데이터베이스 초기화
        self._init_database()

        # 마지막 정리 시간
        self.last_cleanup = time.time()

        logger.info(f"캐시 관리자 초기화: {self.db_path}")

    def _init_database(self):
        """데이터베이스 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 캐시 테이블 생성
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS backtest_cache (
                        cache_key TEXT PRIMARY KEY,
                        strategy_name TEXT,
                        symbol TEXT,
                        data_hash TEXT,
                        strategy_params TEXT,
                        backtest_config TEXT,
                        results TEXT,
                        created_at TIMESTAMP,
                        last_accessed TIMESTAMP,
                        access_count INTEGER DEFAULT 0,
                        data_size INTEGER
                    )
                """
                )

                # 인덱스 생성
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_strategy_symbol
                    ON backtest_cache(strategy_name, symbol)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_created_at
                    ON backtest_cache(created_at)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_last_accessed
                    ON backtest_cache(last_accessed)
                """
                )

                conn.commit()
                logger.info("캐시 데이터베이스 초기화 완료")

        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    def generate_cache_key(
        self,
        strategy_name: str,
        symbol: str,
        data_hash: str,
        strategy_params: Dict = None,
        backtest_config: Dict = None,
    ) -> str:
        """캐시 키 생성"""
        key_data = {
            "strategy": strategy_name,
            "symbol": symbol,
            "data_hash": data_hash,
            "strategy_params": strategy_params or {},
            "backtest_config": backtest_config or {},
        }

        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_data_hash(self, data: pd.DataFrame) -> str:
        """데이터의 해시값 계산"""
        # 데이터의 크기와 첫/마지막 몇 행의 해시를 조합
        data_info = {
            "shape": data.shape,
            "columns": list(data.columns),
            "head_hash": hashlib.md5(data.head().to_string().encode()).hexdigest(),
            "tail_hash": hashlib.md5(data.tail().to_string().encode()).hexdigest(),
        }

        if len(data) > 10:
            # 중간 부분도 샘플링
            mid_data = data.iloc[len(data) // 2 : len(data) // 2 + 5]
            data_info["mid_hash"] = hashlib.md5(
                mid_data.to_string().encode()
            ).hexdigest()

        return hashlib.md5(json.dumps(data_info, sort_keys=True).encode()).hexdigest()

    def get_cached_result(
        self,
        strategy_name: str,
        symbol: str,
        data: pd.DataFrame,
        strategy_params: Dict = None,
        backtest_config: Dict = None,
    ) -> Optional[Dict[str, Any]]:
        """캐시된 결과 조회"""
        self.stats["total_requests"] += 1

        try:
            # 캐시 키 생성
            data_hash = self.get_data_hash(data)
            cache_key = self.generate_cache_key(
                strategy_name, symbol, data_hash, strategy_params, backtest_config
            )

            # 메모리 캐시 먼저 확인
            if self.config.enable_memory_cache:
                with self.cache_lock:
                    if cache_key in self.memory_cache:
                        self.memory_cache_usage[cache_key] = time.time()
                        self.stats["memory_cache_hits"] += 1
                        self.stats["cache_hits"] += 1
                        logger.debug(f"메모리 캐시 히트: {symbol}")
                        return self.memory_cache[cache_key]

            # 데이터베이스 캐시 확인
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 캐시 조회
                cursor.execute(
                    """
                    SELECT results, created_at, last_accessed, access_count
                    FROM backtest_cache
                    WHERE cache_key = ?
                """,
                    (cache_key,),
                )

                result = cursor.fetchone()

                if result:
                    results_json, created_at, last_accessed, access_count = result

                    # 만료 시간 확인
                    created_time = datetime.fromisoformat(created_at)
                    max_age = timedelta(hours=self.config.max_age_hours)

                    if datetime.now() - created_time < max_age:
                        # 캐시 히트
                        cached_results = json.loads(results_json)

                        # 액세스 정보 업데이트
                        cursor.execute(
                            """
                            UPDATE backtest_cache
                            SET last_accessed = ?, access_count = access_count + 1
                            WHERE cache_key = ?
                        """,
                            (datetime.now().isoformat(), cache_key),
                        )

                        conn.commit()

                        # 메모리 캐시에도 저장
                        if self.config.enable_memory_cache:
                            self._add_to_memory_cache(cache_key, cached_results)

                        self.stats["db_cache_hits"] += 1
                        self.stats["cache_hits"] += 1
                        logger.debug(f"DB 캐시 히트: {symbol}")
                        return cached_results
                    else:
                        # 만료된 캐시 삭제
                        cursor.execute(
                            "DELETE FROM backtest_cache WHERE cache_key = ?",
                            (cache_key,),
                        )

                        conn.commit()
                        logger.debug(f"만료된 캐시 삭제: {symbol}")

            # 캐시 미스
            self.stats["cache_misses"] += 1
            return None

        except Exception as e:
            logger.error(f"캐시 조회 실패: {e}")
            self.stats["cache_misses"] += 1
            return None

    def save_result(
        self,
        strategy_name: str,
        symbol: str,
        data: pd.DataFrame,
        results: Dict[str, Any],
        strategy_params: Dict = None,
        backtest_config: Dict = None,
    ):
        """결과를 캐시에 저장"""
        try:
            # 캐시 키 생성
            data_hash = self.get_data_hash(data)
            cache_key = self.generate_cache_key(
                strategy_name, symbol, data_hash, strategy_params, backtest_config
            )

            # 결과 직렬화
            results_json = json.dumps(results, default=str)
            data_size = len(results_json.encode())

            # 데이터베이스에 저장
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO backtest_cache
                    (cache_key, strategy_name, symbol, data_hash, strategy_params,
                     backtest_config, results, created_at, last_accessed, access_count, data_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        cache_key,
                        strategy_name,
                        symbol,
                        data_hash,
                        json.dumps(strategy_params or {}),
                        json.dumps(backtest_config or {}),
                        results_json,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        0,
                        data_size,
                    ),
                )

                conn.commit()

            # 메모리 캐시에도 저장
            if self.config.enable_memory_cache:
                self._add_to_memory_cache(cache_key, results)

            self.stats["cache_saves"] += 1
            logger.debug(f"캐시 저장 완료: {symbol}")

            # 주기적 정리
            self._periodic_cleanup()

        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")

    def _add_to_memory_cache(self, cache_key: str, results: Dict[str, Any]):
        """메모리 캐시에 추가"""
        with self.cache_lock:
            # 메모리 캐시 크기 제한
            while len(self.memory_cache) >= self.config.memory_cache_size:
                # 가장 오래된 항목 제거 (LRU)
                oldest_key = min(
                    self.memory_cache_usage.keys(),
                    key=lambda k: self.memory_cache_usage[k],
                )
                del self.memory_cache[oldest_key]
                del self.memory_cache_usage[oldest_key]

            self.memory_cache[cache_key] = results
            self.memory_cache_usage[cache_key] = time.time()

    def _periodic_cleanup(self):
        """주기적 캐시 정리"""
        current_time = time.time()

        if current_time - self.last_cleanup > self.config.cleanup_interval_hours * 3600:
            self.cleanup_cache()
            self.last_cleanup = current_time

    def cleanup_cache(self):
        """캐시 정리"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 만료된 캐시 삭제
                cutoff_time = datetime.now() - timedelta(
                    hours=self.config.max_age_hours
                )
                cursor.execute(
                    """
                    DELETE FROM backtest_cache
                    WHERE created_at < ?
                """,
                    (cutoff_time.isoformat(),),
                )

                deleted_count = cursor.rowcount

                # 캐시 크기 제한 확인
                cursor.execute("SELECT SUM(data_size) FROM backtest_cache")
                total_size = cursor.fetchone()[0] or 0

                max_size_bytes = self.config.max_cache_size_mb * 1024 * 1024

                if total_size > max_size_bytes:
                    # 오래된 항목부터 삭제
                    cursor.execute(
                        """
                        DELETE FROM backtest_cache
                        WHERE cache_key IN (
                            SELECT cache_key FROM backtest_cache
                            ORDER BY last_accessed ASC
                            LIMIT ?
                        )
                    """,
                        (deleted_count // 2,),
                    )

                    deleted_count += cursor.rowcount

                conn.commit()

                self.stats["cache_cleanups"] += 1
                logger.info(f"캐시 정리 완료: {deleted_count}개 항목 삭제")

        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 데이터베이스 통계
                cursor.execute("SELECT COUNT(*) FROM backtest_cache")
                total_cached = cursor.fetchone()[0]

                cursor.execute("SELECT SUM(data_size) FROM backtest_cache")
                total_size = cursor.fetchone()[0] or 0

                cursor.execute("SELECT AVG(access_count) FROM backtest_cache")
                avg_access = cursor.fetchone()[0] or 0

                # 전략별 통계
                cursor.execute(
                    """
                    SELECT strategy_name, COUNT(*) as count
                    FROM backtest_cache
                    GROUP BY strategy_name
                    ORDER BY count DESC
                """
                )
                strategy_stats = cursor.fetchall()

            stats = self.stats.copy()
            stats.update(
                {
                    "total_cached_items": total_cached,
                    "total_cache_size_mb": total_size / (1024 * 1024),
                    "avg_access_count": avg_access,
                    "memory_cache_items": len(self.memory_cache),
                    "strategy_breakdown": dict(strategy_stats),
                }
            )

            # 히트율 계산
            if stats["total_requests"] > 0:
                stats["hit_rate"] = (
                    stats["cache_hits"] / stats["total_requests"]
                ) * 100
                stats["miss_rate"] = (
                    stats["cache_misses"] / stats["total_requests"]
                ) * 100

            return stats

        except Exception as e:
            logger.error(f"캐시 통계 조회 실패: {e}")
            return self.stats.copy()

    def clear_cache(self, strategy_name: str = None, symbol: str = None):
        """캐시 삭제"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if strategy_name and symbol:
                    cursor.execute(
                        """
                        DELETE FROM backtest_cache
                        WHERE strategy_name = ? AND symbol = ?
                    """,
                        (strategy_name, symbol),
                    )
                elif strategy_name:
                    cursor.execute(
                        """
                        DELETE FROM backtest_cache
                        WHERE strategy_name = ?
                    """,
                        (strategy_name,),
                    )
                elif symbol:
                    cursor.execute(
                        """
                        DELETE FROM backtest_cache
                        WHERE symbol = ?
                    """,
                        (symbol,),
                    )
                else:
                    cursor.execute("DELETE FROM backtest_cache")

                deleted_count = cursor.rowcount
                conn.commit()

                # 메모리 캐시도 정리
                if not strategy_name and not symbol:
                    with self.cache_lock:
                        self.memory_cache.clear()
                        self.memory_cache_usage.clear()

                logger.info(f"캐시 삭제 완료: {deleted_count}개 항목")

        except Exception as e:
            logger.error(f"캐시 삭제 실패: {e}")

    @contextmanager
    def cached_backtest(
        self,
        strategy_name: str,
        symbol: str,
        data: pd.DataFrame,
        strategy_params: Dict = None,
        backtest_config: Dict = None,
    ):
        """캐시된 백테스팅 컨텍스트 매니저"""

        # 캐시 조회
        cached_result = self.get_cached_result(
            strategy_name, symbol, data, strategy_params, backtest_config
        )

        if cached_result:
            yield cached_result
        else:
            # 캐시 미스 시 새로운 결과 저장을 위한 플레이스홀더
            result_container = {"result": None}

            def save_result_callback(result):
                result_container["result"] = result
                self.save_result(
                    strategy_name,
                    symbol,
                    data,
                    result,
                    strategy_params,
                    backtest_config,
                )

            yield save_result_callback


# 전역 캐시 관리자 인스턴스
_cache_manager = None


def get_cache_manager(config: CacheConfig = None) -> BacktestCacheManager:
    """캐시 관리자 싱글톤 인스턴스 반환"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = BacktestCacheManager(config)
    return _cache_manager


def clear_global_cache():
    """전역 캐시 관리자 초기화"""
    global _cache_manager
    if _cache_manager:
        _cache_manager.clear_cache()
        _cache_manager = None
