"""
전략 서비스
매매 전략 관련 로직을 처리하는 서비스
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Type, Any, Tuple
import logging

from src.strategies.base_strategy import BaseStrategy, TradeSignal
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.bollinger_band_strategy import BollingerBandStrategy
from src.strategies.moving_average_strategy import MovingAverageStrategy


class StrategyService:
    """전략 관련 서비스"""
    
    def __init__(self):
        self._strategies = {
            'MACD': MACDStrategy,
            'RSI': RSIStrategy,
            'BollingerBand': BollingerBandStrategy,
            'MovingAverage': MovingAverageStrategy
        }
    
    def get_available_strategies(self) -> List[str]:
        """사용 가능한 전략 목록 반환"""
        return list(self._strategies.keys())
    
    def get_strategy_instance(self, strategy_name: str, **kwargs) -> Optional[BaseStrategy]:
        """전략 인스턴스 생성"""
        try:
            strategy_class = self._strategies.get(strategy_name)
            if strategy_class is None:
                logging.error(f"알 수 없는 전략: {strategy_name}")
                return None
            
            # 매개변수가 있으면 config 객체를 생성
            if kwargs:
                # 전략별로 적절한 config 클래스 생성
                if strategy_name == 'MACD':
                    from src.strategies.macd_strategy import MACDConfig
                    config = MACDConfig(**kwargs)
                elif strategy_name == 'RSI':
                    from src.strategies.rsi_strategy import RSIConfig
                    config = RSIConfig(**kwargs) if hasattr(strategy_class, 'ConfigClass') else None
                elif strategy_name == 'BollingerBand':
                    from src.strategies.bollinger_band_strategy import BollingerBandConfig
                    config = BollingerBandConfig(**kwargs) if hasattr(strategy_class, 'ConfigClass') else None
                elif strategy_name == 'MovingAverage':
                    from src.strategies.moving_average_strategy import MovingAverageConfig
                    config = MovingAverageConfig(**kwargs) if hasattr(strategy_class, 'ConfigClass') else None
                else:
                    config = None
                
                # config 객체가 있으면 이를 사용, 없으면 기본값으로 생성
                if config is not None:
                    return strategy_class(config=config)
                else:
                    # config 클래스가 없는 경우 기본 인스턴스 생성
                    return strategy_class()
            else:
                # 매개변수가 없으면 기본 인스턴스 생성
                return strategy_class()
            
        except Exception as e:
            logging.error(f"전략 인스턴스 생성 실패 {strategy_name}: {e}")
            return None
    
    def get_strategy_info(self, strategy_name: str) -> Dict[str, Any]:
        """전략 정보 반환"""
        strategy_info = {
            'MACD': {
                'name': 'MACD 전략',
                'description': 'MACD 선과 시그널선의 교차를 이용한 추세 추종 전략',
                'parameters': {
                    'fast_period': {'default': 12, 'min': 5, 'max': 50, 'type': 'int'},
                    'slow_period': {'default': 26, 'min': 10, 'max': 100, 'type': 'int'},
                    'signal_period': {'default': 9, 'min': 3, 'max': 30, 'type': 'int'}
                },
                'suitable_for': '추세가 명확한 시장',
                'risk_level': '중간'
            },
            'RSI': {
                'name': 'RSI 전략',
                'description': 'RSI 지표를 이용한 과매수/과매도 역추세 전략',
                'parameters': {
                    'rsi_period': {'default': 14, 'min': 5, 'max': 50, 'type': 'int'},
                    'oversold_threshold': {'default': 30, 'min': 10, 'max': 40, 'type': 'float'},
                    'overbought_threshold': {'default': 70, 'min': 60, 'max': 90, 'type': 'float'}
                },
                'suitable_for': '횡보 또는 변동성이 큰 시장',
                'risk_level': '중간'
            },
            'BollingerBand': {
                'name': '볼린저 밴드 전략',
                'description': '볼린저 밴드의 밴드 터치 및 돌파를 이용한 전략',
                'parameters': {
                    'period': {'default': 20, 'min': 10, 'max': 50, 'type': 'int'},
                    'std_dev': {'default': 2.0, 'min': 1.0, 'max': 3.0, 'type': 'float'}
                },
                'suitable_for': '변동성이 있는 시장',
                'risk_level': '중간'
            },
            'MovingAverage': {
                'name': '이동평균 전략',
                'description': '단기/장기 이동평균선의 교차를 이용한 전략',
                'parameters': {
                    'fast_period': {'default': 10, 'min': 5, 'max': 50, 'type': 'int'},
                    'slow_period': {'default': 30, 'min': 20, 'max': 200, 'type': 'int'}
                },
                'suitable_for': '추세가 있는 시장',
                'risk_level': '낮음'
            }
        }
        
        return strategy_info.get(strategy_name, {})
    
    def generate_signals(self, strategy_name: str, data: pd.DataFrame, symbol: str = "UNKNOWN", **kwargs) -> pd.DataFrame:
        """매매 신호 생성"""
        try:
            strategy = self.get_strategy_instance(strategy_name, **kwargs)
            if strategy is None:
                return pd.DataFrame()
            
            # 전략에 따라 symbol 매개변수 필요 여부가 다름
            try:
                signals = strategy.generate_signals(data, symbol)
            except TypeError:
                # symbol 매개변수를 받지 않는 전략인 경우
                try:
                    signals = strategy.generate_signals(data)
                except Exception:
                    return pd.DataFrame()
            
            # TradeSignal 리스트를 DataFrame으로 변환
            if isinstance(signals, list) and signals and isinstance(signals[0], TradeSignal):
                return self._signals_to_dataframe(signals)
            elif isinstance(signals, pd.DataFrame):
                return signals
            elif isinstance(signals, list):
                # 단순 신호 리스트인 경우 (예: [1, 0, -1, ...])
                result = pd.DataFrame({'signal': signals})
                if len(data) >= len(signals):
                    result.index = data.index[-len(signals):]  # 인덱스 맞춤
                return result
            else:
                return pd.DataFrame()
            
        except Exception as e:
            logging.error(f"신호 생성 실패 {strategy_name}: {e}")
            return pd.DataFrame()
    
    def _signals_to_dataframe(self, signals: List[TradeSignal]) -> pd.DataFrame:
        """TradeSignal 리스트를 DataFrame으로 변환"""
        if not signals:
            return pd.DataFrame()
        
        data = []
        for signal in signals:
            data.append({
                'timestamp': signal.timestamp,
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'price': signal.price,
                'confidence': signal.confidence,
                'reason': signal.reason,
                'risk_level': signal.risk_level
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('timestamp', inplace=True)
        return df
    
    def get_default_parameters(self, strategy_name: str) -> Dict[str, Any]:
        """전략의 기본 매개변수 반환"""
        strategy_info = self.get_strategy_info(strategy_name)
        if not strategy_info or 'parameters' not in strategy_info:
            return {}
        
        defaults = {}
        for param_name, param_info in strategy_info['parameters'].items():
            defaults[param_name] = param_info.get('default')
        
        return defaults
    
    def validate_parameters(self, strategy_name: str, parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """매개변수 유효성 검증"""
        try:
            strategy_info = self.get_strategy_info(strategy_name)
            if not strategy_info or 'parameters' not in strategy_info:
                return True, "매개변수 정보가 없습니다."
            
            for param_name, param_value in parameters.items():
                if param_name not in strategy_info['parameters']:
                    continue
                
                param_info = strategy_info['parameters'][param_name]
                param_type = param_info.get('type', 'float')
                min_val = param_info.get('min')
                max_val = param_info.get('max')
                
                # 타입 체크
                if param_type == 'int' and not isinstance(param_value, int):
                    return False, f"{param_name}은(는) 정수여야 합니다."
                elif param_type == 'float' and not isinstance(param_value, (int, float)):
                    return False, f"{param_name}은(는) 숫자여야 합니다."
                
                # 범위 체크
                if min_val is not None and param_value < min_val:
                    return False, f"{param_name}은(는) {min_val} 이상이어야 합니다."
                if max_val is not None and param_value > max_val:
                    return False, f"{param_name}은(는) {max_val} 이하여야 합니다."
            
            return True, "매개변수가 유효합니다."
            
        except Exception as e:
            return False, f"매개변수 검증 실패: {e}"


# 싱글톤 인스턴스
_strategy_service_instance = None

def get_strategy_service() -> StrategyService:
    """전략 서비스 싱글톤 인스턴스 반환"""
    global _strategy_service_instance
    if _strategy_service_instance is None:
        _strategy_service_instance = StrategyService()
    return _strategy_service_instance 