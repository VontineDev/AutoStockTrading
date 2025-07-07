#!/usr/bin/env python3
"""
상수 파일 테스트

커서룰의 테스트 원칙에 따라 상수 값들의 유효성과 일관성을 검증
"""

import unittest
import sys
from pathlib import Path

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.constants import (
    DataCollectionConstants, TradingConstants, TALibConstants,
    SystemConstants, OptimizationConstants, UIConstants,
    BacktestConstants, StrategyPresets, validate_constants
)


class TestDataCollectionConstants(unittest.TestCase):
    """데이터 수집 관련 상수 테스트"""
    
    def test_backtest_days_positive(self):
        """백테스팅 일수는 양수여야 함"""
        self.assertGreater(DataCollectionConstants.DEFAULT_BACKTEST_DAYS, 0)
        self.assertGreater(DataCollectionConstants.DEFAULT_HISTORICAL_DAYS, 0)
    
    def test_worker_counts_valid(self):
        """워커 수는 유효한 범위 내여야 함"""
        self.assertGreaterEqual(DataCollectionConstants.DEFAULT_MAX_WORKERS, 
                               DataCollectionConstants.MIN_WORKERS)
        self.assertLessEqual(DataCollectionConstants.DEFAULT_MAX_WORKERS, 
                            DataCollectionConstants.MAX_WORKERS)
    
    def test_engine_thresholds_logical(self):
        """엔진 선택 임계값이 논리적으로 올바른지 확인"""
        self.assertLess(DataCollectionConstants.PARALLEL_ENGINE_THRESHOLD,
                       DataCollectionConstants.OPTIMIZED_ENGINE_THRESHOLD)
    
    def test_api_settings_reasonable(self):
        """API 설정이 합리적인지 확인"""
        self.assertGreater(DataCollectionConstants.API_DELAY_SECONDS, 0)
        self.assertGreater(DataCollectionConstants.MAX_RETRY_COUNT, 0)
        self.assertGreater(DataCollectionConstants.API_TIMEOUT, 0)
    
    def test_batch_size_valid(self):
        """배치 크기가 유효한 범위 내인지 확인"""
        self.assertGreaterEqual(DataCollectionConstants.DEFAULT_BATCH_SIZE,
                               DataCollectionConstants.MIN_BATCH_SIZE)
        self.assertLessEqual(DataCollectionConstants.DEFAULT_BATCH_SIZE,
                            DataCollectionConstants.MAX_BATCH_SIZE)


class TestTradingConstants(unittest.TestCase):
    """트레이딩 관련 상수 테스트"""
    
    def test_capital_positive(self):
        """초기 자본은 양수여야 함"""
        self.assertGreater(TradingConstants.DEFAULT_INITIAL_CAPITAL, 0)
    
    def test_position_size_percentage(self):
        """포지션 크기는 0-100% 범위 내여야 함"""
        self.assertGreater(TradingConstants.MAX_POSITION_SIZE_PERCENT, 0)
        self.assertLessEqual(TradingConstants.MAX_POSITION_SIZE_PERCENT, 1)
    
    def test_risk_management_percentages(self):
        """리스크 관리 비율이 합리적인지 확인"""
        self.assertGreater(TradingConstants.STOP_LOSS_PERCENT, 0)
        self.assertLess(TradingConstants.STOP_LOSS_PERCENT, 1)
        self.assertGreater(TradingConstants.MAX_DRAWDOWN_PERCENT, 0)
        self.assertLess(TradingConstants.MAX_DRAWDOWN_PERCENT, 1)
    
    def test_fee_rates_reasonable(self):
        """수수료율이 합리적인지 확인"""
        self.assertGreater(TradingConstants.TRANSACTION_FEE_RATE, 0)
        self.assertLess(TradingConstants.TRANSACTION_FEE_RATE, 0.01)  # 1% 미만
        self.assertGreater(TradingConstants.TAX_RATE, 0)
        self.assertLess(TradingConstants.TAX_RATE, 0.01)  # 1% 미만
    
    def test_trading_signals_valid(self):
        """매매 신호 값이 유효한지 확인"""
        self.assertEqual(TradingConstants.BUY_SIGNAL, 1)
        self.assertEqual(TradingConstants.SELL_SIGNAL, -1)
        self.assertEqual(TradingConstants.HOLD_SIGNAL, 0)
        
        # 신호 값들이 서로 다른지 확인
        signals = {TradingConstants.BUY_SIGNAL, TradingConstants.SELL_SIGNAL, TradingConstants.HOLD_SIGNAL}
        self.assertEqual(len(signals), 3)


class TestTALibConstants(unittest.TestCase):
    """TA-Lib 지표 관련 상수 테스트"""
    
    def test_rsi_parameters(self):
        """RSI 매개변수가 유효한지 확인"""
        self.assertGreater(TALibConstants.RSI_PERIOD, 0)
        self.assertGreater(TALibConstants.RSI_OVERSOLD, 0)
        self.assertLess(TALibConstants.RSI_OVERSOLD, 50)
        self.assertGreater(TALibConstants.RSI_OVERBOUGHT, 50)
        self.assertLess(TALibConstants.RSI_OVERBOUGHT, 100)
        self.assertLess(TALibConstants.RSI_OVERSOLD, TALibConstants.RSI_OVERBOUGHT)
    
    def test_macd_parameters(self):
        """MACD 매개변수가 유효한지 확인"""
        self.assertGreater(TALibConstants.MACD_FAST_PERIOD, 0)
        self.assertGreater(TALibConstants.MACD_SLOW_PERIOD, 0)
        self.assertGreater(TALibConstants.MACD_SIGNAL_PERIOD, 0)
        self.assertLess(TALibConstants.MACD_FAST_PERIOD, TALibConstants.MACD_SLOW_PERIOD)
    
    def test_bollinger_bands_parameters(self):
        """볼린저 밴드 매개변수가 유효한지 확인"""
        self.assertGreater(TALibConstants.BB_PERIOD, 0)
        self.assertGreater(TALibConstants.BB_DEVIATION, 0)
        self.assertLess(TALibConstants.BB_DEVIATION, 5)  # 일반적으로 3 이하
    
    def test_moving_average_periods(self):
        """이동평균 기간이 논리적으로 올바른지 확인"""
        self.assertLess(TALibConstants.SMA_SHORT_PERIOD, TALibConstants.SMA_MEDIUM_PERIOD)
        self.assertLess(TALibConstants.SMA_MEDIUM_PERIOD, TALibConstants.SMA_LONG_PERIOD)
        self.assertLess(TALibConstants.EMA_SHORT_PERIOD, TALibConstants.EMA_LONG_PERIOD)


class TestSystemConstants(unittest.TestCase):
    """시스템 설정 관련 상수 테스트"""
    
    def test_database_settings(self):
        """데이터베이스 설정이 유효한지 확인"""
        self.assertTrue(SystemConstants.DEFAULT_DB_NAME.endswith('.db'))
        self.assertGreater(SystemConstants.CONNECTION_TIMEOUT, 0)
        self.assertGreater(SystemConstants.MAX_CONNECTIONS, 0)
    
    def test_cache_settings(self):
        """캐시 설정이 유효한지 확인"""
        self.assertGreater(SystemConstants.DEFAULT_CACHE_SIZE, 0)
        self.assertGreater(SystemConstants.CACHE_TTL_SECONDS, 0)
    
    def test_memory_thresholds(self):
        """메모리 임계값이 합리적인지 확인"""
        self.assertGreater(SystemConstants.MEMORY_WARNING_THRESHOLD_MB, 0)
        self.assertGreater(SystemConstants.GARBAGE_COLLECTION_INTERVAL, 0)


class TestOptimizationConstants(unittest.TestCase):
    """성능 최적화 관련 상수 테스트"""
    
    def test_optimization_thresholds(self):
        """최적화 임계값이 논리적으로 올바른지 확인"""
        self.assertLessEqual(OptimizationConstants.MIN_SYMBOLS_FOR_PARALLEL,
                            OptimizationConstants.MIN_SYMBOLS_FOR_BATCH)
        self.assertLessEqual(OptimizationConstants.MIN_SYMBOLS_FOR_CACHING,
                            OptimizationConstants.MIN_SYMBOLS_FOR_BATCH)
    
    def test_performance_thresholds(self):
        """성능 임계값이 논리적으로 올바른지 확인"""
        self.assertLess(OptimizationConstants.PERFORMANCE_VERY_FAST_THRESHOLD,
                       OptimizationConstants.PERFORMANCE_FAST_THRESHOLD)
        self.assertLess(OptimizationConstants.PERFORMANCE_FAST_THRESHOLD,
                       OptimizationConstants.PERFORMANCE_NORMAL_THRESHOLD)
    
    def test_timeout_settings(self):
        """타임아웃 설정이 합리적인지 확인"""
        self.assertGreater(OptimizationConstants.THREAD_POOL_TIMEOUT, 0)
        self.assertGreater(OptimizationConstants.TASK_TIMEOUT, 0)
        self.assertLess(OptimizationConstants.TASK_TIMEOUT, 
                       OptimizationConstants.THREAD_POOL_TIMEOUT)


class TestBacktestConstants(unittest.TestCase):
    """백테스팅 관련 상수 테스트"""
    
    def test_performance_thresholds(self):
        """성과 지표 임계값이 합리적인지 확인"""
        self.assertGreater(BacktestConstants.MIN_SHARPE_RATIO, 0)
        self.assertGreater(BacktestConstants.MIN_WIN_RATE, 0)
        self.assertLess(BacktestConstants.MIN_WIN_RATE, 1)
        self.assertGreater(BacktestConstants.MAX_DRAWDOWN_THRESHOLD, 0)
        self.assertLess(BacktestConstants.MAX_DRAWDOWN_THRESHOLD, 1)
    
    def test_trading_days_valid(self):
        """연간 거래일수가 합리적인지 확인"""
        self.assertGreater(BacktestConstants.TRADING_DAYS_PER_YEAR, 200)
        self.assertLess(BacktestConstants.TRADING_DAYS_PER_YEAR, 300)
    
    def test_benchmark_symbol_format(self):
        """벤치마크 심볼이 올바른 형식인지 확인"""
        self.assertIsInstance(BacktestConstants.BENCHMARK_SYMBOL, str)
        self.assertEqual(len(BacktestConstants.BENCHMARK_SYMBOL), 6)
        self.assertTrue(BacktestConstants.BENCHMARK_SYMBOL.isdigit())


class TestStrategyPresets(unittest.TestCase):
    """전략 프리셋 테스트"""
    
    def test_preset_structure(self):
        """모든 프리셋이 필수 키를 포함하는지 확인"""
        required_keys = ['rsi_period', 'rsi_oversold', 'rsi_overbought',
                        'macd_fast', 'macd_slow', 'macd_signal',
                        'bb_period', 'bb_deviation', 'volume_threshold',
                        'min_holding_days', 'max_holding_days']
        
        for preset_name in ['SWING_TRADING', 'DAY_TRADING', 'POSITION_TRADING']:
            preset = getattr(StrategyPresets, preset_name)
            for key in required_keys:
                self.assertIn(key, preset, f"{preset_name}에 {key} 키가 없습니다")
    
    def test_holding_periods_logical(self):
        """보유 기간이 논리적으로 올바른지 확인"""
        for preset_name in ['SWING_TRADING', 'DAY_TRADING', 'POSITION_TRADING']:
            preset = getattr(StrategyPresets, preset_name)
            self.assertLessEqual(preset['min_holding_days'], 
                               preset['max_holding_days'],
                               f"{preset_name}의 보유 기간이 잘못되었습니다")
            self.assertGreaterEqual(preset['min_holding_days'], 0)
    
    def test_day_trading_characteristics(self):
        """데이 트레이딩 특성이 올바른지 확인"""
        day_trading = StrategyPresets.DAY_TRADING
        self.assertEqual(day_trading['max_holding_days'], 1)
        self.assertLessEqual(day_trading['rsi_period'], 
                           StrategyPresets.SWING_TRADING['rsi_period'])


class TestConstantsValidation(unittest.TestCase):
    """상수 검증 함수 테스트"""
    
    def test_validate_constants_function(self):
        """validate_constants 함수가 올바르게 작동하는지 확인"""
        self.assertTrue(validate_constants())
    
    def test_constants_consistency(self):
        """상수들 간의 일관성 확인"""
        # 트레이딩 상수 일관성
        self.assertLess(TradingConstants.STOP_LOSS_PERCENT,
                       TradingConstants.MAX_DRAWDOWN_PERCENT)
        
        # 데이터 수집 일관성
        self.assertLess(DataCollectionConstants.DEFAULT_BACKTEST_DAYS,
                       DataCollectionConstants.DEFAULT_HISTORICAL_DAYS)
        
        # 최적화 일관성
        self.assertLessEqual(OptimizationConstants.MIN_SYMBOLS_FOR_PARALLEL,
                            DataCollectionConstants.PARALLEL_ENGINE_THRESHOLD)


class TestConstantsIntegration(unittest.TestCase):
    """상수 통합 테스트"""
    
    def test_trading_constants_dict(self):
        """TRADING_CONSTANTS 딕셔너리가 올바른지 확인"""
        from src.constants import TRADING_CONSTANTS
        
        self.assertEqual(TRADING_CONSTANTS['DEFAULT_INITIAL_CAPITAL'],
                        TradingConstants.DEFAULT_INITIAL_CAPITAL)
        self.assertEqual(TRADING_CONSTANTS['TRANSACTION_FEE_RATE'],
                        TradingConstants.TRANSACTION_FEE_RATE)
    
    def test_talib_constants_dict(self):
        """TALIB_CONSTANTS 딕셔너리가 올바른지 확인"""
        from src.constants import TALIB_CONSTANTS
        
        self.assertEqual(TALIB_CONSTANTS['RSI_PERIOD'],
                        TALibConstants.RSI_PERIOD)
        self.assertEqual(TALIB_CONSTANTS['MACD_FAST_PERIOD'],
                        TALibConstants.MACD_FAST_PERIOD)
    
    def test_system_constants_dict(self):
        """SYSTEM_CONSTANTS 딕셔너리가 올바른지 확인"""
        from src.constants import SYSTEM_CONSTANTS
        
        self.assertEqual(SYSTEM_CONSTANTS['DEFAULT_DB_NAME'],
                        SystemConstants.DEFAULT_DB_NAME)
        self.assertEqual(SYSTEM_CONSTANTS['DEFAULT_MAX_WORKERS'],
                        DataCollectionConstants.DEFAULT_MAX_WORKERS)


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(verbosity=2) 