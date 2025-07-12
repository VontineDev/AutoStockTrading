"""
배치 처리 최적화 시스템
우선순위 3: 배치 처리 최적화
"""

import gc
import time
import psutil
import logging
from typing import Dict, List, Any, Optional, Tuple, Iterator, Generator
from pathlib import Path
import pandas as pd
import numpy as np
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict
import sys

logger = logging.getLogger(__name__)

@dataclass
class BatchConfig:
    """배치 처리 설정"""
    max_memory_usage_mb: int = 1024  # 최대 메모리 사용량 (MB)
    batch_size: int = 50  # 배치 크기
    min_batch_size: int = 10  # 최소 배치 크기
    max_batch_size: int = 200  # 최대 배치 크기
    memory_monitoring_interval: float = 1.0  # 메모리 모니터링 간격 (초)
    auto_gc_threshold: float = 0.8  # 자동 GC 임계값
    preload_data: bool = True  # 데이터 미리 로드
    adaptive_batch_size: bool = True  # 적응형 배치 크기

class MemoryMonitor:
    """메모리 사용량 모니터링"""
    
def __init__(self, config: BatchConfig):
        self.config = config
        self.process = psutil.Process()
        self.max_memory_bytes = config.max_memory_usage_mb * 1024 * 1024
        self.monitoring = False
        self.stats = {
            'peak_memory_mb': 0,
            'current_memory_mb': 0,
            'gc_count': 0,
            'memory_warnings': 0,
            'memory_exceeded_count': 0
        }
    
def get_memory_usage(self) -> float:
        """현재 메모리 사용량 반환 (MB)"""
        memory_mb = self.process.memory_info().rss / (1024 * 1024)
        self.stats['current_memory_mb'] = memory_mb
        
        if memory_mb > self.stats['peak_memory_mb']:
            self.stats['peak_memory_mb'] = memory_mb
        
        return memory_mb
    
def get_memory_usage_ratio(self) -> float:
        """메모리 사용률 반환 (0-1)"""
        return self.get_memory_usage() / self.config.max_memory_usage_mb
    
def is_memory_exceeded(self) -> bool:
        """메모리 한계 초과 여부"""
        exceeded = self.get_memory_usage() > self.config.max_memory_usage_mb
        if exceeded:
            self.stats['memory_exceeded_count'] += 1
        return exceeded
    
def should_trigger_gc(self) -> bool:
        """가비지 컬렉션 실행 여부"""
        return self.get_memory_usage_ratio() > self.config.auto_gc_threshold
    
def force_gc(self):
        """강제 가비지 컬렉션"""
        gc.collect()
        self.stats['gc_count'] += 1
        logger.debug(f"가비지 컬렉션 실행: {self.get_memory_usage():.1f}MB")

class BatchOptimizer:
    """배치 처리 최적화"""
    
def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self.memory_monitor = MemoryMonitor(self.config)
        self.current_batch_size = self.config.batch_size
        self.performance_history = []
        
        # 성능 통계
        self.stats = {
            'total_batches': 0,
            'total_items': 0,
            'total_time': 0,
            'avg_items_per_second': 0,
            'avg_batch_time': 0,
            'memory_optimizations': 0,
            'batch_size_changes': 0
        }
        
        logger.info(f"배치 최적화 시스템 초기화: 배치 크기 {self.current_batch_size}")
    
def create_batches(self, items: List[Any]) -> List[List[Any]]:
        """아이템을 배치로 분할"""
        batches = []
        current_batch_size = self.current_batch_size
        
        for i in range(0, len(items), current_batch_size):
            batch = items[i:i + current_batch_size]
            batches.append(batch)
        
        logger.info(f"배치 생성: {len(batches)}개 배치, 배치 크기: {current_batch_size}")
        return batches
    
def adaptive_batch_sizing(self, processing_time: float, batch_size: int, success_rate: float):
        """적응형 배치 크기 조정"""
        if not self.config.adaptive_batch_size:
            return
        
        # 성능 기록
        performance_score = success_rate / processing_time if processing_time > 0 else 0
        self.performance_history.append({
            'batch_size': batch_size,
            'processing_time': processing_time,
            'performance_score': performance_score,
            'memory_usage': self.memory_monitor.get_memory_usage()
        })
        
        # 최근 3개 기록만 유지
        if len(self.performance_history) > 3:
            self.performance_history.pop(0)
        
        # 성능 기반 배치 크기 조정
        if len(self.performance_history) >= 2:
            recent_performance = self.performance_history[-1]['performance_score']
            previous_performance = self.performance_history[-2]['performance_score']
            
            # 메모리 사용량 고려
            memory_ratio = self.memory_monitor.get_memory_usage_ratio()
            
            if memory_ratio > 0.8:  # 메모리 부족 시 배치 크기 감소
                new_batch_size = max(self.config.min_batch_size, int(batch_size * 0.8))
                logger.info(f"메모리 부족으로 배치 크기 감소: {batch_size} -> {new_batch_size}")
            elif recent_performance > previous_performance * 1.1:  # 성능 향상 시 배치 크기 증가
                new_batch_size = min(self.config.max_batch_size, int(batch_size * 1.2))
                logger.info(f"성능 향상으로 배치 크기 증가: {batch_size} -> {new_batch_size}")
            elif recent_performance < previous_performance * 0.9:  # 성능 저하 시 배치 크기 감소
                new_batch_size = max(self.config.min_batch_size, int(batch_size * 0.9))
                logger.info(f"성능 저하로 배치 크기 감소: {batch_size} -> {new_batch_size}")
            else:
                new_batch_size = batch_size
            
            if new_batch_size != batch_size:
                self.current_batch_size = new_batch_size
                self.stats['batch_size_changes'] += 1
    
def optimize_memory_usage(self):
        """메모리 사용량 최적화"""
        if self.memory_monitor.should_trigger_gc():
            self.memory_monitor.force_gc()
            self.stats['memory_optimizations'] += 1
        
        # 메모리 한계 초과 시 배치 크기 감소
        if self.memory_monitor.is_memory_exceeded():
            new_batch_size = max(self.config.min_batch_size, int(self.current_batch_size * 0.7))
            if new_batch_size != self.current_batch_size:
                logger.warning(f"메모리 한계 초과로 배치 크기 감소: {self.current_batch_size} -> {new_batch_size}")
                self.current_batch_size = new_batch_size
                self.stats['batch_size_changes'] += 1
    
def process_batch_with_optimization(self, 
                                      batch: List[Any],
                                      processor_func: callable,
                                      **kwargs) -> Dict[str, Any]:
        """최적화된 배치 처리"""
        batch_start_time = time.time()
        
        # 메모리 최적화
        self.optimize_memory_usage()
        
        # 배치 처리
        try:
            results = processor_func(batch, **kwargs)
            success_rate = 1.0
        except Exception as e:
            logger.error(f"배치 처리 실패: {e}")
            results = {'error': str(e)}
            success_rate = 0.0
        
        # 성능 측정
        batch_time = time.time() - batch_start_time
        
        # 통계 업데이트
        self.stats['total_batches'] += 1
        self.stats['total_items'] += len(batch)
        self.stats['total_time'] += batch_time
        
        # 안전한 통계 계산
        if self.stats['total_batches'] > 0:
            self.stats['avg_batch_time'] = self.stats['total_time'] / self.stats['total_batches']
        
        if self.stats['total_time'] > 0:
            self.stats['avg_items_per_second'] = self.stats['total_items'] / self.stats['total_time']
        
        # 적응형 배치 크기 조정
        self.adaptive_batch_sizing(batch_time, len(batch), success_rate)
        
        return results

class DataBatchLoader:
    """데이터 배치 로더"""
    
def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self.data_cache = {}
        self.cache_lock = threading.Lock()
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'data_loads': 0,
            'cache_size_mb': 0
        }
    
def load_data_batch(self, symbols: List[str], data_source: callable) -> Dict[str, pd.DataFrame]:
        """데이터 배치 로드"""
        loaded_data = {}
        
        for symbol in symbols:
            # 캐시 확인
            if symbol in self.data_cache:
                loaded_data[symbol] = self.data_cache[symbol]
                self.stats['cache_hits'] += 1
            else:
                # 새로운 데이터 로드
                try:
                    data = data_source(symbol)
                    loaded_data[symbol] = data
                    
                    # 캐시에 저장 (메모리 허용 시)
                    if self.config.preload_data:
                        with self.cache_lock:
                            self.data_cache[symbol] = data
                    
                    self.stats['cache_misses'] += 1
                    self.stats['data_loads'] += 1
                    
                except Exception as e:
                    logger.error(f"데이터 로드 실패 ({symbol}): {e}")
                    continue
        
        return loaded_data
    
def get_cache_size(self) -> float:
        """캐시 크기 반환 (MB)"""
        total_size = 0
        for symbol, data in self.data_cache.items():
            total_size += data.memory_usage(deep=True).sum()
        
        size_mb = total_size / (1024 * 1024)
        self.stats['cache_size_mb'] = size_mb
        return size_mb
    
def clear_cache(self):
        """캐시 클리어"""
        with self.cache_lock:
            self.data_cache.clear()
            self.stats['cache_hits'] = 0
            self.stats['cache_misses'] = 0
            self.stats['cache_size_mb'] = 0

class BatchProcessor:
    """통합 배치 처리 시스템"""
    
def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self.optimizer = BatchOptimizer(config)
        self.data_loader = DataBatchLoader(config)
        self.memory_monitor = MemoryMonitor(config)
        
        logger.info("배치 처리 시스템 초기화 완료")
    
def process_symbols_in_batches(self,
                                 symbols: List[str],
                                 processor_func: callable,
                                 data_source: callable = None,
                                 **kwargs) -> Dict[str, Any]:
        """심볼 목록을 배치로 처리"""
        
        # 빈 심볼 리스트 처리
        if not symbols:
            logger.warning("빈 심볼 리스트가 제공되었습니다.")
            return {
                'results': {},
                'performance_stats': {
                    'total_symbols': 0,
                    'successful_symbols': 0,
                    'failed_symbols': 0,
                    'success_rate': 0.0,
                    'total_time': 0.0,
                    'avg_time_per_symbol': 0.0,
                    'symbols_per_second': 0.0,
                    'total_batches': 0,
                    'avg_batch_size': 0.0,
                    'memory_stats': self.memory_monitor.stats,
                    'optimizer_stats': self.optimizer.stats,
                    'loader_stats': self.data_loader.stats
                }
            }
        
        start_time = time.time()
        logger.info(f"배치 처리 시작: {len(symbols)}개 심볼")
        
        # 배치 생성
        batches = self.optimizer.create_batches(symbols)
        
        all_results = {}
        successful_count = 0
        failed_count = 0
        
        for batch_idx, batch in enumerate(batches):
            logger.info(f"배치 {batch_idx + 1}/{len(batches)} 처리 중... ({len(batch)}개 심볼)")
            
            try:
                # 데이터 로드 (필요 시)
                if data_source:
                    batch_data = self.data_loader.load_data_batch(batch, data_source)
                    kwargs['batch_data'] = batch_data
                
                # 배치 처리
                batch_results = self.optimizer.process_batch_with_optimization(
                    batch, processor_func, **kwargs
                )
                
                # 결과 병합
                if isinstance(batch_results, dict) and 'error' not in batch_results:
                    all_results.update(batch_results)
                    successful_count += len(batch)
                else:
                    failed_count += len(batch)
                
            except Exception as e:
                logger.error(f"배치 {batch_idx + 1} 처리 실패: {e}")
                failed_count += len(batch)
            
            # 진행률 출력
            progress = (batch_idx + 1) / len(batches) * 100
            logger.info(f"진행률: {progress:.1f}% ({batch_idx + 1}/{len(batches)} 배치 완료)")
        
        total_time = time.time() - start_time
        
        # 안전한 나눗셈을 위한 함수
def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
            """0으로 나누기 방지를 위한 안전한 나눗셈"""
            return numerator / denominator if denominator != 0 else default
        
        # 최종 성능 통계
        performance_stats = {
            'total_symbols': len(symbols),
            'successful_symbols': successful_count,
            'failed_symbols': failed_count,
            'success_rate': safe_divide(successful_count, len(symbols), 0.0) * 100,
            'total_time': total_time,
            'avg_time_per_symbol': safe_divide(total_time, len(symbols), 0.0),
            'symbols_per_second': safe_divide(len(symbols), total_time, 0.0),
            'total_batches': len(batches),
            'avg_batch_size': safe_divide(len(symbols), len(batches), 0.0),
            'memory_stats': self.memory_monitor.stats,
            'optimizer_stats': self.optimizer.stats,
            'loader_stats': self.data_loader.stats
        }
        
        logger.info(f"배치 처리 완료: {successful_count}/{len(symbols)} 성공, {total_time:.2f}초")
        
        return {
            'results': all_results,
            'performance_stats': performance_stats
        }
    
def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 반환"""
        return {
            'batch_optimizer': self.optimizer.stats,
            'data_loader': self.data_loader.stats,
            'memory_monitor': self.memory_monitor.stats,
            'current_batch_size': self.optimizer.current_batch_size,
            'cache_size_mb': self.data_loader.get_cache_size(),
            'memory_usage_mb': self.memory_monitor.get_memory_usage()
        }
    
def optimize_for_system(self) -> Dict[str, Any]:
        """시스템 최적화 권장사항"""
        total_memory_mb = psutil.virtual_memory().total / (1024 * 1024)
        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)
        cpu_cores = psutil.cpu_count()
        
        # 메모리 기반 권장사항
        recommended_memory_limit = min(available_memory_mb * 0.6, 2048)  # 60% 또는 2GB 중 작은 값
        recommended_batch_size = max(10, int(recommended_memory_limit / 20))  # 20MB당 1개 배치
        
        # CPU 기반 권장사항
        recommended_workers = min(cpu_cores, 8)
        
        recommendations = {
            'system_info': {
                'total_memory_mb': total_memory_mb,
                'available_memory_mb': available_memory_mb,
                'cpu_cores': cpu_cores
            },
            'recommended_settings': {
                'max_memory_usage_mb': recommended_memory_limit,
                'batch_size': recommended_batch_size,
                'max_workers': recommended_workers
            },
            'current_settings': {
                'max_memory_usage_mb': self.config.max_memory_usage_mb,
                'batch_size': self.config.batch_size,
                'current_batch_size': self.optimizer.current_batch_size
            }
        }
        
        return recommendations

# 편의 함수들
def create_optimized_batch_processor(max_memory_mb: int = None, batch_size: int = None) -> BatchProcessor:
    """최적화된 배치 처리기 생성"""
    
    # 시스템 기반 기본값 설정
    if max_memory_mb is None:
        available_memory = psutil.virtual_memory().available / (1024 * 1024)
        max_memory_mb = min(available_memory * 0.6, 2048)
    
    if batch_size is None:
        batch_size = max(10, int(max_memory_mb / 20))
    
    config = BatchConfig(
        max_memory_usage_mb=max_memory_mb,
        batch_size=batch_size,
        adaptive_batch_size=True,
        preload_data=True
    )
    
    return BatchProcessor(config)

def estimate_optimal_batch_size(data_size_mb: float, available_memory_mb: float) -> int:
    """최적 배치 크기 추정"""
    # 메모리 여유분의 80%를 배치 처리에 사용
    usable_memory = available_memory_mb * 0.8
    
    # 데이터 크기 기반 배치 크기 계산
    if data_size_mb > 0:
        estimated_batch_size = int(usable_memory / data_size_mb)
        return max(10, min(200, estimated_batch_size))
    
    return 50  # 기본값 