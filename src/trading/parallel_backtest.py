"""
병렬 백테스팅 엔진
우선순위 1: 병렬 처리 구현
"""

import time
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Any, Callable
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import pickle
import traceback
from dataclasses import dataclass

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

logger = logging.getLogger(__name__)


@dataclass
class ParallelBacktestConfig:
    """병렬 백테스팅 설정"""

    max_workers: Optional[int] = None
    chunk_size: int = 10
    timeout: Optional[float] = 300  # 5분 타임아웃
    progress_callback: Optional[Callable] = None
    cache_results: bool = True
    memory_limit_mb: int = 1024  # 1GB 메모리 제한


class ParallelBacktestEngine:
    """고성능 병렬 백테스팅 엔진"""


def __init__(self, config: ParallelBacktestConfig = None):
    self.config = config or ParallelBacktestConfig()
    self.cpu_cores = multiprocessing.cpu_count()

    # 최적 워커 수 계산
    if self.config.max_workers is None:
        self.config.max_workers = min(self.cpu_cores, 8)  # 최대 8개 워커

    self.results_cache = {}
    self.performance_stats = {
        "total_symbols": 0,
        "successful_backtests": 0,
        "failed_backtests": 0,
        "total_time": 0,
        "avg_time_per_symbol": 0,
        "cache_hits": 0,
    }

    logger.info(f"병렬 백테스팅 엔진 초기화: {self.config.max_workers}개 워커")


def run_parallel_backtest(
    self,
    strategy_class,
    symbols_data: Dict[str, pd.DataFrame],
    strategy_params: Dict = None,
    backtest_config: Dict = None,
) -> Dict[str, Any]:
    """
    병렬 백테스팅 실행

    Args:
        strategy_class: 전략 클래스
        symbols_data: {symbol: DataFrame} 형태의 데이터
        strategy_params: 전략 파라미터
        backtest_config: 백테스팅 설정

    Returns:
        백테스팅 결과 딕셔너리
    """
    start_time = time.time()
    symbols = list(symbols_data.keys())

    logger.info(
        f"병렬 백테스팅 시작: {len(symbols)}개 종목, {self.config.max_workers}개 워커"
    )

    # 성능 통계 초기화
    self.performance_stats["total_symbols"] = len(symbols)
    self.performance_stats["successful_backtests"] = 0
    self.performance_stats["failed_backtests"] = 0

    # 심볼을 청크로 분할
    symbol_chunks = self._create_symbol_chunks(symbols)

    # 병렬 처리 작업 준비
    tasks = []
    for chunk in symbol_chunks:
        chunk_data = {symbol: symbols_data[symbol] for symbol in chunk}
        task = {
            "strategy_class": strategy_class,
            "symbols_data": chunk_data,
            "strategy_params": strategy_params or {},
            "backtest_config": backtest_config or {},
            "chunk_id": len(tasks),
        }
        tasks.append(task)

    # 병렬 실행
    results = {}

    try:
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 작업 제출
            future_to_chunk = {
                executor.submit(process_backtest_chunk, task): task["chunk_id"]
                for task in tasks
            }

            # 결과 수집
            completed_chunks = 0
            for future in as_completed(future_to_chunk, timeout=self.config.timeout):
                chunk_id = future_to_chunk[future]

                try:
                    chunk_results = future.result()
                    results.update(chunk_results)

                    # 성공한 백테스팅 수 업데이트
                    successful_count = sum(
                        1 for r in chunk_results.values() if r.get("success", False)
                    )
                    self.performance_stats["successful_backtests"] += successful_count
                    self.performance_stats["failed_backtests"] += (
                        len(chunk_results) - successful_count
                    )

                    completed_chunks += 1

                    # 진행률 콜백
                    if self.config.progress_callback:
                        progress = completed_chunks / len(tasks) * 100
                        self.config.progress_callback(
                            progress, completed_chunks, len(tasks)
                        )

                    logger.info(
                        f"청크 {chunk_id} 완료: {len(chunk_results)}개 종목 처리"
                    )

                except Exception as e:
                    logger.error(f"청크 {chunk_id} 처리 실패: {e}")
                    self.performance_stats["failed_backtests"] += len(
                        tasks[chunk_id]["symbols_data"]
                    )

    except Exception as e:
        logger.error(f"병렬 백테스팅 실행 실패: {e}")
        return {"error": str(e), "results": {}}

    # 성능 통계 계산
    total_time = time.time() - start_time
    self.performance_stats["total_time"] = total_time

    if self.performance_stats["successful_backtests"] > 0:
        self.performance_stats["avg_time_per_symbol"] = (
            total_time / self.performance_stats["successful_backtests"]
        )

    logger.info(f"병렬 백테스팅 완료: {len(results)}개 결과, {total_time:.2f}초")

    return {
        "results": results,
        "performance_stats": self.performance_stats,
        "total_time": total_time,
        "success_rate": self.performance_stats["successful_backtests"]
        / self.performance_stats["total_symbols"]
        * 100,
    }


def _create_symbol_chunks(self, symbols: List[str]) -> List[List[str]]:
    """심볼을 청크로 분할"""
    chunk_size = self.config.chunk_size
    chunks = []

    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i : i + chunk_size]
        chunks.append(chunk)

    logger.info(
        f"심볼 청크 생성: {len(chunks)}개 청크, 청크당 최대 {chunk_size}개 종목"
    )
    return chunks


def get_performance_report(self) -> Dict[str, Any]:
    """성능 리포트 반환"""
    stats = self.performance_stats.copy()

    if stats["total_symbols"] > 0:
        stats["success_rate"] = (
            stats["successful_backtests"] / stats["total_symbols"] * 100
        )
        stats["failure_rate"] = stats["failed_backtests"] / stats["total_symbols"] * 100

    # 예상 전체 코스피 처리 시간
    if stats["avg_time_per_symbol"] > 0:
        kospi_total = 962
        estimated_time = stats["avg_time_per_symbol"] * kospi_total
        estimated_parallel_time = estimated_time / self.config.max_workers

        stats["estimated_kospi_sequential"] = estimated_time
        stats["estimated_kospi_parallel"] = estimated_parallel_time

    return stats


def process_backtest_chunk(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    백테스팅 청크 처리 함수 (멀티프로세싱용)

    Args:
        task: 작업 정보 딕셔너리

    Returns:
        청크 백테스팅 결과
    """
    try:
        # 필요한 모듈 임포트
        import sys
        from pathlib import Path

        # 프로젝트 루트 설정
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        sys.path.append(str(PROJECT_ROOT / "src"))

        from src.trading.backtest import BacktestEngine, BacktestConfig

        # 작업 정보 추출
        strategy_class = task["strategy_class"]
        symbols_data = task["symbols_data"]
        strategy_params = task.get("strategy_params", {})
        backtest_config = task.get("backtest_config", {})

        # 백테스팅 설정
        config = BacktestConfig(
            initial_capital=backtest_config.get("initial_capital", 1000000),
            commission_rate=backtest_config.get("commission", 0.00015),
            slippage_rate=backtest_config.get("slippage", 0.001),
        )

        results = {}

        # 각 종목에 대해 백테스팅 실행
        for symbol, data in symbols_data.items():
            try:
                # 전략 인스턴스 생성
                strategy = strategy_class()

                # 전략 파라미터 설정
                for param, value in strategy_params.items():
                    if hasattr(strategy, param):
                        setattr(strategy, param, value)

                # 백테스팅 엔진 생성 및 실행
                engine = BacktestEngine(config)
                result = engine.run_backtest(strategy, {symbol: data})

                # 결과 저장
                results[symbol] = {
                    "success": True,
                    "total_return": result.get("total_return", 0),
                    "sharpe_ratio": result.get("sharpe_ratio", 0),
                    "max_drawdown": result.get("max_drawdown", 0),
                    "win_rate": result.get("win_rate", 0),
                    "total_trades": result.get("total_trades", 0),
                    "final_portfolio_value": result.get("final_portfolio_value", 0),
                    "data_points": len(data),
                }

            except Exception as e:
                # 개별 종목 실패 시
                results[symbol] = {
                    "success": False,
                    "error": str(e),
                    "total_return": 0,
                    "sharpe_ratio": 0,
                    "max_drawdown": 0,
                    "win_rate": 0,
                    "total_trades": 0,
                }

        return results

    except Exception as e:
        # 청크 전체 실패 시
        error_msg = f"청크 처리 실패: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        return {
            symbol: {"success": False, "error": error_msg}
            for symbol in task["symbols_data"].keys()
        }


def progress_callback_default(progress: float, completed: int, total: int):
    """기본 진행률 콜백"""
    print(
        f"\r진행률: {progress:.1f}% ({completed}/{total} 청크 완료)", end="", flush=True
    )
    if completed == total:
        print()  # 완료 시 새 줄


# 편의 함수들
def run_parallel_backtest_simple(
    strategy_class, symbols_data: Dict[str, pd.DataFrame], max_workers: int = None
) -> Dict[str, Any]:
    """간단한 병렬 백테스팅 실행"""
    config = ParallelBacktestConfig(
        max_workers=max_workers, progress_callback=progress_callback_default
    )

    engine = ParallelBacktestEngine(config)
    return engine.run_parallel_backtest(strategy_class, symbols_data)


def benchmark_parallel_performance(
    strategy_class, sample_data: Dict[str, pd.DataFrame]
) -> Dict[str, Any]:
    """병렬 처리 성능 벤치마크"""
    results = {}

    # 순차 처리
    start_time = time.time()
    sequential_results = {}

    from src.trading.backtest import BacktestEngine, BacktestConfig

    config = BacktestConfig(initial_capital=1000000)

    for symbol, data in sample_data.items():
        strategy = strategy_class()
        engine = BacktestEngine(config)
        result = engine.run_backtest(strategy, {symbol: data})
        sequential_results[symbol] = result

    sequential_time = time.time() - start_time

    # 병렬 처리
    parallel_result = run_parallel_backtest_simple(strategy_class, sample_data)
    parallel_time = parallel_result["total_time"]

    # 성능 비교
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    efficiency = speedup / multiprocessing.cpu_count() * 100

    return {
        "sequential_time": sequential_time,
        "parallel_time": parallel_time,
        "speedup": speedup,
        "efficiency": efficiency,
        "sample_size": len(sample_data),
        "parallel_results": parallel_result,
    }
