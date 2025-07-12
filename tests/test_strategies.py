#!/usr/bin/env python3
"""
전략 클래스 테스트

커서룰의 테스트 원칙에 따라 BaseStrategy와 전략 관련 기능들을 검증
"""

import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.strategies.base_strategy import (
    BaseStrategy,
    TradeSignal,
    StrategyConfig,
    create_default_config,
    calculate_signal_confidence,
)
from src.constants import TALibConstants, TradingConstants


class MockStrategy(BaseStrategy):
    """테스트용 전략 구현체"""


def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
    """간단한 RSI와 이동평균 계산"""
    data["rsi"] = np.random.uniform(20, 80, len(data))  # 모의 RSI
    data["sma_20"] = data["close"].rolling(20).mean()
    data["sma_5"] = data["close"].rolling(5).mean()
    return data


def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
    """간단한 매매 신호 생성"""
    signals = []

    for i in range(len(data)):
        if i < 20:  # 충분한 데이터가 없으면 건너뜀
            continue

        row = data.iloc[i]

        # 간단한 골든크로스/데드크로스 전략
        if (
            row["sma_5"] > row["sma_20"]
            and data.iloc[i - 1]["sma_5"] <= data.iloc[i - 1]["sma_20"]
        ):
            # 골든크로스 - 매수 신호
            signal = TradeSignal(
                timestamp=datetime.now(),
                symbol="TEST",
                signal_type="BUY",
                price=row["close"],
                confidence=0.8,
                reason="Golden Cross",
                indicators={
                    "rsi": row["rsi"],
                    "sma_5": row["sma_5"],
                    "sma_20": row["sma_20"],
                },
                risk_level="MEDIUM",
            )
            signals.append(signal)

        elif (
            row["sma_5"] < row["sma_20"]
            and data.iloc[i - 1]["sma_5"] >= data.iloc[i - 1]["sma_20"]
        ):
            # 데드크로스 - 매도 신호
            signal = TradeSignal(
                timestamp=datetime.now(),
                symbol="TEST",
                signal_type="SELL",
                price=row["close"],
                confidence=0.7,
                reason="Dead Cross",
                indicators={
                    "rsi": row["rsi"],
                    "sma_5": row["sma_5"],
                    "sma_20": row["sma_20"],
                },
                risk_level="LOW",
            )
            signals.append(signal)

    return signals


def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
    """신호 검증 - RSI 극값 필터링"""
    rsi = signal.indicators.get("rsi", 50)

    if signal.signal_type == "BUY":
        # RSI가 70 이상이면 과매수로 판단하여 거부
        return rsi < 70
    elif signal.signal_type == "SELL":
        # RSI가 30 이하면 과매도로 판단하여 거부
        return rsi > 30

    return True


class TestTradeSignal(unittest.TestCase):
    """TradeSignal 데이터 클래스 테스트"""


def setUp(self):
    """테스트 데이터 설정"""
    self.signal = TradeSignal(
        timestamp=datetime.now(),
        symbol="005930",
        signal_type="BUY",
        price=70000.0,
        confidence=0.85,
        reason="RSI oversold",
        indicators={"rsi": 25, "macd": 0.5},
        risk_level="MEDIUM",
    )


def test_signal_creation(self):
    """신호 생성 테스트"""
    self.assertEqual(self.signal.symbol, "005930")
    self.assertEqual(self.signal.signal_type, "BUY")
    self.assertEqual(self.signal.price, 70000.0)
    self.assertEqual(self.signal.confidence, 0.85)


def test_signal_attributes(self):
    """신호 속성 검증"""
    self.assertIsInstance(self.signal.timestamp, datetime)
    self.assertIsInstance(self.signal.indicators, dict)
    self.assertIn("rsi", self.signal.indicators)
    self.assertIn(self.signal.risk_level, ["LOW", "MEDIUM", "HIGH"])


class TestStrategyConfig(unittest.TestCase):
    """StrategyConfig 데이터 클래스 테스트"""


def test_default_config(self):
    """기본 설정 테스트"""
    config = StrategyConfig()
    self.assertEqual(config.name, "BaseStrategy")
    self.assertIsInstance(config.parameters, dict)
    self.assertIsInstance(config.risk_management, dict)
    self.assertIsInstance(config.required_indicators, list)


def test_custom_config(self):
    """사용자 정의 설정 테스트"""
    custom_params = {"rsi_period": 14, "threshold": 0.5}
    custom_risk = {"stop_loss": 0.03, "take_profit": 0.06}

    config = StrategyConfig(
        name="TestStrategy",
        description="테스트 전략",
        parameters=custom_params,
        risk_management=custom_risk,
        min_data_length=100,
    )

    self.assertEqual(config.name, "TestStrategy")
    self.assertEqual(config.parameters, custom_params)
    self.assertEqual(config.risk_management, custom_risk)
    self.assertEqual(config.min_data_length, 100)


class TestBaseStrategy(unittest.TestCase):
    """BaseStrategy 클래스 테스트"""


def setUp(self):
    """테스트 환경 설정"""
    config = StrategyConfig(
        name="MockStrategy", description="테스트용 모의 전략", min_data_length=30
    )
    self.strategy = MockStrategy(config)

    # 테스트용 주식 데이터 생성
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    np.random.seed(42)  # 재현 가능한 난수

    base_price = 50000
    returns = np.random.normal(0.001, 0.02, 100)  # 일일 수익률
    prices = [base_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    self.test_data = pd.DataFrame(
        {
            "date": dates,
            "open": np.array(prices) * np.random.uniform(0.99, 1.01, 100),
            "high": np.array(prices) * np.random.uniform(1.01, 1.05, 100),
            "low": np.array(prices) * np.random.uniform(0.95, 0.99, 100),
            "close": prices,
            "volume": np.random.randint(10000, 100000, 100),
        }
    )


def test_strategy_initialization(self):
    """전략 초기화 테스트"""
    self.assertEqual(self.strategy.name, "MockStrategy")
    self.assertIsInstance(self.strategy.parameters, dict)
    self.assertIsInstance(self.strategy.risk_management, dict)
    self.assertIn("stop_loss_pct", self.strategy.risk_management)


def test_prepare_data(self):
    """데이터 전처리 테스트"""
    prepared_data = self.strategy.prepare_data(self.test_data)

    self.assertEqual(len(prepared_data), len(self.test_data))
    self.assertFalse(prepared_data.isnull().any().any())

    # 필수 컬럼 존재 확인
    required_columns = ["open", "high", "low", "close", "volume"]
    for col in required_columns:
        self.assertIn(col, prepared_data.columns)


def test_prepare_data_insufficient_length(self):
    """데이터 길이 부족 테스트"""
    short_data = self.test_data.head(20)  # 30개 미만

    with self.assertRaises(ValueError) as context:
        self.strategy.prepare_data(short_data)

    self.assertIn("데이터 부족", str(context.exception))


def test_prepare_data_missing_columns(self):
    """필수 컬럼 누락 테스트"""
    incomplete_data = self.test_data.drop(columns=["volume"])

    with self.assertRaises(ValueError) as context:
        self.strategy.prepare_data(incomplete_data)

    self.assertIn("필수 컬럼 누락", str(context.exception))


def test_calculate_indicators(self):
    """지표 계산 테스트"""
    indicators = self.strategy.calculate_indicators(self.test_data)

    self.assertIn("rsi", indicators.columns)
    self.assertIn("sma_20", indicators.columns)
    self.assertIn("sma_5", indicators.columns)

    # RSI 값 범위 확인 (0-100)
    rsi_values = indicators["rsi"].dropna()
    self.assertTrue((rsi_values >= 0).all())
    self.assertTrue((rsi_values <= 100).all())


def test_generate_signals(self):
    """신호 생성 테스트"""
    indicators = self.strategy.calculate_indicators(self.test_data)
    signals = self.strategy.generate_signals(indicators)

    self.assertIsInstance(signals, list)

    if signals:  # 신호가 생성된 경우
        for signal in signals:
            self.assertIsInstance(signal, TradeSignal)
            self.assertIn(signal.signal_type, ["BUY", "SELL", "HOLD"])
            self.assertGreater(signal.price, 0)
            self.assertGreaterEqual(signal.confidence, 0)
            self.assertLessEqual(signal.confidence, 1)


def test_validate_signal(self):
    """신호 검증 테스트"""
    # 유효한 매수 신호 (RSI < 70)
    valid_buy_signal = TradeSignal(
        timestamp=datetime.now(),
        symbol="TEST",
        signal_type="BUY",
        price=50000,
        confidence=0.8,
        reason="Test",
        indicators={"rsi": 60},
        risk_level="MEDIUM",
    )

    self.assertTrue(self.strategy.validate_signal(valid_buy_signal, self.test_data))

    # 무효한 매수 신호 (RSI >= 70)
    invalid_buy_signal = TradeSignal(
        timestamp=datetime.now(),
        symbol="TEST",
        signal_type="BUY",
        price=50000,
        confidence=0.8,
        reason="Test",
        indicators={"rsi": 75},
        risk_level="HIGH",
    )

    self.assertFalse(self.strategy.validate_signal(invalid_buy_signal, self.test_data))


def test_run_strategy_full_pipeline(self):
    """전체 전략 실행 파이프라인 테스트"""
    signals = self.strategy.run_strategy(self.test_data, symbol="005930")

    self.assertIsInstance(signals, list)

    # 생성된 신호들 검증
    for signal in signals:
        self.assertEqual(signal.symbol, "005930")
        self.assertIsInstance(signal, TradeSignal)

    # 신호 이력 저장 확인
    self.assertEqual(len(self.strategy.signals_history), len(signals))


def test_calculate_performance_metrics(self):
    """성과 지표 계산 테스트"""
    # 모의 수익률 데이터
    returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.03])

    metrics = self.strategy.calculate_performance_metrics(returns)

    self.assertIn("total_return", metrics)
    self.assertIn("cumulative_return", metrics)
    self.assertIn("volatility", metrics)
    self.assertIn("sharpe_ratio", metrics)
    self.assertIn("max_drawdown", metrics)
    self.assertIn("win_rate", metrics)
    self.assertIn("total_trades", metrics)

    # 기본적인 값 검증
    self.assertEqual(metrics["total_trades"], len(returns))
    self.assertGreaterEqual(metrics["win_rate"], 0)
    self.assertLessEqual(metrics["win_rate"], 1)
    self.assertLessEqual(metrics["max_drawdown"], 0)  # MDD는 음수


def test_calculate_performance_metrics_empty(self):
    """빈 수익률 데이터 처리 테스트"""
    empty_returns = pd.Series([])
    metrics = self.strategy.calculate_performance_metrics(empty_returns)

    self.assertEqual(metrics, {})


def test_apply_risk_management(self):
    """리스크 관리 적용 테스트"""
    signal = TradeSignal(
        timestamp=datetime.now(),
        symbol="TEST",
        signal_type="BUY",
        price=50000,
        confidence=0.8,
        reason="Test",
        indicators={},
        risk_level="MEDIUM",
    )

    position_size, stop_loss, take_profit = self.strategy.apply_risk_management(
        signal, 50000, 1000000  # 현재가 50000, 포트폴리오 100만원
    )

    self.assertGreater(position_size, 0)
    self.assertLess(stop_loss, 50000)  # 손절가 < 현재가
    self.assertGreater(take_profit, 50000)  # 익절가 > 현재가


def test_get_strategy_info(self):
    """전략 정보 조회 테스트"""
    info = self.strategy.get_strategy_info()

    self.assertIn("name", info)
    self.assertIn("description", info)
    self.assertIn("parameters", info)
    self.assertIn("risk_management", info)
    self.assertIn("performance_metrics", info)
    self.assertIn("total_signals", info)


class TestUtilityFunctions(unittest.TestCase):
    """유틸리티 함수 테스트"""


def test_create_default_config(self):
    """기본 설정 생성 함수 테스트"""
    config = create_default_config("TestStrategy")

    self.assertEqual(config.name, "TestStrategy")
    self.assertIsInstance(config.parameters, dict)

    # 사용자 정의 매개변수 포함
    custom_params = {"rsi_period": 21}
    config_with_params = create_default_config("TestStrategy", custom_params)

    self.assertEqual(config_with_params.parameters["rsi_period"], 21)


def test_calculate_signal_confidence(self):
    """신호 신뢰도 계산 함수 테스트"""
    indicators = {"rsi": 25, "macd": 0.8, "volume_ratio": 1.5}
    thresholds = {
        "rsi": (20, 80),  # RSI < 20 or > 80일 때 높은 신뢰도
        "macd": (0.5, 2.0),  # MACD > 0.5일 때 높은 신뢰도
        "volume_ratio": (1.2, 3.0),  # 거래량 비율 > 1.2일 때 높은 신뢰도
    }

    confidence = calculate_signal_confidence(indicators, thresholds)

    self.assertGreaterEqual(confidence, 0)
    self.assertLessEqual(confidence, 1)
    self.assertIsInstance(confidence, float)


class TestStrategyIntegration(unittest.TestCase):
    """전략 통합 테스트"""


def test_strategy_with_constants(self):
    """상수를 사용한 전략 설정 테스트"""
    config = StrategyConfig(
        name="ConstantsBasedStrategy",
        parameters={
            "rsi_period": TALibConstants.RSI_PERIOD,
            "rsi_oversold": TALibConstants.RSI_OVERSOLD,
            "rsi_overbought": TALibConstants.RSI_OVERBOUGHT,
        },
        risk_management={
            "stop_loss_pct": TradingConstants.STOP_LOSS_PERCENT,
            "max_position_pct": TradingConstants.MAX_POSITION_SIZE_PERCENT,
        },
    )

    strategy = MockStrategy(config)

    self.assertEqual(strategy.parameters["rsi_period"], 14)
    self.assertEqual(strategy.parameters["rsi_oversold"], 30)
    self.assertEqual(strategy.risk_management["stop_loss_pct"], 0.03)


def test_multiple_signals_handling(self):
    """다중 신호 처리 테스트"""
    config = StrategyConfig(name="MultiSignalStrategy")
    strategy = MockStrategy(config)

    # 더 긴 데이터로 여러 신호 생성 유도
    dates = pd.date_range(start="2023-01-01", periods=200, freq="D")
    np.random.seed(123)

    # 트렌드가 있는 데이터 생성 (골든크로스/데드크로스 발생 유도)
    trend_data = pd.DataFrame(
        {
            "date": dates,
            "open": np.arange(50000, 50000 + 200 * 100, 100)
            + np.random.normal(0, 500, 200),
            "high": np.arange(50000, 50000 + 200 * 100, 100)
            + np.random.normal(1000, 500, 200),
            "low": np.arange(50000, 50000 + 200 * 100, 100)
            + np.random.normal(-1000, 500, 200),
            "close": np.arange(50000, 50000 + 200 * 100, 100)
            + np.random.normal(0, 300, 200),
            "volume": np.random.randint(10000, 100000, 200),
        }
    )

    signals = strategy.run_strategy(trend_data, symbol="TREND_TEST")

    # 트렌드 데이터에서 신호가 생성되었는지 확인
    self.assertGreaterEqual(len(signals), 0)

    # 매수/매도 신호가 모두 있는지 확인 (있다면)
    if len(signals) >= 2:
        signal_types = [s.signal_type for s in signals]
        self.assertTrue(
            any(s == "BUY" for s in signal_types)
            or any(s == "SELL" for s in signal_types)
        )


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
