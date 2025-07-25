# -*- coding: utf-8 -*-
import sys
import os
import sqlite3
import pandas as pd
import yaml
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any
import time
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import psutil
import gc

try:
    from pykrx import stock
except ImportError:
    print("pykrx가 설치되지 않았습니다. 'pip install pykrx'로 설치해주세요.")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.makedirs(PROJECT_ROOT / "logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "data_update.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
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
    cache_expiry_hours: int = 6
    check_latest_data: bool = True
    
    # 배치 처리 설정
    batch_size: int = 30
    max_memory_usage_mb: int = 512
    adaptive_batch_size: bool = True
    
    # API 최적화 설정
    api_delay: float = 0.3
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 증분 업데이트 설정
    incremental_update: bool = True
    skip_existing: bool = True
    force_update_days: int = 3
    
    # 진행률 콜백
    progress_callback: Optional[Callable] = None


class DataUpdateCacheManager:
    """데이터 업데이트 캐싱 관리자"""
    
    def __init__(self, db_path: str, config: OptimizedDataUpdateConfig):
        self.db_path = db_path
        self.config = config
        self.cache_lock = threading.Lock()
        self.cache_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "skipped_symbols": 0,
            "incremental_updates": 0,
            "full_updates": 0,
        }
    
    def should_skip_symbol(self, symbol: str) -> bool:
        """캐시 기반으로 종목 업데이트 건너뛸지 판단"""
        if not self.config.enable_cache:
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT MAX(date) FROM stock_ohlcv WHERE symbol = ?
                    """,
                    (symbol,)
                )
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    return False
                
                last_date = datetime.strptime(result[0], "%Y-%m-%d")
                days_diff = (datetime.now() - last_date).days
                
                # 강제 업데이트 기간 내라면 건너뛰지 않음
                if days_diff <= self.config.force_update_days:
                    return False
                
                # 캐시 만료 시간 확인
                return days_diff * 24 < self.config.cache_expiry_hours
                
        except Exception as e:
            logger.error(f"캐시 확인 실패 ({symbol}): {e}")
            return False
    
    def get_missing_date_ranges(self, symbol: str, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """누락된 날짜 범위 확인"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(
                    """
                    SELECT date FROM stock_ohlcv WHERE symbol = ? 
                    AND date BETWEEN ? AND ? ORDER BY date
                    """,
                    conn,
                    params=[symbol, start_date, end_date]
                )
            
            if df.empty:
                return [(start_date, end_date)]
            
            # 실제 구현에서는 더 정교한 날짜 범위 분석 필요
            return []
            
        except Exception as e:
            logger.error(f"누락 날짜 범위 확인 실패 ({symbol}): {e}")
            return [(start_date, end_date)]
    
    def invalidate_cache(self, symbol: str):
        """캐시 무효화"""
        # 실제 구현에서는 메모리 캐시가 있다면 무효화
        pass
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계 반환"""
        return self.cache_stats.copy()


class DataUpdateBatchProcessor:
    """데이터 업데이트 배치 처리자"""
    
    def __init__(self, config: OptimizedDataUpdateConfig):
        self.config = config
        self.stats = {
            "total_batches": 0,
            "total_symbols": 0,
            "total_time": 0.0,
            "api_calls": 0,
            "avg_symbols_per_second": 0.0,
        }
    
    def create_optimized_batches(self, symbols: List[str]) -> List[List[str]]:
        """최적화된 배치 생성"""
        if self.config.adaptive_batch_size:
            # 메모리 사용량에 따라 배치 크기 조정
            memory_usage = psutil.virtual_memory().percent
            if memory_usage > 80:
                batch_size = max(5, self.config.batch_size // 2)
            else:
                batch_size = self.config.batch_size
        else:
            batch_size = self.config.batch_size
        
        return [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
    
    def process_batch_with_monitoring(
        self, batch: List[str], processor_func: Callable, **kwargs
    ) -> Dict[str, Any]:
        """모니터링을 포함한 배치 처리"""
        batch_start_time = time.time()
        
        # 메모리 최적화
        self._optimize_memory()
        
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
        self.stats["total_batches"] += 1
        self.stats["total_symbols"] += len(batch)
        self.stats["total_time"] += batch_time
        self.stats["api_calls"] += len(batch)
        
        if self.stats["total_time"] > 0:
            self.stats["avg_symbols_per_second"] = (
                self.stats["total_symbols"] / self.stats["total_time"]
            )
        
        logger.info(
            f"배치 처리 완료: {len(batch)}개 종목, {batch_time:.2f}초, 성공률: {success_rate:.1%}"
        )
        
        return {
            "results": results,
            "batch_time": batch_time,
            "success_rate": success_rate,
            "symbols_processed": len(batch),
        }
    
    def _optimize_memory(self):
        """메모리 최적화"""
        gc.collect()
    
    def get_performance_stats(self) -> Dict:
        """성능 통계 반환"""
        return self.stats.copy()


class StockDataUpdater:
    """주식 데이터를 수집, 저장 및 관리하는 클래스 (병렬 처리 지원)."""

    def __init__(self, db_path: Optional[str] = None, config_path: Optional[str] = None,
                 optimization_config: Optional[OptimizedDataUpdateConfig] = None):
        self.db_path = db_path or str(PROJECT_ROOT / "data" / "trading.db")
        self.config_path = config_path or str(PROJECT_ROOT / "config.yaml")
        self.config = self._load_config()
        
        # 최적화 설정 초기화
        self.optimization_config = optimization_config or OptimizedDataUpdateConfig()
        
        # 최적화 컴포넌트 초기화
        self.cache_manager = DataUpdateCacheManager(self.db_path, self.optimization_config)
        self.batch_processor = DataUpdateBatchProcessor(self.optimization_config)
        
        # 진행률 추적
        self.progress_lock = threading.Lock()
        self.progress_stats = {
            "total_symbols": 0,
            "completed_symbols": 0,
            "skipped_symbols": 0,
            "failed_symbols": 0,
            "start_time": None,
        }
        
        self._init_database()

    def _load_config(self) -> Dict:
        """설정 파일(config.yaml)을 로드합니다."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"설정 파일 로드 실패: {e}")
        return {}

    def _init_database(self):
        """통합 스키마를 사용하여 데이터베이스를 초기화합니다."""
        from .database import DatabaseManager
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 통합 스키마 파일 경로
        schema_path = PROJECT_ROOT / "data" / "schema.sql"
        
        if schema_path.exists():
            # DatabaseManager를 사용하여 스키마 초기화
            db_manager = DatabaseManager(self.db_path)
            db_manager.initialize_schema(str(schema_path))
            logger.info("통합 스키마를 사용하여 데이터베이스 초기화 완료")
        else:
            # 스키마 파일이 없는 경우 최소한의 테이블만 생성
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS stock_info (symbol TEXT PRIMARY KEY, name TEXT NOT NULL, market TEXT, sector TEXT, industry TEXT, listing_date TEXT, market_cap INTEGER, updated_at TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS stock_ohlcv (symbol TEXT NOT NULL, date TEXT NOT NULL, open INTEGER, high INTEGER, low INTEGER, close INTEGER, volume INTEGER, PRIMARY KEY (symbol, date))")
                conn.commit()
            logger.warning("스키마 파일을 찾을 수 없어 최소한의 테이블만 생성했습니다.")

    def save_symbol_info(self, symbol_info: Dict):
        """단일 종목의 정보를 `stock_info` 테이블에 저장하거나 업데이트합니다."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO stock_info (symbol, name, market, sector, updated_at) VALUES (?, ?, ?, ?, ?)",
                (symbol_info['symbol'], symbol_info['name'], symbol_info['market'], symbol_info.get('sector', ''), datetime.now().isoformat()),
            )

    def update_all_symbol_info_with_krx(self, kospi_csv: str = "krx_sector_kospi.csv", kosdaq_csv: str = "krx_sector_kosdaq.csv") -> Optional[pd.DataFrame]:
        """전체 상장 종목의 기본 정보를 최신 상태로 업데이트합니다."""
        logger.info("전체 종목 정보 업데이트 시작...")
        today = datetime.now().strftime("%Y%m%d")
        all_tickers = stock.get_market_ticker_list(today, market="ALL")
        kospi_tickers = set(stock.get_market_ticker_list(today, market="KOSPI"))
        
        pykrx_data = []
        for ticker in all_tickers:
            name = stock.get_market_ticker_name(ticker)
            market = "KOSPI" if ticker in kospi_tickers else "KOSDAQ"
            if market == "KOSPI":
                market = "KOSPI"
            elif market == "KOSDAQ":
                market = "KOSDAQ"
            else:
                market = "UNKNOWN"
            pykrx_data.append({"symbol": ticker, "name": name, "market": market})
        df_pykrx = pd.DataFrame(pykrx_data)

        try:
            df_kospi_sector = pd.read_csv(PROJECT_ROOT / kospi_csv, dtype={"종목코드": str}, encoding="cp949")
            df_kosdaq_sector = pd.read_csv(PROJECT_ROOT / kosdaq_csv, dtype={"종목코드": str}, encoding="cp949")
            df_sector = pd.concat([df_kospi_sector, df_kosdaq_sector], ignore_index=True)
            df_sector["종목코드"] = df_sector["종목코드"].str.zfill(6)
            df_merged = pd.merge(df_pykrx, df_sector[["종목코드", "업종명"]], left_on="symbol", right_on="종목코드", how="left")
            df_merged.rename(columns={"업종명": "sector"}, inplace=True)
            df_merged["sector"] = df_merged["sector"].fillna("")
        except FileNotFoundError:
            logger.warning("업종 CSV 파일이 없어 업종 정보 없이 진행합니다.")
            df_merged = df_pykrx
            df_merged['sector'] = ''

        with sqlite3.connect(self.db_path) as conn:
            for _, row in df_merged.iterrows():
                self.save_symbol_info({'symbol': row['symbol'], 'name': row['name'], 'market': row['market'], 'sector': row['sector']})
        logger.info(f"총 {len(df_merged)}개 종목 정보 DB 저장 완료.")
        return df_merged

    def _save_ohlcv_data(self, df: pd.DataFrame, ticker: Optional[str] = None):
        """OHLCV 데이터프레임을 DB에 저장합니다."""
        if df.empty:
            return
        
        # 컬럼명 한글 -> 영어 변환
        df.rename(columns={"시가": "open", "고가": "high", "저가": "low", "종가": "close", "거래량": "volume"}, inplace=True)
        
        # 인덱스가 날짜인지 종목코드인지 확인하여 적절히 처리
        if hasattr(df.index, 'dtype') and pd.api.types.is_datetime64_any_dtype(df.index):
            # 인덱스가 datetime인 경우
            df['date'] = df.index.to_series().dt.strftime('%Y-%m-%d')
        elif isinstance(df.index, pd.DatetimeIndex):
            # DatetimeIndex인 경우
            df['date'] = df.index.to_series().dt.strftime('%Y-%m-%d')
        else:
            # 인덱스가 종목코드인 경우 (일별 전체 시장 데이터)
            df.reset_index(inplace=True)
            
            # 첫 번째 컬럼이 symbol 정보일 가능성이 높음
            first_col = str(df.columns[0])
            if first_col in ['ticker', '티커', 'symbol', 'index']:
                # 첫 번째 컬럼 이름을 명시적으로 가져와서 변경
                old_col = df.columns.tolist()[0]
                df.rename(columns={old_col: 'symbol'}, inplace=True)
            elif 'symbol' not in df.columns:
                # 첫 번째 컬럼을 symbol로 사용
                old_col = df.columns.tolist()[0]
                df.rename(columns={old_col: 'symbol'}, inplace=True)
            
            # 날짜 정보가 없으므로 현재 날짜로 설정 (일별 데이터의 경우)
            current_date = datetime.now().strftime('%Y-%m-%d')
            df['date'] = current_date
        
        # 심볼 정보 추가 처리
        if '티커' in df.columns and 'symbol' not in df.columns:
             df.rename(columns={'티커': 'symbol'}, inplace=True)
        elif ticker and 'symbol' not in df.columns:
            df['symbol'] = ticker
        elif 'symbol' not in df.columns:
            logger.error("OHLCV 데이터 저장 시 티커 정보가 없습니다.")
            return
        
        cols_to_save = ["symbol", "date", "open", "high", "low", "close", "volume"]
        
        # 필요한 컬럼이 모두 있는지 확인
        missing_cols = [col for col in cols_to_save if col not in df.columns]
        if missing_cols:
            logger.error(f"필수 컬럼이 누락되었습니다: {missing_cols}")
            return
        
        with sqlite3.connect(self.db_path) as conn:
            df[cols_to_save].to_sql("stock_ohlcv", conn, if_exists='replace', index=False)

    def update_daily_market_data(self, date_str: str):
        """특정일의 전체 시장 OHLCV 데이터를 업데이트합니다."""
        logger.info(f"일별 전체 시장 데이터 업데이트 시작: {date_str}")
        try:
            df = stock.get_market_ohlcv(date_str, market="ALL")
            self._save_ohlcv_data(df)
        except Exception as e:
            logger.error(f"일별 시장 데이터({date_str}) 업데이트 실패: {e}")

    def update_specific_stock_data(self, ticker: str, start_date: str, end_date: str):
        """특정 종목의 지정된 기간 OHLCV 데이터를 업데이트합니다."""
        logger.info(f"종목({ticker}) 데이터 업데이트: {start_date}~{end_date}")
        try:
            df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
            self._save_ohlcv_data_optimized(ticker, df)
        except Exception as e:
            logger.error(f"종목({ticker}) 데이터 업데이트 실패: {e}")

    def update_all_historical_data(self, start_date: str, end_date: str):
        """전체 종목의 지정된 기간 OHLCV 데이터를 업데이트합니다."""
        logger.info(f"전체 종목 기간 데이터 업데이트 시작: {start_date}~{end_date}")
        with sqlite3.connect(self.db_path) as conn:
            tickers = pd.read_sql_query("SELECT symbol FROM stock_info", conn)['symbol'].tolist()
        
        delay = self.config.get("data_collection", {}).get("api_delay", 0.2)
        for i, ticker in enumerate(tickers, 1):
            logger.info(f"  - ({i}/{len(tickers)}) {ticker} 데이터 수집 중...")
            self.update_specific_stock_data(ticker, start_date, end_date)
            time.sleep(delay)
        logger.info("전체 종목 기간 데이터 업데이트 완료.")

    def update_market_cap_data(self, date_str: Optional[str] = None):
        """특정일의 전체 시장 시가총액 데이터를 업데이트합니다."""
        date_str = date_str or datetime.now().strftime("%Y%m%d")
        logger.info(f"시가총액 데이터 업데이트 시작: {date_str}")
        try:
            df = stock.get_market_cap(date_str, market="ALL")
            df.reset_index(inplace=True)
            df.rename(columns={'티커': 'symbol', '시가총액': 'market_cap'}, inplace=True)
            
            with sqlite3.connect(self.db_path) as conn:
                for _, row in df.iterrows():
                    conn.execute("UPDATE stock_info SET market_cap = ? WHERE symbol = ?", (row['market_cap'], row['symbol']))
                conn.commit()
            logger.info(f"총 {len(df)}개 종목 시가총액 정보 DB 업데이트 완료.")
        except Exception as e:
            logger.error(f"시가총액 데이터({date_str}) 업데이트 실패: {e}")

    # 새로운 병렬 처리 메서드들
    def update_multiple_symbols_parallel(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_update: bool = False,
        max_workers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """최적화된 병렬 심볼 업데이트"""
        if max_workers:
            self.optimization_config.max_workers = max_workers
        
        start_time = time.time()
        logger.info(f"최적화된 병렬 데이터 업데이트 시작: {len(symbols)}개 종목")
        
        # 진행률 초기화
        self.progress_stats.update({
            "total_symbols": len(symbols),
            "completed_symbols": 0,
            "skipped_symbols": 0,
            "failed_symbols": 0,
            "start_time": start_time,
        })
        
        # 캐시 기반 필터링
        symbols_to_process = self._filter_symbols_by_cache(symbols, force_update)
        
        logger.info(
            f"캐시 필터링 완료: {len(symbols_to_process)}개 처리 대상 "
            f"(건너뛴 종목: {len(symbols) - len(symbols_to_process)}개)"
        )
        
        # 병렬 처리
        if symbols_to_process:
            batches = self.batch_processor.create_optimized_batches(symbols_to_process)
            parallel_results = self._process_batches_parallel(
                batches, start_date, end_date, force_update
            )
        else:
            parallel_results = {"results": {}, "batch_stats": []}
        
        # 성능 분석
        total_time = time.time() - start_time
        
        logger.info(f"최적화된 병렬 데이터 업데이트 완료: {total_time:.2f}초")
        
        return {
            "results": parallel_results["results"],
            "cache_stats": self.cache_manager.get_cache_stats(),
            "batch_stats": self.batch_processor.get_performance_stats(),
            "total_time": total_time,
        }

    def _filter_symbols_by_cache(self, symbols: List[str], force_update: bool) -> List[str]:
        """캐시 기반 종목 필터링"""
        if force_update or not self.optimization_config.enable_cache:
            return symbols

        symbols_to_process = []
        for symbol in symbols:
            if not self.cache_manager.should_skip_symbol(symbol):
                symbols_to_process.append(symbol)
            else:
                with self.progress_lock:
                    self.progress_stats["skipped_symbols"] += 1

        return symbols_to_process

    def _process_batches_parallel(
        self, batches: List[List[str]], start_date: Optional[str], end_date: Optional[str], force_update: bool
    ) -> Dict[str, Any]:
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
                force_update=force_update,
            )

        # 병렬 배치 처리
        with ThreadPoolExecutor(max_workers=self.optimization_config.max_workers) as executor:
            future_to_batch = {
                executor.submit(process_single_batch, batch): i
                for i, batch in enumerate(batches)
            }

            for future in as_completed(future_to_batch, timeout=self.optimization_config.timeout):
                try:
                    batch_result = future.result()
                    all_results.update(batch_result["results"])
                    batch_stats.append(batch_result)
                except Exception as e:
                    batch_idx = future_to_batch[future]
                    logger.error(f"배치 {batch_idx} 처리 실패: {e}")

        return {"results": all_results, "batch_stats": batch_stats}

    def _update_batch_sequential(
        self, batch: List[str], start_date: Optional[str] = None, end_date: Optional[str] = None, force_update: bool = False
    ) -> Dict[str, bool]:
        """배치를 순차적으로 업데이트"""
        results = {}

        for symbol in batch:
            try:
                # API 호출 간격 준수
                time.sleep(self.optimization_config.api_delay)

                # 개별 종목 업데이트
                success = self._update_single_symbol_optimized(symbol, start_date, end_date, force_update)
                results[symbol] = success

                # 진행률 업데이트
                with self.progress_lock:
                    if success:
                        self.progress_stats["completed_symbols"] += 1
                    else:
                        self.progress_stats["failed_symbols"] += 1

                    # 진행률 콜백 호출
                    if self.optimization_config.progress_callback is not None:
                        self._call_progress_callback()

            except Exception as e:
                logger.error(f"종목 {symbol} 업데이트 실패: {e}")
                results[symbol] = False

                with self.progress_lock:
                    self.progress_stats["failed_symbols"] += 1

        return results

    def _update_single_symbol_optimized(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None, force_update: bool = False
    ) -> bool:
        """최적화된 단일 종목 업데이트"""
        try:
            # 증분 업데이트 사용 여부 확인
            if self.optimization_config.incremental_update and not force_update and start_date and end_date:
                missing_ranges = self.cache_manager.get_missing_date_ranges(symbol, start_date, end_date)

                if not missing_ranges:
                    logger.debug(f"종목 {symbol}: 업데이트 불필요")
                    return True

                # 누락된 범위만 업데이트
                for range_start, range_end in missing_ranges:
                    if not self._fetch_and_save_data(symbol, range_start, range_end):
                        return False

                self.cache_manager.cache_stats["incremental_updates"] += 1
            else:
                # 전체 업데이트
                if start_date and end_date and not self._fetch_and_save_data(symbol, start_date, end_date):
                    return False

                self.cache_manager.cache_stats["full_updates"] += 1

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
            self._save_ohlcv_data_optimized(symbol, df)
            return True

        except Exception as e:
            logger.error(f"데이터 조회/저장 실패 ({symbol}): {e}")
            return False

    def _save_ohlcv_data_optimized(self, symbol: str, df: pd.DataFrame):
        """최적화된 OHLCV 데이터 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 데이터 변환
                df_to_save = df.copy()
                df_to_save["symbol"] = symbol
                df_to_save["date"] = pd.to_datetime(df_to_save.index).strftime("%Y-%m-%d")
                df_to_save = df_to_save.reset_index(drop=True)

                # 컬럼명 매핑 (pykrx -> DB)
                column_mapping = {
                    "시가": "open",
                    "고가": "high",
                    "저가": "low",
                    "종가": "close",
                    "거래량": "volume",
                    "거래대금": "amount",
                }
                df_to_save = df_to_save.rename(columns=column_mapping)

                # 필요한 컬럼만 선택
                required_columns = ["symbol", "date", "open", "high", "low", "close", "volume"]
                if "amount" in df_to_save.columns:
                    required_columns.append("amount")

                df_final = df_to_save[required_columns]

                # 데이터베이스에 저장
                df_final.to_sql("stock_ohlcv", conn, if_exists="append", index=False, method="multi")

        except Exception as e:
            logger.error(f"DB 저장 실패 ({symbol}): {e}")
            raise

    def _call_progress_callback(self):
        """진행률 콜백 호출"""
        total = self.progress_stats["total_symbols"]
        completed = (
            self.progress_stats["completed_symbols"]
            + self.progress_stats["skipped_symbols"]
            + self.progress_stats["failed_symbols"]
        )

        progress = completed / total if total > 0 else 0

        if self.optimization_config.progress_callback is not None:
            self.optimization_config.progress_callback(
                progress=progress,
                completed=completed,
                total=total,
                start_time=self.progress_stats["start_time"],
            )

    def get_optimization_stats(self) -> Dict[str, Any]:
        """최적화 통계 반환"""
        return {
            "cache_stats": self.cache_manager.get_cache_stats(),
            "batch_stats": self.batch_processor.get_performance_stats(),
            "progress_stats": self.progress_stats.copy(),
            "optimization_config": {
                "max_workers": self.optimization_config.max_workers,
                "enable_cache": self.optimization_config.enable_cache,
                "batch_size": self.optimization_config.batch_size,
                "api_delay": self.optimization_config.api_delay,
            },
        }


def main():
    """테스트 및 직접 실행을 위한 메인 함수"""
    updater = StockDataUpdater()
    # 예시: 전체 종목 정보 업데이트
    # updater.update_all_symbol_info_with_krx()
    
    # 예시: 특정일의 시가총액 정보 업데이트
    updater.update_market_cap_data()

if __name__ == "__main__":
    main()
