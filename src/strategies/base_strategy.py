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

# indicators.py 통합
from src.data.indicators import TALibIndicators, get_indicator_info, SWING_TRADING_PARAMS

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
    parameters: Optional[Dict[str, Any]] = None
    risk_management: Optional[Dict[str, float]] = None
    min_data_length: int = 20
    required_indicators: Optional[List[str]] = None

    def __post_init__(self):
        if self.risk_management is None:
            self.risk_management = {}
        if self.parameters is None:
            self.parameters = {}
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
        self.parameters: Dict[str, Any] = config.parameters or {}
        self.signals_history: List[TradeSignal] = []
        self.performance_metrics: Dict[str, float] = {}

        # 기본 리스크 관리 설정
        self.default_risk_settings = {
            "stop_loss_pct": 0.03,  # 3% 손절
            "take_profit_pct": 0.06,  # 6% 익절
            "position_size_pct": 0.2,  # 포트폴리오의 20%
            "max_positions": 5,  # 최대 보유 종목 수
        }
        self.risk_management: Dict[str, float] = {**self.default_risk_settings, **(config.risk_management or {})}

        logger.info(f"전략 '{self.name}' 초기화 완료")

    def calculate_all_indicators(self, data: pd.DataFrame, custom_params: Optional[Dict] = None) -> pd.DataFrame:
        """
        통합된 기술적 지표 계산 (indicators.py 활용)
        
        Args:
            data: OHLCV 데이터
            custom_params: 사용자 정의 매개변수 (선택사항)
            
        Returns:
            모든 지표가 계산된 데이터프레임
        """
        try:
            # 데이터 검증 및 전처리
            if data.empty:
                logger.warning("빈 데이터프레임이 전달되었습니다.")
                return data.copy()
            
            # 필수 컬럼 확인
            required_columns = ["open", "high", "low", "close", "volume"]
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                logger.error(f"필수 컬럼이 누락되었습니다: {missing_columns}")
                logger.info(f"사용 가능한 컬럼: {list(data.columns)}")
                return data.copy()
            
            # 데이터 길이 확인
            if len(data) < 50:
                logger.warning(f"데이터가 부족합니다. 최소 50개 필요, 현재 {len(data)}개")
                # 최소 데이터 요구사항을 낮춤
                if len(data) < 20:
                    logger.error("데이터가 너무 부족하여 지표 계산을 건너뜁니다.")
                    return data.copy()
            
            # TALibIndicators 인스턴스 생성
            calculator = TALibIndicators(data)
            
            # 모든 지표 계산
            if custom_params:
                df_with_indicators = calculator.calculate_custom_indicators(data, custom_params)
            else:
                df_with_indicators = calculator.calculate_all_indicators()
            
            # 지표 계산 결과 확인
            original_columns = set(data.columns)
            new_columns = set(df_with_indicators.columns) - original_columns
            
            if not new_columns:
                logger.warning("지표가 계산되지 않았습니다. 기본 지표만 추가합니다.")
                # 기본 지표 수동 계산
                df_with_indicators = self._calculate_basic_indicators(data)
            
            logger.info(f"기술적 지표 계산 완료: {len(new_columns)}개 지표 추가")
            return df_with_indicators
            
        except Exception as e:
            logger.error(f"지표 계산 실패: {e}")
            logger.info("기본 지표 계산으로 대체합니다.")
            # 실패 시 기본 지표만 계산
            return self._calculate_basic_indicators(data)
    
    def _calculate_basic_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """기본 지표만 계산 (fallback)"""
        try:
            df = data.copy()
            
            # 기본 이동평균
            df["SMA_20"] = df["close"].rolling(window=20).mean()
            df["SMA_50"] = df["close"].rolling(window=50).mean()
            
            # 기본 RSI (pandas로 계산)
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))
            
            # 기본 볼린저 밴드
            df["BB_middle"] = df["close"].rolling(window=20).mean()
            bb_std = df["close"].rolling(window=20).std()
            df["BB_upper"] = df["BB_middle"] + (bb_std * 2)
            df["BB_lower"] = df["BB_middle"] - (bb_std * 2)
            
            # 기본 거래량 지표
            df["volume_sma"] = df["volume"].rolling(window=20).mean()
            df["volume_ratio"] = df["volume"] / df["volume_sma"]
            
            logger.info("기본 지표 계산 완료 (fallback)")
            return df
            
        except Exception as e:
            logger.error(f"기본 지표 계산도 실패: {e}")
            return data.copy()

    def get_trading_signals_from_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        indicators.py의 매매 신호 생성 기능 활용
        
        Args:
            data: 지표가 계산된 데이터
            
        Returns:
            매매 신호가 추가된 데이터프레임
        """
        try:
            calculator = TALibIndicators(data)
            return calculator.get_trading_signals(data)
        except Exception as e:
            logger.error(f"매매 신호 생성 실패: {e}")
            return data.copy()

    def calculate_specific_indicators(self, data: pd.DataFrame, indicator_types: List[str]) -> pd.DataFrame:
        """
        특정 카테고리의 지표만 계산
        
        Args:
            data: OHLCV 데이터
            indicator_types: ['trend', 'momentum', 'volatility', 'volume'] 중 선택
            
        Returns:
            선택된 지표가 계산된 데이터프레임
        """
        try:
            calculator = TALibIndicators(data)
            df_result = data.copy()
            
            if 'trend' in indicator_types:
                trend_df = calculator.calculate_trend_indicators()
                new_columns = [col for col in trend_df.columns if col not in df_result.columns]
                df_result[new_columns] = trend_df[new_columns]
            
            if 'momentum' in indicator_types:
                momentum_df = calculator.calculate_momentum_indicators()
                new_columns = [col for col in momentum_df.columns if col not in df_result.columns]
                df_result[new_columns] = momentum_df[new_columns]
            
            if 'volatility' in indicator_types:
                volatility_df = calculator.calculate_volatility_indicators()
                new_columns = [col for col in volatility_df.columns if col not in df_result.columns]
                df_result[new_columns] = volatility_df[new_columns]
            
            if 'volume' in indicator_types:
                volume_df = calculator.calculate_volume_indicators()
                new_columns = [col for col in volume_df.columns if col not in df_result.columns]
                df_result[new_columns] = volume_df[new_columns]
            
            return df_result
            
        except Exception as e:
            logger.error(f"선택 지표 계산 실패: {e}")
            return data.copy()

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        전략별 특화 지표 계산 (필요시 calculate_all_indicators 활용 권장)
        
        Args:
            data: OHLCV 데이터

        Returns:
            지표가 추가된 데이터프레임
        """
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """매매 신호 생성"""
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
            raise ValueError(
                f"데이터 부족: 최소 {self.config.min_data_length}개 필요, 현재 {len(data)}개"
            )

        # 기본 컬럼 검증
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼 누락: {missing_columns}")

        # 데이터 정렬 (날짜순)
        if "date" in data.columns:
            data = data.sort_values("date").reset_index(drop=True)

        # 결측값 처리
        data = data.ffill().bfill()

        return data

    @abstractmethod
    def run_strategy(self, data: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """전략 실행 및 신호 생성"""
        pass

    def calculate_performance_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """성과 지표 계산"""
        if len(returns) == 0:
            return {}

        metrics = {
            "total_return": returns.sum(),
            "cumulative_return": (1 + returns).prod() - 1,
            "volatility": returns.std() * np.sqrt(252),  # 연환산
            "sharpe_ratio": (
                returns.mean() / returns.std() * np.sqrt(252)
                if returns.std() > 0
                else 0
            ),
            "max_drawdown": self._calculate_max_drawdown(returns),
            "win_rate": (returns > 0).mean(),
            "avg_win": (
                returns[returns > 0].mean() if len(returns[returns > 0]) > 0 else 0
            ),
            "avg_loss": (
                returns[returns < 0].mean() if len(returns[returns < 0]) > 0 else 0
            ),
            "total_trades": len(returns),
        }

        self.performance_metrics = metrics
        return metrics

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """최대 낙폭(MDD) 계산"""
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        return drawdown.min()

    def apply_risk_management(
        self, signal: TradeSignal, current_price: float, portfolio_value: float
    ) -> Tuple[float, float, float]:
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
        position_value = portfolio_value * self.risk_management["position_size_pct"]
        position_size = position_value / current_price

        # 손절/익절 가격 계산
        if signal.signal_type == "BUY":
            stop_loss_price = current_price * (
                1 - self.risk_management["stop_loss_pct"]
            )
            take_profit_price = current_price * (
                1 + self.risk_management["take_profit_pct"]
            )
        else:  # SELL
            stop_loss_price = current_price * (
                1 + self.risk_management["stop_loss_pct"]
            )
            take_profit_price = current_price * (
                1 - self.risk_management["take_profit_pct"]
            )

        return position_size, stop_loss_price, take_profit_price

    def get_strategy_info(self) -> Dict[str, Any]:
        """전략 정보 반환"""
        return {
            "name": self.name,
            "description": self.config.description,
            "parameters": self.parameters,
            "risk_management": self.risk_management,
            "required_indicators": self.config.required_indicators,
            "min_data_length": self.config.min_data_length,
            "total_signals": len(self.signals_history),
            "performance_metrics": self.performance_metrics,
        }


# 유틸리티 함수들
def create_default_config(
    strategy_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    risk_settings: Optional[Dict[str, float]] = None,
) -> StrategyConfig:
    """기본 전략 설정 생성"""
    return StrategyConfig(
        name=strategy_name,
        description=f"{strategy_name} 스윙 트레이딩 전략",
        parameters=parameters or {},
        risk_management=risk_settings or {},
        min_data_length=50,
    )


def calculate_signal_confidence(
    indicators: Dict[str, float], thresholds: Dict[str, Tuple[float, float]]
) -> float:
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

    return float(np.mean(confidence_scores)) if confidence_scores else 0.5


if __name__ == "__main__":
    # 테스트 코드
    print("Base Strategy 모듈 테스트")
    config = create_default_config(
        "테스트전략", {"param1": 10}, {"stop_loss_pct": 0.02}
    )
    print(f"기본 설정: {config}")
