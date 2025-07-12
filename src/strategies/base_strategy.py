"""
스윙 트레이딩 전략 기본 클래스

모든 매매 전략의 기본이 되는 추상 클래스를 정의합니다.
TA-Lib 지표를 활용한 스윙 트레이딩에 최적화되어 있습니다.
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TradeSignal:
    """매매 신호 데이터 클래스"""
    timestamp: datetime
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    price: float
    confidence: float  # 0.0 ~ 1.0
    reason: str
    indicators: Dict[str, float]
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH'

@dataclass
class StrategyConfig:
    """전략 설정 데이터 클래스"""
    name: str = "BaseStrategy"
    description: str = "기본 전략"
    parameters: Dict[str, Any] = None
    risk_management: Dict[str, float] = None
    min_data_length: int = 50
    required_indicators: List[str] = None
    
def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.risk_management is None:
            self.risk_management = {}
        if self.required_indicators is None:
            self.required_indicators = []

class BaseStrategy(ABC):
    """스윙 트레이딩 전략 기본 클래스"""
    
def __init__(self, config: StrategyConfig):
        """
        Args:
            config: 전략 설정
        """
        self.config = config
        self.name = config.name
        self.parameters = config.parameters
        self.risk_management = config.risk_management
        self.signals_history: List[TradeSignal] = []
        self.performance_metrics: Dict[str, float] = {}
        
        # 기본 리스크 관리 설정
        self.default_risk_settings = {
            'stop_loss_pct': 0.03,  # 3% 손절
            'take_profit_pct': 0.06,  # 6% 익절
            'position_size_pct': 0.2,  # 포트폴리오의 20%
            'max_positions': 5  # 최대 보유 종목 수
        }
        self.risk_management = {**self.default_risk_settings, **self.risk_management}
        
        logger.info(f"전략 '{self.name}' 초기화 완료")
    
    @abstractmethod
def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        전략에 필요한 기술적 지표 계산 (TA-Lib 사용)
        
        Args:
            data: OHLCV 데이터
            
        Returns:
            지표가 추가된 데이터프레임
        """
        pass
    
    @abstractmethod
def generate_signals(self, data: pd.DataFrame) -> List[TradeSignal]:
        """
        매매 신호 생성
        
        Args:
            data: 지표가 계산된 데이터
            
        Returns:
            매매 신호 리스트
        """
        pass
    
    @abstractmethod
def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """
        매매 신호 검증 (리스크 관리 포함)
        
        Args:
            signal: 검증할 신호
            data: 현재 데이터
            
        Returns:
            신호 유효성 여부
        """
        pass
    
def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """데이터 전처리 및 검증"""
        if len(data) < self.config.min_data_length:
            raise ValueError(f"데이터 부족: 최소 {self.config.min_data_length}개 필요, 현재 {len(data)}개")
        
        # 기본 컬럼 검증
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼 누락: {missing_columns}")
        
        # 데이터 정렬 (날짜순)
        if 'date' in data.columns:
            data = data.sort_values('date').reset_index(drop=True)
        
        # 결측값 처리
        data = data.ffill().bfill()
        
        return data
    
def run_strategy(self, data: pd.DataFrame, symbol: str = "UNKNOWN") -> List[TradeSignal]:
        """
        전략 실행 (전체 파이프라인)
        
        Args:
            data: OHLCV 데이터
            symbol: 종목 코드
            
        Returns:
            검증된 매매 신호 리스트
        """
        try:
            # 1. 데이터 전처리
            processed_data = self.prepare_data(data)
            
            # 2. 지표 계산
            indicator_data = self.calculate_indicators(processed_data)
            
            # 3. 신호 생성
            raw_signals = self.generate_signals(indicator_data)
            
            # 4. 신호 검증 및 필터링
            validated_signals = []
            for signal in raw_signals:
                signal.symbol = symbol
                if self.validate_signal(signal, indicator_data):
                    validated_signals.append(signal)
            
            # 5. 신호 이력 저장
            self.signals_history.extend(validated_signals)
            
            logger.info(f"전략 '{self.name}' 실행 완료: {len(validated_signals)}개 신호 생성")
            return validated_signals
            
        except Exception as e:
            logger.error(f"전략 실행 중 오류 발생: {e}")
            raise
    
def calculate_performance_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """성과 지표 계산"""
        if len(returns) == 0:
            return {}
        
        metrics = {
            'total_return': returns.sum(),
            'cumulative_return': (1 + returns).prod() - 1,
            'volatility': returns.std() * np.sqrt(252),  # 연환산
            'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0,
            'max_drawdown': self._calculate_max_drawdown(returns),
            'win_rate': (returns > 0).mean(),
            'avg_win': returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0,
            'avg_loss': returns[returns < 0].mean() if len(returns[returns < 0]) > 0 else 0,
            'total_trades': len(returns)
        }
        
        self.performance_metrics = metrics
        return metrics
    
def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """최대 낙폭(MDD) 계산"""
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        return drawdown.min()
    
def apply_risk_management(self, signal: TradeSignal, current_price: float, 
                            portfolio_value: float) -> Tuple[float, float, float]:
        """
        리스크 관리 적용
        
        Args:
            signal: 매매 신호
            current_price: 현재 가격
            portfolio_value: 포트폴리오 총 가치
            
        Returns:
            (포지션 크기, 손절가격, 익절가격)
        """
        # 포지션 크기 계산 (포트폴리오 비율 기준)
        position_value = portfolio_value * self.risk_management['position_size_pct']
        position_size = position_value / current_price
        
        # 손절/익절 가격 계산
        if signal.signal_type == 'BUY':
            stop_loss_price = current_price * (1 - self.risk_management['stop_loss_pct'])
            take_profit_price = current_price * (1 + self.risk_management['take_profit_pct'])
        else:  # SELL
            stop_loss_price = current_price * (1 + self.risk_management['stop_loss_pct'])
            take_profit_price = current_price * (1 - self.risk_management['take_profit_pct'])
        
        return position_size, stop_loss_price, take_profit_price
    
def get_strategy_info(self) -> Dict[str, Any]:
        """전략 정보 반환"""
        return {
            'name': self.name,
            'description': self.config.description,
            'parameters': self.parameters,
            'risk_management': self.risk_management,
            'required_indicators': self.config.required_indicators,
            'min_data_length': self.config.min_data_length,
            'total_signals': len(self.signals_history),
            'performance_metrics': self.performance_metrics
        }
    
def optimize_parameters(self, data: pd.DataFrame, parameter_ranges: Dict[str, List]) -> Dict[str, Any]:
        """
        매개변수 최적화 (그리드 서치)
        
        Args:
            data: 백테스팅 데이터
            parameter_ranges: 매개변수 범위 딕셔너리
            
        Returns:
            최적 매개변수 및 성과
        """
        from itertools import product
        
        best_params = None
        best_performance = -float('inf')
        best_metrics = {}
        
        # 매개변수 조합 생성
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())
        
        logger.info(f"매개변수 최적화 시작: {len(list(product(*param_values)))}개 조합")
        
        for i, param_combination in enumerate(product(*param_values)):
            # 현재 매개변수 조합 적용
            current_params = dict(zip(param_names, param_combination))
            original_params = self.parameters.copy()
            self.parameters.update(current_params)
            
            try:
                # 백테스팅 실행
                signals = self.run_strategy(data)
                
                # 수익률 계산 (간단한 버전)
                if signals:
                    returns = self._calculate_simple_returns(signals, data)
                    metrics = self.calculate_performance_metrics(returns)
                    
                    # 샤프 비율 기준 최적화
                    performance_score = metrics.get('sharpe_ratio', -float('inf'))
                    
                    if performance_score > best_performance:
                        best_performance = performance_score
                        best_params = current_params.copy()
                        best_metrics = metrics.copy()
                
            except Exception as e:
                logger.warning(f"매개변수 조합 {current_params}에서 오류: {e}")
            
            finally:
                # 원래 매개변수 복원
                self.parameters = original_params
        
        # 최적 매개변수 적용
        if best_params:
            self.parameters.update(best_params)
            logger.info(f"최적화 완료: {best_params}, 샤프 비율: {best_performance:.4f}")
        
        return {
            'best_parameters': best_params,
            'best_performance': best_performance,
            'best_metrics': best_metrics
        }
    
def _calculate_simple_returns(self, signals: List[TradeSignal], data: pd.DataFrame) -> pd.Series:
        """간단한 수익률 계산 (매개변수 최적화용)"""
        returns = []
        
        for i in range(len(signals) - 1):
            current_signal = signals[i]
            next_signal = signals[i + 1]
            
            if current_signal.signal_type == 'BUY' and next_signal.signal_type == 'SELL':
                ret = (next_signal.price - current_signal.price) / current_signal.price
                returns.append(ret)
            elif current_signal.signal_type == 'SELL' and next_signal.signal_type == 'BUY':
                ret = (current_signal.price - next_signal.price) / current_signal.price
                returns.append(ret)
        
        return pd.Series(returns) if returns else pd.Series([])

# 유틸리티 함수들
def create_default_config(strategy_name: str, parameters: Dict[str, Any] = None,
                         risk_settings: Dict[str, float] = None) -> StrategyConfig:
    """기본 전략 설정 생성"""
    return StrategyConfig(
        name=strategy_name,
        description=f"{strategy_name} 스윙 트레이딩 전략",
        parameters=parameters or {},
        risk_management=risk_settings or {},
        min_data_length=50
    )

def calculate_signal_confidence(indicators: Dict[str, float], thresholds: Dict[str, Tuple[float, float]]) -> float:
    """지표 기반 신호 신뢰도 계산"""
    confidence_scores = []
    
    for indicator, value in indicators.items():
        if indicator in thresholds:
            min_threshold, max_threshold = thresholds[indicator]
            if min_threshold <= value <= max_threshold:
                confidence_scores.append(1.0)
            else:
                # 임계값에서 벗어난 정도에 따라 신뢰도 감소
                distance = min(abs(value - min_threshold), abs(value - max_threshold))
                max_distance = max(abs(max_threshold - min_threshold), 1.0)
                confidence_scores.append(max(0.0, 1.0 - distance / max_distance))
    
    return np.mean(confidence_scores) if confidence_scores else 0.5

if __name__ == "__main__":
    # 테스트 코드
    print("Base Strategy 모듈 테스트")
    config = create_default_config("테스트전략", {"param1": 10}, {"stop_loss_pct": 0.02})
    print(f"기본 설정: {config}") 