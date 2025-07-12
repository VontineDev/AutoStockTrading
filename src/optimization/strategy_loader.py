"""
전략 클래스/파라미터 범위 관리 모듈
- get_strategy_class, get_parameter_ranges 등
"""

from typing import Dict, List
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.bollinger_band_strategy import BollingerBandStrategy
from src.strategies.moving_average_strategy import MovingAverageStrategy
import logging


def get_strategy_class(strategy_type: str):
    """
    전략 타입에 따라 실제 전략 클래스를 반환
    """
    logger = logging.getLogger(__name__)
    logger.info(f"get_strategy_class: strategy_type={strategy_type}")
    mapping = {
        # MACD
        "macd": MACDStrategy,
        "macd_strategy": MACDStrategy,
        "MACD": MACDStrategy,
        "맥디": MACDStrategy,
        # RSI
        "rsi": RSIStrategy,
        "rsi_strategy": RSIStrategy,
        "RSI": RSIStrategy,
        # 볼린저밴드
        "bollinger": BollingerBandStrategy,
        "bollingerband": BollingerBandStrategy,
        "bollinger_band": BollingerBandStrategy,
        "bollinger_band_strategy": BollingerBandStrategy,
        "볼린저밴드": BollingerBandStrategy,
        # 이동평균
        "ma": MovingAverageStrategy,
        "moving_average": MovingAverageStrategy,
        "movingaveragestrategy": MovingAverageStrategy,
        "moving_average_strategy": MovingAverageStrategy,
        "이동평균": MovingAverageStrategy,
    }
    class DummyStrategy:
        def __init__(self):
            self.parameters = {}
        def run_strategy(self, data, symbol):
            pass
    return mapping.get(str(strategy_type).lower(), DummyStrategy)
