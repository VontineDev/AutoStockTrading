"""
최적화된 백테스팅 통합 인터페이스
성능 최적화 1,2,3 통합
"""

import time
import logging
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import pandas as pd
import numpy as np
from dataclasses import dataclass
import sys
from datetime import datetime, timedelta

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / 'src'))

# 상수 임포트
from src.constants import (
    TradingConstants, BacktestConstants, DataCollectionConstants,
    SystemConstants, OptimizationConstants
)

# 최적화 모듈 임포트
from src.trading.parallel_backtest import ParallelBacktestEngine, ParallelBacktestConfig
from src.trading.cache_manager import BacktestCacheManager, CacheConfig, get_cache_manager
from src.trading.batch_optimizer import BatchProcessor, BatchConfig, create_optimized_batch_processor
from scripts.data_update import StockDataUpdater
from src.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

@dataclass
class OptimizedBacktestConfig:
    """최적화된 백테스팅 설정"""
    # 병렬 처리 설정
    max_workers: Optional[int] = None
    chunk_size: int = OptimizationConstants.MIN_SYMBOLS_FOR_PARALLEL
    
    # 캐싱 설정
    enable_cache: bool = True
    cache_max_age_hours: int = SystemConstants.CACHE_TTL_SECONDS // 3600  # 1시간
    cache_max_size_mb: int = SystemConstants.MEMORY_WARNING_THRESHOLD_MB
    
    # 배치 처리 설정
    batch_size: int = DataCollectionConstants.DEFAULT_BATCH_SIZE
    max_memory_usage_mb: int = SystemConstants.MEMORY_WARNING_THRESHOLD_MB * 2  # 1GB
    adaptive_batch_size: bool = True
    
    # 백테스팅 설정
    initial_capital: float = TradingConstants.DEFAULT_INITIAL_CAPITAL
    commission: float = TradingConstants.TRANSACTION_FEE_RATE
    slippage: float = BacktestConstants.SLIPPAGE_RATE
    
    # 진행률 콜백
    progress_callback: Optional[Callable] = None

class OptimizedBacktestEngine:
    """최적화된 백테스팅 엔진"""
    
def __init__(self, config: OptimizedBacktestConfig = None):
        self.config = config or OptimizedBacktestConfig()
        
        # 성능 최적화 컴포넌트 초기화
        self._init_components()
        
        # 성능 통계
        self.performance_stats = {
            'optimization_enabled': {
                'parallel_processing': True,
                'caching': self.config.enable_cache,
                'batch_optimization': True
            },
            'total_runs': 0,
            'total_symbols': 0,
            'total_time': 0,
            'cache_efficiency': 0,
            'parallel_efficiency': 0,
            'memory_efficiency': 0
        }
        
        logger.info("최적화된 백테스팅 엔진 초기화 완료")
    
def _init_components(self):
        """성능 최적화 컴포넌트 초기화"""
        
        # 1. 병렬 처리 초기화
        parallel_config = ParallelBacktestConfig(
            max_workers=self.config.max_workers,
            chunk_size=self.config.chunk_size,
            progress_callback=self.config.progress_callback
        )
        self.parallel_engine = ParallelBacktestEngine(parallel_config)
        
        # 2. 캐싱 시스템 초기화
        if self.config.enable_cache:
            cache_config = CacheConfig(
                max_age_hours=self.config.cache_max_age_hours,
                max_cache_size_mb=self.config.cache_max_size_mb
            )
            self.cache_manager = get_cache_manager(cache_config)
        else:
            self.cache_manager = None
        
        # 3. 배치 처리 최적화 초기화
        batch_config = BatchConfig(
            max_memory_usage_mb=self.config.max_memory_usage_mb,
            batch_size=self.config.batch_size,
            adaptive_batch_size=self.config.adaptive_batch_size
        )
        self.batch_processor = BatchProcessor(batch_config)
        
        # 데이터 업데이터
        self.data_updater = StockDataUpdater()
        
        logger.info("성능 최적화 컴포넌트 초기화 완료")
    
def run_optimized_backtest(self,
                              strategy_class,
                              symbols: List[str],
                              strategy_params: Dict = None,
                              days: int = DataCollectionConstants.DEFAULT_BACKTEST_DAYS) -> Dict[str, Any]:
        """
        최적화된 백테스팅 실행
        
        Args:
            strategy_class: 전략 클래스
            symbols: 백테스팅할 심볼 목록
            strategy_params: 전략 파라미터
            days: 백테스팅 기간 (일)
            
        Returns:
            최적화된 백테스팅 결과
        """
        
        # 입력 검증
        if strategy_class is None:
            raise TypeError("전략 클래스가 None입니다.")
        
        if not hasattr(strategy_class, '__call__'):
            raise AttributeError("전략 클래스가 호출 가능하지 않습니다.")
        
        if days <= 0:
            raise ValueError(f"백테스팅 기간은 양수여야 합니다: {days}")
        
        if not isinstance(symbols, list):
            raise TypeError("심볼은 리스트 형태여야 합니다.")
        
        start_time = time.time()
        logger.info(f"최적화된 백테스팅 시작: {len(symbols)}개 심볼, {days}일")
        
        # 1. 데이터 수집 (배치 최적화 적용)
        symbols_data = self._collect_data_optimized(symbols, days)
        
        # 2. 캐시 확인 및 필터링
        symbols_to_process, cached_results = self._filter_cached_symbols(
            strategy_class, symbols_data, strategy_params
        )
        
        # 3. 병렬 백테스팅 실행
        if symbols_to_process:
            parallel_results = self.parallel_engine.run_parallel_backtest(
                strategy_class, symbols_to_process, strategy_params,
                {
                    'initial_capital': self.config.initial_capital,
                    'commission': self.config.commission,
                    'slippage': self.config.slippage
                }
            )
            
            # 4. 결과 캐싱
            if self.config.enable_cache:
                self._cache_results(strategy_class, parallel_results['results'], 
                                  symbols_to_process, strategy_params)
            
            # 결과 병합
            all_results = {**cached_results, **parallel_results['results']}
            parallel_stats = parallel_results['performance_stats']
        else:
            all_results = cached_results
            parallel_stats = {}
        
        # 5. 성능 분석
        total_time = time.time() - start_time
        performance_analysis = self._analyze_performance(
            all_results, total_time, len(symbols), parallel_stats
        )
        
        # 6. 통계 업데이트
        self._update_stats(len(symbols), total_time, performance_analysis)
        
        logger.info(f"최적화된 백테스팅 완료: {len(all_results)}개 결과, {total_time:.2f}초")
        
        return {
            'results': all_results,
            'performance_analysis': performance_analysis,
            'optimization_stats': self.get_optimization_stats(),
            'total_time': total_time
        }
    
def _collect_data_optimized(self, symbols: List[str], days: int) -> Dict[str, pd.DataFrame]:
        """배치 최적화를 적용한 데이터 수집"""
        
        # StockDataUpdater의 update_symbol 메서드를 사용하여 데이터 수집 및 저장
        # update_symbol은 내부적으로 데이터베이스에 저장하므로 별도의 저장 로직 불필요
        # 여기서는 force_update=False로 설정하여 이미 최신 데이터가 있으면 건너뛰도록 함
        
        # 데이터 수집 및 저장
        results = self.data_updater.update_multiple_symbols_parallel(
            symbols=symbols,
            start_date=(datetime.now() - timedelta(days=days + 30)).strftime('%Y%m%d'), # 백테스팅 기간 + 여유분
            end_date=datetime.now().strftime('%Y%m%d'),
            force_update=False, # 이미 최신 데이터가 있으면 업데이트하지 않음
            max_workers=self.config.max_workers or 5 # 병렬 워커 수
        )

        # 데이터베이스에서 수집된 데이터 로드
        symbols_data = {}
        for symbol, success in results.items():
            if success:
                # StockDataManager를 사용하여 데이터베이스에서 데이터 로드
                # StockDataManager는 db_path를 필요로 함
                from src.data.stock_data_manager import StockDataManager
                dm = StockDataManager(db_path=self.data_updater.db_path)
                df = dm.get_latest_data(symbol, days=days)
                if not df.empty:
                    symbols_data[symbol] = df
                else:
                    logger.warning(f"데이터베이스에서 {symbol} 데이터 로드 실패")
            else:
                logger.warning(f"{symbol} 데이터 수집 실패")

        return symbols_data
    
def _filter_cached_symbols(self, 
                              strategy_class,
                              symbols_data: Dict[str, pd.DataFrame],
                              strategy_params: Dict = None) -> tuple:
        """캐시된 심볼 필터링"""
        
        if not self.config.enable_cache:
            return symbols_data, {}
        
        strategy_name = strategy_class.__name__
        symbols_to_process = {}
        cached_results = {}
        
        for symbol, data in symbols_data.items():
            if data.empty:
                continue
                
            # 캐시 조회
            cached_result = self.cache_manager.get_cached_result(
                strategy_name, symbol, data, strategy_params
            )
            
            if cached_result:
                cached_results[symbol] = cached_result
                logger.debug(f"캐시 히트: {symbol}")
            else:
                symbols_to_process[symbol] = data
        
        cache_hit_rate = len(cached_results) / len(symbols_data) * 100 if symbols_data else 0
        logger.info(f"캐시 히트율: {cache_hit_rate:.1f}% ({len(cached_results)}/{len(symbols_data)})")
        
        return symbols_to_process, cached_results
    
def _cache_results(self,
                      strategy_class,
                      results: Dict[str, Any],
                      symbols_data: Dict[str, pd.DataFrame],
                      strategy_params: Dict = None):
        """결과 캐싱"""
        
        if not self.config.enable_cache:
            return
        
        strategy_name = strategy_class.__name__
        
        for symbol, result in results.items():
            if symbol in symbols_data and result.get('success', False):
                self.cache_manager.save_result(
                    strategy_name, symbol, symbols_data[symbol], 
                    result, strategy_params
                )
    
def _analyze_performance(self, 
                           results: Dict[str, Any],
                           total_time: float,
                           total_symbols: int,
                           parallel_stats: Dict = None) -> Dict[str, Any]:
        """성능 분석"""
        
        successful_results = {k: v for k, v in results.items() if v.get('success', False)}
        
        # 기본 통계
        analysis = {
            'total_symbols': total_symbols,
            'successful_symbols': len(successful_results),
            'failed_symbols': total_symbols - len(successful_results),
            'success_rate': len(successful_results) / total_symbols * 100 if total_symbols > 0 else 0,
            'total_time': total_time,
            'avg_time_per_symbol': total_time / total_symbols if total_symbols > 0 else 0,
            'symbols_per_second': total_symbols / total_time if total_time > 0 else 0
        }
        
        # 백테스팅 결과 통계
        if successful_results:
            returns = [r.get('total_return', 0) for r in successful_results.values()]
            sharpe_ratios = [r.get('sharpe_ratio', 0) for r in successful_results.values()]
            
            analysis['backtest_stats'] = {
                'avg_return': np.mean(returns),
                'median_return': np.median(returns),
                'std_return': np.std(returns),
                'best_return': max(returns),
                'worst_return': min(returns),
                'avg_sharpe': np.mean(sharpe_ratios),
                'positive_returns': sum(1 for r in returns if r > 0),
                'negative_returns': sum(1 for r in returns if r < 0)
            }
        
        # 병렬 처리 통계
        if parallel_stats:
            analysis['parallel_stats'] = parallel_stats
        
        # 캐시 통계
        if self.config.enable_cache:
            analysis['cache_stats'] = self.cache_manager.get_cache_stats()
        
        # 배치 처리 통계
        analysis['batch_stats'] = self.batch_processor.get_performance_report()
        
        return analysis
    
def _update_stats(self, symbols_count: int, total_time: float, performance_analysis: Dict):
        """성능 통계 업데이트"""
        
        self.performance_stats['total_runs'] += 1
        self.performance_stats['total_symbols'] += symbols_count
        self.performance_stats['total_time'] += total_time
        
        # 캐시 효율성
        if self.config.enable_cache and 'cache_stats' in performance_analysis:
            cache_stats = performance_analysis['cache_stats']
            if cache_stats.get('total_requests', 0) > 0:
                self.performance_stats['cache_efficiency'] = cache_stats.get('hit_rate', 0)
        
        # 병렬 처리 효율성
        if 'parallel_stats' in performance_analysis:
            parallel_stats = performance_analysis['parallel_stats']
            if parallel_stats.get('total_symbols', 0) > 0:
                sequential_estimate = parallel_stats.get('avg_time_per_symbol', 0) * symbols_count
                if sequential_estimate > 0:
                    self.performance_stats['parallel_efficiency'] = (
                        sequential_estimate / total_time * 100
                    )
        
        # 메모리 효율성
        if 'batch_stats' in performance_analysis:
            batch_stats = performance_analysis['batch_stats']
            memory_stats = batch_stats.get('memory_monitor', {})
            if memory_stats.get('peak_memory_mb', 0) > 0:
                self.performance_stats['memory_efficiency'] = min(100, (
                    self.config.max_memory_usage_mb / memory_stats['peak_memory_mb'] * 100
                ))
    
def get_optimization_stats(self) -> Dict[str, Any]:
        """최적화 통계 반환"""
        
        stats = self.performance_stats.copy()
        
        # 평균 계산
        if stats['total_runs'] > 0:
            stats['avg_symbols_per_run'] = stats['total_symbols'] / stats['total_runs']
            stats['avg_time_per_run'] = stats['total_time'] / stats['total_runs']
        
        if stats['total_symbols'] > 0:
            stats['avg_time_per_symbol'] = stats['total_time'] / stats['total_symbols']
        
        # 컴포넌트별 상세 통계
        if self.config.enable_cache:
            stats['cache_detailed'] = self.cache_manager.get_cache_stats()
        
        stats['parallel_detailed'] = self.parallel_engine.get_performance_report()
        stats['batch_detailed'] = self.batch_processor.get_performance_report()
        
        return stats
    
def benchmark_optimizations(self, 
                              strategy_class,
                              sample_symbols: List[str],
                              days: int = DataCollectionConstants.DEFAULT_BACKTEST_DAYS) -> Dict[str, Any]:
        """최적화 성능 벤치마크"""
        
        logger.info("최적화 성능 벤치마크 시작")
        
        # 1. 최적화 없이 (순차 처리)
        start_time = time.time()
        
        # 캐싱 비활성화
        original_cache_setting = self.config.enable_cache
        self.config.enable_cache = False
        
        # 병렬 처리 비활성화 (워커 1개)
        original_workers = self.parallel_engine.config.max_workers
        self.parallel_engine.config.max_workers = 1
        
        sequential_results = self.run_optimized_backtest(
            strategy_class, sample_symbols[:10], days=days  # 샘플만 테스트
        )
        sequential_time = time.time() - start_time
        
        # 2. 최적화 활성화
        self.config.enable_cache = original_cache_setting
        self.parallel_engine.config.max_workers = original_workers
        
        start_time = time.time()
        optimized_results = self.run_optimized_backtest(
            strategy_class, sample_symbols[:10], days=days
        )
        optimized_time = time.time() - start_time
        
        # 3. 성능 비교
        speedup = sequential_time / optimized_time if optimized_time > 0 else 0
        
        benchmark_results = {
            'sequential_time': sequential_time,
            'optimized_time': optimized_time,
            'speedup': speedup,
            'efficiency_improvement': (1 - optimized_time / sequential_time) * 100,
            'sample_size': len(sample_symbols[:10]),
            'estimated_full_speedup': {
                'full_kospi_sequential': sequential_time * (DataCollectionConstants.TOTAL_KOSPI_SYMBOLS / 10),
                'full_kospi_optimized': optimized_time * (DataCollectionConstants.TOTAL_KOSPI_SYMBOLS / 10),
                'estimated_full_speedup': speedup
            }
        }
        
        logger.info(f"벤치마크 완료: {speedup:.2f}x 성능 향상")
        return benchmark_results
    
def clear_all_caches(self):
        """모든 캐시 클리어"""
        if self.config.enable_cache:
            self.cache_manager.clear_cache()
        
        self.batch_processor.data_loader.clear_cache()
        logger.info("모든 캐시 클리어 완료")

# 편의 함수들
def create_optimized_engine(max_workers: int = None, 
                          enable_cache: bool = True,
                          max_memory_mb: int = None) -> OptimizedBacktestEngine:
    """최적화된 백테스팅 엔진 생성"""
    
    config = OptimizedBacktestConfig(
        max_workers=max_workers,
        enable_cache=enable_cache,
        max_memory_usage_mb=max_memory_mb or SystemConstants.MEMORY_WARNING_THRESHOLD_MB * 2
    )
    
    return OptimizedBacktestEngine(config)

def run_kospi_backtest_optimized(strategy_class, 
                                top_n: int = DataCollectionConstants.OPTIMIZED_ENGINE_THRESHOLD,
                                days: int = DataCollectionConstants.DEFAULT_BACKTEST_DAYS) -> Dict[str, Any]:
    """코스피 상위 종목 최적화 백테스팅"""
    
    # 최적화 엔진 생성
    engine = create_optimized_engine()
    
    # 상위 종목 선택
    from src.data.stock_filter import get_kospi_top
    
    top_symbols = get_kospi_top(top_n)
    
    # 최적화된 백테스팅 실행
    return engine.run_optimized_backtest(strategy_class, top_symbols, days=days)

def estimate_kospi_full_time(sample_results: Dict[str, Any]) -> Dict[str, Any]:
    """전체 코스피 백테스팅 예상 시간 계산"""
    
    performance_analysis = sample_results.get('performance_analysis', {})
    sample_size = performance_analysis.get('total_symbols', 0)
    total_time = performance_analysis.get('total_time', 0)
    
    if sample_size > 0 and total_time > 0:
        time_per_symbol = total_time / sample_size
        kospi_total = DataCollectionConstants.TOTAL_KOSPI_SYMBOLS
        
        estimated_time = time_per_symbol * kospi_total
        
        return {
            'sample_size': sample_size,
            'sample_time': total_time,
            'time_per_symbol': time_per_symbol,
            'kospi_total_symbols': kospi_total,
            'estimated_total_time': estimated_time,
            'estimated_time_minutes': estimated_time / 60,
            'performance_grade': '매우 빠름 ⚡⚡⚡' if estimated_time < OptimizationConstants.PERFORMANCE_VERY_FAST_THRESHOLD else
                               '빠름 ⚡⚡' if estimated_time < OptimizationConstants.PERFORMANCE_FAST_THRESHOLD else
                               '보통 ⚡' if estimated_time < OptimizationConstants.PERFORMANCE_NORMAL_THRESHOLD else '느림'
        }
    
    return {'error': '샘플 결과가 불충분합니다'}

# 진행률 콜백 예시
def progress_callback_with_eta(progress: float, completed: int, total: int, start_time: float = None):
    """ETA 포함 진행률 콜백"""
    if start_time is None:
        start_time = time.time()
    
    elapsed = time.time() - start_time
    if progress > 0:
        eta = elapsed * (100 - progress) / progress
        eta_str = f"ETA: {eta:.1f}초"
    else:
        eta_str = "ETA: 계산중..."
    
    print(f"\r진행률: {progress:.1f}% ({completed}/{total}) | {eta_str}", end='', flush=True)
    if completed == total:
        print(f"\n완료! 총 소요시간: {elapsed:.1f}초")

# 성능 프로파일링 데코레이터
def profile_performance(func):
    """성능 프로파일링 데코레이터"""
def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        logger.info(f"{func.__name__} 실행 시간: {end_time - start_time:.2f}초")
        return result
    
    return wrapper 