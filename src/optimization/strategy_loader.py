"""
전략 클래스/파라미터 범위 관리 모듈
- get_strategy_class, get_parameter_ranges 등
"""
from typing import Dict, List

def get_parameter_ranges(strategy_type: str) -> Dict[str, List]:
    """
    전략별 매개변수 범위 반환
    """
    if strategy_type == "MACD":
        return {
            'fast_period': list(range(8, 16)),
            'slow_period': list(range(20, 31, 2)),
            'signal_period': list(range(7, 13)),
            'histogram_threshold': [0.0, 0.1]
        }
    elif strategy_type == "RSI":
        return {
            'rsi_period': [10, 12, 14, 16, 18, 20],
            'overbought_threshold': [65, 70, 75, 80],
            'oversold_threshold': [20, 25, 30, 35]
        }
    elif strategy_type == "볼린저밴드":
        return {
            'bb_period': [15, 20, 25, 30],
            'bb_deviation': [1.5, 2.0, 2.5, 3.0]
        }
    elif strategy_type == "이동평균":
        return {
            'short_period': [3, 5, 7, 10],
            'long_period': [15, 20, 25, 30]
        }
    return {}

def get_strategy_class(strategy_type: str):
    """
    전략 타입에 따라 전략 클래스 반환 (더미 예시)
    실제 구현에서는 각 전략 모듈 import 필요
    """
    class DummyStrategy:
def __init__(self):
            self.parameters = {}
def run_strategy(self, data, symbol):
            pass
    return DummyStrategy 