#!/usr/bin/env python3
"""
백테스팅 엔진 테스트

커서룰의 테스트 원칙에 따라 최적화된 백테스팅 시스템을 검증
"""

import unittest
import pandas as pd
import numpy as np
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.trading.optimized_backtest import (
    OptimizedBacktestEngine,
    OptimizedBacktestConfig,
    create_optimized_engine,
    run_kospi_backtest_optimized,
)
from src.strategies.base_strategy import BaseStrategy, TradeSignal, StrategyConfig
from src.constants import (
    TradingConstants,
    DataCollectionConstants,
    OptimizationConstants,
)


class MockDataCollector:
    """테스트용 데이터 수집기"""

    def __init__(self):
        self.call_count = 0

    def get_stock_data(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """모의 주식 데이터 생성"""
        self.call_count += 1

        # 재현 가능한 데이터 생성
        np.random.seed(hash(symbol) % 1000)

        dates = pd.date_range(
            start=datetime.now() - timedelta(days=days), periods=days, freq="D"
        )

        base_price = 50000 + (hash(symbol) % 50000)
        returns = np.random.normal(0.001, 0.02, days)
        prices = [base_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        return pd.DataFrame(
            {
                "date": dates,
                "open": np.array(prices) * np.random.uniform(0.99, 1.01, days),
                "high": np.array(prices) * np.random.uniform(1.01, 1.05, days),
                "low": np.array(prices) * np.random.uniform(0.95, 0.99, days),
                "close": prices,
                "volume": np.random.randint(10000, 100000, days),
            }
        )


class MockStrategy(BaseStrategy):
    """테스트용 간단한 전략"""

    def __init__(self, config: StrategyConfig = None):
        if config is None:
            config = StrategyConfig(name="MockStrategy")
        super().__init__(config)
        self.calculation_count = 0
        self.signal_count = 0

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """간단한 지표 계산"""
        self.calculation_count += 1

        data["sma_5"] = data["close"].rolling(5).mean()
        data["sma_20"] = data["close"].rolling(20).mean()
        data["rsi"] = np.random.uniform(20, 80, len(data))

        return data

    def generate_signals(self, data: pd.DataFrame) -> list:
        """간단한 신호 생성"""
        self.signal_count += 1
        signals = []

        for i in range(20, len(data)):  # 충분한 데이터가 있는 구간만
            row = data.iloc[i]
            prev_row = data.iloc[i - 1]

            # 골든크로스
            if row["sma_5"] > row["sma_20"] and prev_row["sma_5"] <= prev_row["sma_20"]:
                signals.append(
                    TradeSignal(
                        timestamp=datetime.now(),
                        symbol="TEST",
                        signal_type="BUY",
                        price=row["close"],
                        confidence=0.8,
                        reason="Golden Cross",
                        indicators={"rsi": row["rsi"]},
                        risk_level="MEDIUM",
                    )
                )

        return signals

    def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """모든 신호 유효하다고 가정"""
        return True


class TestOptimizedBacktestConfig(unittest.TestCase):
    """OptimizedBacktestConfig 테스트"""

    def test_default_config(self):
        """기본 설정 테스트"""
        config = OptimizedBacktestConfig()

        # 상수 기반 기본값 확인
        self.assertEqual(
            config.initial_capital, TradingConstants.DEFAULT_INITIAL_CAPITAL
        )
        self.assertEqual(config.commission, TradingConstants.TRANSACTION_FEE_RATE)
        self.assertEqual(config.batch_size, DataCollectionConstants.DEFAULT_BATCH_SIZE)

        # 기본 설정 확인
        self.assertTrue(config.enable_cache)
        self.assertTrue(config.adaptive_batch_size)
        self.assertIsNone(config.max_workers)

    def test_custom_config(self):
        """사용자 정의 설정 테스트"""
        config = OptimizedBacktestConfig(
            max_workers=8,
            enable_cache=False,
            initial_capital=2000000,
            commission=0.0002,
        )

        self.assertEqual(config.max_workers, 8)
        self.assertFalse(config.enable_cache)
        self.assertEqual(config.initial_capital, 2000000)
        self.assertEqual(config.commission, 0.0002)


class TestOptimizedBacktestEngine(unittest.TestCase):
    """OptimizedBacktestEngine 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        # 캐시 비활성화하여 테스트 격리
        self.config = OptimizedBacktestConfig(
            enable_cache=False, max_workers=2, batch_size=5
        )
        self.engine = OptimizedBacktestEngine(self.config)

        # 모의 데이터 수집기 주입
        self.mock_collector = MockDataCollector()
        self.engine.data_collector = self.mock_collector

        # 테스트용 심볼 리스트
        self.test_symbols = ["005930", "000660", "035420", "051910", "035720"]

        # 모의 전략
        self.mock_strategy = MockStrategy

    def test_engine_initialization(self):
        """엔진 초기화 테스트"""
        self.assertIsInstance(self.engine.config, OptimizedBacktestConfig)
        self.assertIsNotNone(self.engine.parallel_engine)
        self.assertIsNotNone(self.engine.batch_processor)

        # 성능 통계 초기화 확인
        self.assertIn("optimization_enabled", self.engine.performance_stats)
        self.assertEqual(self.engine.performance_stats["total_runs"], 0)

    def test_data_collection_optimized(self):
        """최적화된 데이터 수집 테스트"""
        symbols_data = self.engine._collect_data_optimized(self.test_symbols, days=60)

        self.assertIsInstance(symbols_data, dict)
        self.assertEqual(len(symbols_data), len(self.test_symbols))

        # 각 심볼의 데이터 확인
        for symbol in self.test_symbols:
            self.assertIn(symbol, symbols_data)
            data = symbols_data[symbol]
            self.assertIsInstance(data, pd.DataFrame)
            self.assertGreater(len(data), 0)

            # 필수 컬럼 확인
            required_cols = ["open", "high", "low", "close", "volume"]
            for col in required_cols:
                self.assertIn(col, data.columns)

    def test_run_optimized_backtest_basic(self):
        """기본 최적화 백테스팅 실행 테스트"""
        results = self.engine.run_optimized_backtest(
            self.mock_strategy, self.test_symbols[:3], days=30  # 작은 샘플로 테스트
        )

        # 결과 구조 확인
        self.assertIn("results", results)
        self.assertIn("performance_analysis", results)
        self.assertIn("optimization_stats", results)
        self.assertIn("total_time", results)

        # 결과 내용 확인
        backtest_results = results["results"]
        self.assertIsInstance(backtest_results, dict)
        self.assertGreater(len(backtest_results), 0)

        # 성능 분석 확인
        perf_analysis = results["performance_analysis"]
        self.assertIn("total_time", perf_analysis)
        self.assertIn("total_symbols", perf_analysis)
        self.assertGreater(perf_analysis["total_symbols"], 0)

    def test_run_optimized_backtest_with_parameters(self):
        """매개변수가 있는 백테스팅 테스트"""
        strategy_params = {"rsi_period": 14, "threshold": 0.7}

        results = self.engine.run_optimized_backtest(
            self.mock_strategy,
            self.test_symbols[:2],
            strategy_params=strategy_params,
            days=45,
        )

        self.assertIsInstance(results, dict)
        self.assertIn("results", results)

        # 매개변수가 전달되었는지 간접적으로 확인 (오류 없이 실행되면 성공)
        self.assertGreater(len(results["results"]), 0)

    def test_performance_stats_update(self):
        """성능 통계 업데이트 테스트"""
        initial_runs = self.engine.performance_stats["total_runs"]
        initial_symbols = self.engine.performance_stats["total_symbols"]

        self.engine.run_optimized_backtest(
            self.mock_strategy, self.test_symbols[:2], days=20
        )

        # 통계가 업데이트되었는지 확인
        self.assertEqual(self.engine.performance_stats["total_runs"], initial_runs + 1)
        self.assertEqual(
            self.engine.performance_stats["total_symbols"], initial_symbols + 2
        )
        self.assertGreater(self.engine.performance_stats["total_time"], 0)

    def test_optimization_stats(self):
        """최적화 통계 조회 테스트"""
        # 백테스팅 실행
        self.engine.run_optimized_backtest(
            self.mock_strategy, self.test_symbols[:3], days=25
        )

        stats = self.engine.get_optimization_stats()

        # 기본 통계 확인
        self.assertIn("total_runs", stats)
        self.assertIn("total_symbols", stats)
        self.assertIn("avg_symbols_per_run", stats)
        self.assertIn("avg_time_per_symbol", stats)

        # 컴포넌트별 상세 통계 확인
        self.assertIn("parallel_detailed", stats)
        self.assertIn("batch_detailed", stats)

    def test_clear_caches(self):
        """캐시 클리어 테스트"""
        # 캐시 활성화된 엔진으로 테스트
        cached_config = OptimizedBacktestConfig(enable_cache=True)
        cached_engine = OptimizedBacktestEngine(cached_config)
        cached_engine.data_collector = self.mock_collector

        # 캐시 클리어 실행 (오류 없이 실행되면 성공)
        try:
            cached_engine.clear_all_caches()
        except Exception as e:
            self.fail(f"캐시 클리어 중 오류 발생: {e}")

    def test_benchmark_optimizations(self):
        """최적화 벤치마크 테스트"""
        # 작은 샘플로 벤치마크 실행
        benchmark_results = self.engine.benchmark_optimizations(
            self.mock_strategy, self.test_symbols[:3], days=20
        )

        # 벤치마크 결과 구조 확인
        self.assertIn("sequential_time", benchmark_results)
        self.assertIn("optimized_time", benchmark_results)
        self.assertIn("speedup", benchmark_results)
        self.assertIn("efficiency_improvement", benchmark_results)
        self.assertIn("estimated_full_speedup", benchmark_results)

        # 기본적인 값 검증
        self.assertGreater(benchmark_results["sequential_time"], 0)
        self.assertGreater(benchmark_results["optimized_time"], 0)
        self.assertGreaterEqual(benchmark_results["speedup"], 0)


class TestConvenienceFunctions(unittest.TestCase):
    """편의 함수 테스트"""

    def test_create_optimized_engine(self):
        """최적화 엔진 생성 함수 테스트"""
        engine = create_optimized_engine(
            max_workers=4, enable_cache=True, max_memory_mb=512
        )

        self.assertIsInstance(engine, OptimizedBacktestEngine)
        self.assertEqual(engine.config.max_workers, 4)
        self.assertTrue(engine.config.enable_cache)
        self.assertEqual(engine.config.max_memory_usage_mb, 512)

    def test_create_optimized_engine_defaults(self):
        """기본값으로 엔진 생성 테스트"""
        engine = create_optimized_engine()

        self.assertIsInstance(engine, OptimizedBacktestEngine)
        self.assertTrue(engine.config.enable_cache)
        # 기본 메모리 제한 확인
        expected_memory = OptimizationConstants.MEMORY_WARNING_THRESHOLD_MB * 2
        self.assertEqual(engine.config.max_memory_usage_mb, expected_memory)

    @patch("src.data.stock_filter.get_kospi_top")
    def test_run_kospi_backtest_optimized(self, mock_get_kospi_top):
        """코스피 백테스팅 함수 테스트"""
        # 모의 상위 종목 반환
        mock_symbols = ["005930", "000660", "035420"]
        mock_get_kospi_top.return_value = mock_symbols

        # 데이터 수집기 모킹
        with patch(
            "src.trading.optimized_backtest.StockCollector"
        ) as mock_collector_class:
            mock_collector_instance = MockDataCollector()
            mock_collector_class.return_value = mock_collector_instance

            try:
                results = run_kospi_backtest_optimized(MockStrategy, top_n=3, days=30)

                # 기본 결과 구조 확인
                self.assertIn("results", results)
                self.assertIn("performance_analysis", results)

            except Exception as e:
                # 실제 데이터 의존성으로 인한 실패는 허용
                self.assertIn("StockCollector", str(e)) or self.assertIn(
                    "get_kospi_top", str(e)
                )


class TestPerformanceOptimizations(unittest.TestCase):
    """성능 최적화 테스트"""

    def setUp(self):
        """테스트 환경 설정"""
        self.mock_collector = MockDataCollector()

    def test_parallel_processing_benefit(self):
        """병렬 처리 성능 이득 테스트"""
        symbols = ["SYM1", "SYM2", "SYM3", "SYM4", "SYM5"]

        # 순차 처리 엔진
        sequential_config = OptimizedBacktestConfig(
            max_workers=1, enable_cache=False, batch_size=1
        )
        sequential_engine = OptimizedBacktestEngine(sequential_config)
        sequential_engine.data_collector = self.mock_collector

        # 병렬 처리 엔진
        parallel_config = OptimizedBacktestConfig(
            max_workers=3, enable_cache=False, batch_size=2
        )
        parallel_engine = OptimizedBacktestEngine(parallel_config)
        parallel_engine.data_collector = self.mock_collector

        # 실행 시간 측정
        start_time = time.time()
        sequential_results = sequential_engine.run_optimized_backtest(
            MockStrategy, symbols[:3], days=20
        )
        sequential_time = time.time() - start_time

        start_time = time.time()
        parallel_results = parallel_engine.run_optimized_backtest(
            MockStrategy, symbols[:3], days=20
        )
        parallel_time = time.time() - start_time

        # 결과 검증
        self.assertEqual(
            len(sequential_results["results"]), len(parallel_results["results"])
        )

        # 성능 향상이 있거나 최소한 크게 나빠지지 않았는지 확인
        # (작은 샘플에서는 오버헤드로 인해 병렬 처리가 더 느릴 수 있음)
        self.assertLess(parallel_time, sequential_time * 2)  # 2배 이상 느려지지 않음

    def test_batch_processing_memory_efficiency(self):
        """배치 처리 메모리 효율성 테스트"""
        large_symbol_list = [f"SYM{i:03d}" for i in range(20)]

        # 작은 배치 크기로 엔진 설정
        config = OptimizedBacktestConfig(
            enable_cache=False,
            batch_size=5,
            max_memory_usage_mb=100,  # 작은 메모리 제한
        )
        engine = OptimizedBacktestEngine(config)
        engine.data_collector = self.mock_collector

        # 메모리 제한 하에서 실행 (오류 없이 완료되면 성공)
        try:
            results = engine.run_optimized_backtest(
                MockStrategy, large_symbol_list[:10], days=15  # 적당한 크기로 테스트
            )

            self.assertIsInstance(results, dict)
            self.assertIn("results", results)

        except MemoryError:
            self.fail("배치 처리에서 메모리 오류 발생")

    def test_optimization_components_integration(self):
        """최적화 컴포넌트 통합 테스트"""
        config = OptimizedBacktestConfig(
            enable_cache=True, max_workers=2, batch_size=3, adaptive_batch_size=True
        )
        engine = OptimizedBacktestEngine(config)
        engine.data_collector = self.mock_collector

        symbols = ["TEST1", "TEST2", "TEST3", "TEST4", "TEST5"]

        # 첫 번째 실행 (캐시 구축)
        results1 = engine.run_optimized_backtest(MockStrategy, symbols, days=25)

        # 두 번째 실행 (캐시 활용)
        results2 = engine.run_optimized_backtest(MockStrategy, symbols, days=25)

        # 두 실행 모두 성공했는지 확인
        self.assertIsInstance(results1, dict)
        self.assertIsInstance(results2, dict)

        # 기본적인 최적화 통계 확인
        stats = engine.get_optimization_stats()
        self.assertEqual(stats["total_runs"], 2)
        self.assertEqual(stats["total_symbols"], len(symbols) * 2)


class TestErrorHandling(unittest.TestCase):
    """오류 처리 테스트"""

    def test_invalid_strategy_handling(self):
        """잘못된 전략 처리 테스트"""
        engine = create_optimized_engine(enable_cache=False)
        engine.data_collector = MockDataCollector()

        # None 전략 전달
        with self.assertRaises((TypeError, AttributeError)):
            engine.run_optimized_backtest(None, ["TEST"], days=20)

    def test_empty_symbols_list(self):
        """빈 심볼 리스트 처리 테스트"""
        engine = create_optimized_engine(enable_cache=False)
        engine.data_collector = MockDataCollector()

        results = engine.run_optimized_backtest(MockStrategy, [], days=20)

        # 빈 결과 반환
        self.assertEqual(len(results["results"]), 0)

    def test_invalid_days_parameter(self):
        """잘못된 일수 매개변수 테스트"""
        engine = create_optimized_engine(enable_cache=False)
        engine.data_collector = MockDataCollector()

        # 음수 일수
        with self.assertRaises((ValueError, Exception)):
            engine.run_optimized_backtest(MockStrategy, ["TEST"], days=-10)

        # 0 일수
        with self.assertRaises((ValueError, Exception)):
            engine.run_optimized_backtest(MockStrategy, ["TEST"], days=0)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
