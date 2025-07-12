"""
데이터 업데이트 최적화 엔진
백테스팅 최적화 구조를 참고한 데이터 업데이트 전용 최적화 시스템

최적화 전략:
1. 중복 업데이트 방지 (캐싱)
2. 증분 업데이트 (누락 날짜만)
3. 배치 API 호출 최적화
4. 메모리 관리 및 진행률 모니터링
"""

import time
import logging
import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
from pathlib import Path
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import psutil
import gc
import sys

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# pykrx import
try:
    from pykrx import stock
except ImportError:
    print("pykrx가 설치되지 않았습니다. 'pip install pykrx'로 설치해주세요.")
    sys.exit(1)

logger = logging.getLogger(__name__)

@dataclass
class OptimizedDataUpdateConfig:
    """최적화된 데이터 업데이트 설정"""
    # 병렬 처리 설정
    max_workers: int = 4
    chunk_size: int = 20
    timeout: int = 300
    
    # 캐싱 설정
    enable_cache: bool = True
    cache_expiry_hours: int = 6  # 캐시 만료 시간
    check_latest_data: bool = True  # 최신 데이터 체크
    
    # 배치 처리 설정
    batch_size: int = 30
    max_memory_usage_mb: int = 512
    adaptive_batch_size: bool = True
    
    # API 최적화 설정
    api_delay: float = 0.3  # API 호출 간격
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 증분 업데이트 설정
    incremental_update: bool = True
    skip_existing: bool = True
    force_update_days: int = 3  # 최근 N일은 강제 업데이트
    
    # 진행률 콜백
    progress_callback: Optional[Callable] = None

class DataUpdateCacheManager:
    """데이터 업데이트 캐싱 매니저"""
    
def __init__(self, db_path: str, config: OptimizedDataUpdateConfig):
        self.db_path = db_path
        self.config = config
        self.memory_cache = {}  # 메모리 캐시
        self.cache_lock = threading.Lock()
        
        # 캐시 통계
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'skipped_updates': 0,
            'incremental_updates': 0,
            'full_updates': 0
        }
        
        logger.info("데이터 업데이트 캐시 매니저 초기화")
    
def get_symbol_update_status(self, symbol: str) -> Dict[str, Any]:
        """종목의 업데이트 상태 확인"""
        with self.cache_lock:
            # 메모리 캐시 확인
            cache_key = f"status_{symbol}"
            if cache_key in self.memory_cache:
                cached_time, status = self.memory_cache[cache_key]
                if (datetime.now() - cached_time).seconds < self.config.cache_expiry_hours * 3600:
                    self.cache_stats['hits'] += 1
                    return status
            
            # DB에서 상태 조회
            status = self._query_symbol_status_from_db(symbol)
            
            # 캐시에 저장
            self.memory_cache[cache_key] = (datetime.now(), status)
            self.cache_stats['misses'] += 1
            
            return status
    
def _query_symbol_status_from_db(self, symbol: str) -> Dict[str, Any]:
        """DB에서 종목 상태 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 최신 업데이트 날짜 조회
                cursor = conn.execute('''
                    SELECT date, updated_at 
                    FROM stock_data 
                    WHERE symbol = ? 
                    ORDER BY date DESC 
                    LIMIT 1
                ''', (symbol,))
                result = cursor.fetchone()
                
                if result:
                    latest_date, updated_at = result
                    
                    # 데이터 개수 조회
                    cursor = conn.execute('''
                        SELECT COUNT(*) 
                        FROM stock_data 
                        WHERE symbol = ?
                    ''', (symbol,))
                    data_count = cursor.fetchone()[0]
                    
                    return {
                        'has_data': True,
                        'latest_date': latest_date,
                        'updated_at': updated_at,
                        'data_count': data_count,
                        'needs_update': self._needs_update(latest_date, updated_at)
                    }
                else:
                    return {
                        'has_data': False,
                        'latest_date': None,
                        'updated_at': None,
                        'data_count': 0,
                        'needs_update': True
                    }
        except Exception as e:
            logger.error(f"종목 상태 조회 실패 ({symbol}): {e}")
            return {'has_data': False, 'needs_update': True}
    
def _needs_update(self, latest_date: str, updated_at: str) -> bool:
        """업데이트 필요 여부 판단"""
        if not latest_date or not updated_at:
            return True
        
        try:
            # 최신 데이터 날짜가 오늘 또는 어제면 업데이트 불필요
            latest_dt = datetime.strptime(latest_date, '%Y-%m-%d').date()
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # 주말 고려 (금요일 데이터가 있으면 OK)
            if today.weekday() in [5, 6]:  # 토, 일
                # 최근 3일 내 데이터가 있으면 업데이트 불필요
                threshold_date = today - timedelta(days=3)
            else:
                # 평일은 어제 데이터가 있으면 OK
                threshold_date = yesterday
            
            return latest_dt < threshold_date
            
        except Exception as e:
            logger.error(f"업데이트 필요 여부 판단 실패: {e}")
            return True
    
def get_missing_date_ranges(self, symbol: str, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """누락된 날짜 범위 조회 (증분 업데이트용)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 기존 데이터 날짜들 조회
                cursor = conn.execute('''
                    SELECT date 
                    FROM stock_data 
                    WHERE symbol = ? AND date BETWEEN ? AND ?
                    ORDER BY date
                ''', (symbol, start_date, end_date))
                
                existing_dates = set(row[0] for row in cursor.fetchall())
                
                # 전체 날짜 범위 생성 (주말 제외)
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                all_dates = []
                current_date = start_dt
                while current_date <= end_dt:
                    # 주말 제외 (실제로는 거래일 달력을 사용해야 하지만 간단화)
                    if current_date.weekday() < 5:
                        all_dates.append(current_date.strftime('%Y-%m-%d'))
                    current_date += timedelta(days=1)
                
                # 누락된 날짜들 찾기
                missing_dates = sorted(set(all_dates) - existing_dates)
                
                # 연속된 날짜들을 범위로 그룹화
                if not missing_dates:
                    return []
                
                ranges = []
                start_range = missing_dates[0]
                end_range = missing_dates[0]
                
                for i in range(1, len(missing_dates)):
                    current_dt = datetime.strptime(missing_dates[i], '%Y-%m-%d').date()
                    prev_dt = datetime.strptime(missing_dates[i-1], '%Y-%m-%d').date()
                    
                    if (current_dt - prev_dt).days <= 3:  # 연속으로 간주 (주말 포함)
                        end_range = missing_dates[i]
                    else:
                        ranges.append((start_range, end_range))
                        start_range = missing_dates[i]
                        end_range = missing_dates[i]
                
                ranges.append((start_range, end_range))
                return ranges
                
        except Exception as e:
            logger.error(f"누락 날짜 범위 조회 실패 ({symbol}): {e}")
            return [(start_date, end_date)]  # 실패 시 전체 범위 반환
    
def should_skip_symbol(self, symbol: str) -> bool:
        """종목 업데이트 건너뛰기 여부"""
        if not self.config.skip_existing:
            return False
        
        status = self.get_symbol_update_status(symbol)
        
        if not status['needs_update']:
            self.cache_stats['skipped_updates'] += 1
            return True
        
        return False
    
def invalidate_cache(self, symbol: str = None):
        """캐시 무효화"""
        with self.cache_lock:
            if symbol:
                cache_key = f"status_{symbol}"
                self.memory_cache.pop(cache_key, None)
            else:
                self.memory_cache.clear()
    
def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'cache_size': len(self.memory_cache)
        }

class DataUpdateBatchProcessor:
    """데이터 업데이트 배치 프로세서"""
    
def __init__(self, config: OptimizedDataUpdateConfig):
        self.config = config
        self.current_batch_size = config.batch_size
        self.memory_monitor = self._init_memory_monitor()
        
        # 성능 통계
        self.stats = {
            'total_batches': 0,
            'total_symbols': 0,
            'total_time': 0,
            'api_calls': 0,
            'memory_optimizations': 0,
            'batch_size_changes': 0,
            'avg_symbols_per_second': 0
        }
        
        logger.info(f"배치 프로세서 초기화: 배치 크기 {self.current_batch_size}")
    
def _init_memory_monitor(self):
        """메모리 모니터 초기화"""
        return {
            'process': psutil.Process(),
            'max_memory_mb': self.config.max_memory_usage_mb,
            'peak_memory_mb': 0,
            'gc_count': 0
        }
    
def create_optimized_batches(self, symbols: List[str]) -> List[List[str]]:
        """최적화된 배치 생성"""
        # 메모리 사용량에 따른 배치 크기 조정
        current_memory_mb = self.memory_monitor['process'].memory_info().rss / (1024 * 1024)
        memory_ratio = current_memory_mb / self.config.max_memory_usage_mb
        
        if memory_ratio > 0.8:
            # 메모리 부족 시 배치 크기 감소
            self.current_batch_size = max(10, int(self.current_batch_size * 0.8))
            self.stats['batch_size_changes'] += 1
            logger.info(f"메모리 부족으로 배치 크기 조정: {self.current_batch_size}")
        
        # 배치 생성
        batches = []
        for i in range(0, len(symbols), self.current_batch_size):
            batch = symbols[i:i + self.current_batch_size]
            batches.append(batch)
        
        logger.info(f"배치 생성 완료: {len(batches)}개 배치, 배치 크기: {self.current_batch_size}")
        return batches
    
def process_batch_with_monitoring(self, 
                                    batch: List[str],
                                    processor_func: Callable,
                                    **kwargs) -> Dict[str, Any]:
        """모니터링을 포함한 배치 처리"""
        batch_start_time = time.time()
        
        # 메모리 최적화
        self._optimize_memory()
        
        # 배치 처리 실행
        try:
            results = processor_func(batch, **kwargs)
            success_count = sum(1 for result in results.values() if result)
            success_rate = success_count / len(batch) if batch else 0
        except Exception as e:
            logger.error(f"배치 처리 실패: {e}")
            results = {symbol: False for symbol in batch}
            success_rate = 0
        
        # 성능 통계 업데이트
        batch_time = time.time() - batch_start_time
        self.stats['total_batches'] += 1
        self.stats['total_symbols'] += len(batch)
        self.stats['total_time'] += batch_time
        self.stats['api_calls'] += len(batch)
        
        if self.stats['total_time'] > 0:
            self.stats['avg_symbols_per_second'] = self.stats['total_symbols'] / self.stats['total_time']
        
        logger.info(f"배치 처리 완료: {len(batch)}개 종목, {batch_time:.2f}초, 성공률: {success_rate:.1%}")
        
        return {
            'results': results,
            'batch_time': batch_time,
            'success_rate': success_rate,
            'symbols_processed': len(batch)
        }
    
def _optimize_memory(self):
        """메모리 최적화"""
        current_memory_mb = self.memory_monitor['process'].memory_info().rss / (1024 * 1024)
        
        # 피크 메모리 업데이트
        if current_memory_mb > self.memory_monitor['peak_memory_mb']:
            self.memory_monitor['peak_memory_mb'] = current_memory_mb
        
        # 메모리 임계값 초과 시 가비지 컬렉션
        if current_memory_mb > self.config.max_memory_usage_mb * 0.8:
            gc.collect()
            self.memory_monitor['gc_count'] += 1
            self.stats['memory_optimizations'] += 1
            
            new_memory_mb = self.memory_monitor['process'].memory_info().rss / (1024 * 1024)
            logger.info(f"메모리 최적화: {current_memory_mb:.1f}MB -> {new_memory_mb:.1f}MB")
    
def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        return {
            **self.stats,
            'current_batch_size': self.current_batch_size,
            'peak_memory_mb': self.memory_monitor['peak_memory_mb'],
            'gc_count': self.memory_monitor['gc_count']
        }

class OptimizedDataUpdater:
    """최적화된 데이터 업데이터 메인 엔진"""
    
def __init__(self, db_path: str, config: OptimizedDataUpdateConfig = None):
        self.db_path = db_path
        self.config = config or OptimizedDataUpdateConfig()
        
        # 최적화 컴포넌트 초기화
        self.cache_manager = DataUpdateCacheManager(db_path, self.config)
        self.batch_processor = DataUpdateBatchProcessor(self.config)
        
        # 진행률 추적
        self.progress_lock = threading.Lock()
        self.progress_stats = {
            'total_symbols': 0,
            'completed_symbols': 0,
            'skipped_symbols': 0,
            'failed_symbols': 0,
            'start_time': None
        }
        
        # 전체 성능 통계
        self.performance_stats = {
            'optimization_enabled': {
                'caching': self.config.enable_cache,
                'incremental_update': self.config.incremental_update,
                'parallel_processing': True,
                'batch_optimization': True
            },
            'total_runs': 0,
            'total_time': 0,
            'total_symbols_processed': 0,
            'optimization_efficiency': 0
        }
        
        logger.info("최적화된 데이터 업데이터 초기화 완료")
    
def update_symbols_optimized(self,
                               symbols: List[str],
                               start_date: str = None,
                               end_date: str = None,
                               force_update: bool = False) -> Dict[str, Any]:
        """최적화된 심볼 업데이트"""
        
        start_time = time.time()
        logger.info(f"최적화된 데이터 업데이트 시작: {len(symbols)}개 종목")
        
        # 진행률 초기화
        self.progress_stats.update({
            'total_symbols': len(symbols),
            'completed_symbols': 0,
            'skipped_symbols': 0,
            'failed_symbols': 0,
            'start_time': start_time
        })
        
        # 1. 캐시 기반 필터링 (건너뛸 종목 확인)
        symbols_to_process = self._filter_symbols_by_cache(symbols, force_update)
        
        logger.info(f"캐시 필터링 완료: {len(symbols_to_process)}개 처리 대상 "
                   f"(건너뛴 종목: {len(symbols) - len(symbols_to_process)}개)")
        
        # 2. 배치 생성 및 병렬 처리
        if symbols_to_process:
            batches = self.batch_processor.create_optimized_batches(symbols_to_process)
            parallel_results = self._process_batches_parallel(batches, start_date, end_date, force_update)
        else:
            parallel_results = {'results': {}, 'batch_stats': []}
        
        # 3. 성능 분석
        total_time = time.time() - start_time
        performance_analysis = self._analyze_performance(parallel_results, total_time, len(symbols))
        
        # 4. 통계 업데이트
        self._update_performance_stats(len(symbols), total_time, performance_analysis)
        
        logger.info(f"최적화된 데이터 업데이트 완료: {total_time:.2f}초")
        
        return {
            'results': parallel_results['results'],
            'performance_analysis': performance_analysis,
            'cache_stats': self.cache_manager.get_cache_stats(),
            'batch_stats': self.batch_processor.get_performance_stats(),
            'total_time': total_time
        }
    
def _filter_symbols_by_cache(self, symbols: List[str], force_update: bool) -> List[str]:
        """캐시 기반 종목 필터링"""
        if force_update or not self.config.enable_cache:
            return symbols
        
        symbols_to_process = []
        
        for symbol in symbols:
            if not self.cache_manager.should_skip_symbol(symbol):
                symbols_to_process.append(symbol)
            else:
                with self.progress_lock:
                    self.progress_stats['skipped_symbols'] += 1
                    
                # 진행률 콜백 호출
                if self.config.progress_callback:
                    self._call_progress_callback()
        
        return symbols_to_process
    
def _process_batches_parallel(self, 
                                batches: List[List[str]], 
                                start_date: str, 
                                end_date: str,
                                force_update: bool) -> Dict[str, Any]:
        """배치들을 병렬로 처리"""
        
        all_results = {}
        batch_stats = []
        
def process_single_batch(batch: List[str]) -> Dict[str, Any]:
            """단일 배치 처리"""
            return self.batch_processor.process_batch_with_monitoring(
                batch,
                self._update_batch_sequential,
                start_date=start_date,
                end_date=end_date,
                force_update=force_update
            )
        
        # 병렬 배치 처리
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_batch = {
                executor.submit(process_single_batch, batch): i 
                for i, batch in enumerate(batches)
            }
            
            for future in as_completed(future_to_batch, timeout=self.config.timeout):
                try:
                    batch_result = future.result()
                    all_results.update(batch_result['results'])
                    batch_stats.append(batch_result)
                    
                except Exception as e:
                    batch_idx = future_to_batch[future]
                    logger.error(f"배치 {batch_idx} 처리 실패: {e}")
        
        return {
            'results': all_results,
            'batch_stats': batch_stats
        }
    
def _update_batch_sequential(self, 
                               batch: List[str],
                               start_date: str = None,
                               end_date: str = None,
                               force_update: bool = False) -> Dict[str, bool]:
        """배치를 순차적으로 업데이트 (API 호출 제한 고려)"""
        
        results = {}
        
        for symbol in batch:
            try:
                # API 호출 간격 준수
                time.sleep(self.config.api_delay)
                
                # 개별 종목 업데이트
                success = self._update_single_symbol_optimized(symbol, start_date, end_date, force_update)
                results[symbol] = success
                
                # 진행률 업데이트
                with self.progress_lock:
                    if success:
                        self.progress_stats['completed_symbols'] += 1
                    else:
                        self.progress_stats['failed_symbols'] += 1
                    
                    # 진행률 콜백 호출
                    if self.config.progress_callback:
                        self._call_progress_callback()
                
            except Exception as e:
                logger.error(f"종목 {symbol} 업데이트 실패: {e}")
                results[symbol] = False
                
                with self.progress_lock:
                    self.progress_stats['failed_symbols'] += 1
        
        return results
    
def _update_single_symbol_optimized(self, 
                                      symbol: str, 
                                      start_date: str = None, 
                                      end_date: str = None,
                                      force_update: bool = False) -> bool:
        """최적화된 단일 종목 업데이트"""
        
        try:
            # 증분 업데이트 사용 여부 확인
            if self.config.incremental_update and not force_update:
                missing_ranges = self.cache_manager.get_missing_date_ranges(symbol, start_date, end_date)
                
                if not missing_ranges:
                    logger.debug(f"종목 {symbol}: 업데이트 불필요")
                    return True
                
                # 누락된 범위만 업데이트
                for range_start, range_end in missing_ranges:
                    if not self._fetch_and_save_data(symbol, range_start, range_end):
                        return False
                
                self.cache_manager.cache_stats['incremental_updates'] += 1
            else:
                # 전체 업데이트
                if not self._fetch_and_save_data(symbol, start_date, end_date):
                    return False
                
                self.cache_manager.cache_stats['full_updates'] += 1
            
            # 캐시 무효화
            self.cache_manager.invalidate_cache(symbol)
            return True
            
        except Exception as e:
            logger.error(f"종목 {symbol} 최적화 업데이트 실패: {e}")
            return False
    
def _fetch_and_save_data(self, symbol: str, start_date: str, end_date: str) -> bool:
        """데이터 조회 및 저장"""
        try:
            # pykrx로 데이터 조회
            df = stock.get_market_ohlcv_by_date(start_date, end_date, symbol)
            
            if df.empty:
                logger.warning(f"종목 {symbol}: 데이터 없음 ({start_date}~{end_date})")
                return False
            
            # 데이터베이스에 저장
            self._save_data_to_db(symbol, df)
            return True
            
        except Exception as e:
            logger.error(f"데이터 조회/저장 실패 ({symbol}): {e}")
            return False
    
def _save_data_to_db(self, symbol: str, df: pd.DataFrame):
        """데이터베이스에 데이터 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 데이터 변환
                df_to_save = df.copy()
                df_to_save['symbol'] = symbol
                df_to_save['date'] = df_to_save.index.strftime('%Y-%m-%d')
                df_to_save = df_to_save.reset_index(drop=True)
                
                # 컬럼명 매핑 (pykrx -> DB)
                column_mapping = {
                    '시가': 'open',
                    '고가': 'high', 
                    '저가': 'low',
                    '종가': 'close',
                    '거래량': 'volume',
                    '거래대금': 'amount'
                }
                df_to_save = df_to_save.rename(columns=column_mapping)
                
                # 필요한 컬럼만 선택
                required_columns = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
                if 'amount' in df_to_save.columns:
                    required_columns.append('amount')
                
                df_final = df_to_save[required_columns]
                
                # 데이터베이스에 저장 (REPLACE 사용으로 중복 처리)
                df_final.to_sql('stock_data', conn, if_exists='append', index=False, method='multi')
                
        except Exception as e:
            logger.error(f"DB 저장 실패 ({symbol}): {e}")
            raise
    
def _call_progress_callback(self):
        """진행률 콜백 호출"""
        total = self.progress_stats['total_symbols']
        completed = (self.progress_stats['completed_symbols'] + 
                    self.progress_stats['skipped_symbols'] + 
                    self.progress_stats['failed_symbols'])
        
        progress = completed / total if total > 0 else 0
        
        self.config.progress_callback(
            progress=progress,
            completed=completed,
            total=total,
            start_time=self.progress_stats['start_time']
        )
    
def _analyze_performance(self, parallel_results: Dict, total_time: float, total_symbols: int) -> Dict[str, Any]:
        """성능 분석"""
        
        cache_stats = self.cache_manager.get_cache_stats()
        batch_stats = self.batch_processor.get_performance_stats()
        
        successful_updates = sum(1 for result in parallel_results['results'].values() if result)
        symbols_per_second = total_symbols / total_time if total_time > 0 else 0
        
        # 최적화 효율성 계산
        cache_efficiency = cache_stats['hit_rate'] if cache_stats['total_requests'] > 0 else 0
        skip_efficiency = cache_stats['skipped_updates'] / total_symbols if total_symbols > 0 else 0
        incremental_efficiency = cache_stats['incremental_updates'] / max(1, cache_stats['incremental_updates'] + cache_stats['full_updates'])
        
        overall_efficiency = (cache_efficiency + skip_efficiency + incremental_efficiency) / 3
        
        return {
            'total_time': total_time,
            'total_symbols': total_symbols,
            'successful_updates': successful_updates,
            'success_rate': successful_updates / total_symbols if total_symbols > 0 else 0,
            'symbols_per_second': symbols_per_second,
            'cache_efficiency': cache_efficiency,
            'skip_efficiency': skip_efficiency,
            'incremental_efficiency': incremental_efficiency,
            'overall_efficiency': overall_efficiency,
            'memory_peak_mb': batch_stats['peak_memory_mb'],
            'api_calls': batch_stats['api_calls']
        }
    
def _update_performance_stats(self, symbols_count: int, total_time: float, performance_analysis: Dict):
        """성능 통계 업데이트"""
        self.performance_stats['total_runs'] += 1
        self.performance_stats['total_time'] += total_time
        self.performance_stats['total_symbols_processed'] += symbols_count
        self.performance_stats['optimization_efficiency'] = performance_analysis['overall_efficiency']
    
def get_optimization_stats(self) -> Dict[str, Any]:
        """최적화 통계 반환"""
        return {
            'performance_stats': self.performance_stats,
            'cache_stats': self.cache_manager.get_cache_stats(),
            'batch_stats': self.batch_processor.get_performance_stats(),
            'progress_stats': self.progress_stats
        }
    
def clear_all_caches(self):
        """모든 캐시 클리어"""
        self.cache_manager.invalidate_cache()
        logger.info("모든 캐시가 클리어되었습니다")

def create_optimized_data_updater(db_path: str,
                                max_workers: int = 4,
                                enable_cache: bool = True,
                                batch_size: int = 30,
                                progress_callback: Callable = None) -> OptimizedDataUpdater:
    """최적화된 데이터 업데이터 생성"""
    
    config = OptimizedDataUpdateConfig(
        max_workers=max_workers,
        enable_cache=enable_cache,
        batch_size=batch_size,
        progress_callback=progress_callback
    )
    
    return OptimizedDataUpdater(db_path, config)

def progress_callback_with_eta(progress: float, completed: int, total: int, start_time: float = None):
    """ETA 포함 진행률 콜백"""
    if start_time:
        elapsed_time = time.time() - start_time
        if progress > 0:
            eta = elapsed_time * (1 - progress) / progress
            eta_str = f", ETA: {eta:.1f}초"
        else:
            eta_str = ""
    else:
        eta_str = ""
    
    print(f"\r📊 진행률: {progress:.1%} ({completed}/{total}){eta_str}", end="", flush=True) 