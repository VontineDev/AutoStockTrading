"""
MACD 스윙 트레이딩 전략

TA-Lib의 MACD 지표를 활용한 스윙 트레이딩 전략입니다.
MACD 라인과 시그널 라인의 교차, 히스토그램 변화를 종합적으로 분석합니다.
"""

import pandas as pd
import numpy as np
import talib
from datetime import datetime
from typing import List, Dict, Any
import logging
from dataclasses import dataclass

from .base_strategy import (
    BaseStrategy,
    TradeSignal,
    StrategyConfig,
    create_default_config,
    calculate_signal_confidence,
)

logger = logging.getLogger(__name__)

@dataclass
class MACDConfig(StrategyConfig):
    name: str = "MACD_SwingTrading"
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    histogram_threshold: float = 0.0
    min_data_length: int = 20
    stop_loss_pct: float = 0.04
    take_profit_pct: float = 0.08
    rsi_filter: bool = False
    rsi_period: int = 14
    rsi_oversold: float = 35
    rsi_overbought: float = 65
    def __post_init__(self):
        if getattr(self, 'risk_management', None) is None:
            self.risk_management = {}
        if getattr(self, 'parameters', None) is None:
            self.parameters = {}

class MACDStrategy(BaseStrategy):
    """MACD 기반 스윙 트레이딩 전략"""

    ConfigClass = MACDConfig

    def __init__(self, config: StrategyConfig = None):
        """MACD 전략 초기화"""
        if config is None:
            config = self._create_default_macd_config()

        super().__init__(config)

        # MACD 특화 설정
        self.fast_period = self.parameters.get("fast_period", 12)
        self.slow_period = self.parameters.get("slow_period", 26)
        self.signal_period = self.parameters.get("signal_period", 9)
        self.histogram_threshold = self.parameters.get("histogram_threshold", 0.0)
        self.trend_filter = self.parameters.get("use_trend_filter", True)
        self.volume_filter = self.parameters.get("use_volume_filter", False)

        # 신호 신뢰도 임계값
        self.confidence_thresholds = {
            "MACD": (-2.0, 2.0),
            "MACD_signal": (-1.5, 1.5),
            "MACD_hist": (-1.0, 1.0),
            "RSI": (20, 80),
            "volume_ratio": (0.8, 2.0),
        }

        logger.info(
            f"MACD 전략 초기화: fast={self.fast_period}, slow={self.slow_period}, signal={self.signal_period}"
        )

    def _create_default_macd_config(self) -> StrategyConfig:
        """기본 MACD 전략 설정 생성"""
        return create_default_config(
            strategy_name="MACD_SwingTrading",
            parameters={
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "histogram_threshold": 0.0,
                "use_trend_filter": True,
                "use_volume_filter": False,
                "rsi_period": 14,
                "volume_ma_period": 20,
            },
            risk_settings={
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.06,
                "position_size_pct": 0.2,
            },
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        MACD 전략에 필요한 지표 계산 (base_strategy의 통합 지표 계산 활용)
        """
        # 통합 지표 계산 활용 - 모든 표준 지표를 한번에 계산
        df = self.calculate_all_indicators(data)

        # MACD 특화 추가 지표 (이미 MACD는 통합 지표에서 계산됨)
        if 'MACD' in df.columns and 'MACD_signal' in df.columns:
            # MACD 히스토그램 변화량
            df["MACD_hist_change"] = df["MACD_hist"] - df["MACD_hist"].shift(1)
            
            # MACD 제로라인 크로스
            df["MACD_bullish_zero"] = (df["MACD"] > 0) & (df["MACD"].shift(1) <= 0)
            df["MACD_bearish_zero"] = (df["MACD"] < 0) & (df["MACD"].shift(1) >= 0)
            
            # MACD 신호 강도
            df["MACD_strength"] = abs(df["MACD"] - df["MACD_signal"])

        # 기존 코드에서 중복 제거 - 통합 지표를 활용
        # RSI, SMA, EMA, volume 지표들은 이미 계산됨
        
        return df

    def generate_signals(self, data: pd.DataFrame, symbol: str = "UNKNOWN") -> list:
        """MACD 신호 생성: 데이터 컬럼 체크 및 예외 발생 시 빈 리스트 반환, 상세 로깅"""
        logger.debug(f"[MACDStrategy] 입력 데이터 shape: {data.shape}, 컬럼: {list(data.columns)}")
        required_cols = ['close']
        for col in required_cols:
            if col not in data.columns:
                logger.error(f"[MACDStrategy] 필수 컬럼 누락: {col}")
                return []
        try:
            import talib
            df = data.copy()
            # talib.MACD 계산 및 컬럼명 통일
            macd, macd_signal, macd_hist = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
            df['MACD'] = macd
            df['MACD_signal'] = macd_signal
            df['MACD_hist'] = macd_hist
            # 신호 생성에 필요한 컬럼 추가
            df['macd_cross_above'] = (df['MACD'] > df['MACD_signal']) & (df['MACD'].shift(1) <= df['MACD_signal'].shift(1))
            df['macd_cross_below'] = (df['MACD'] < df['MACD_signal']) & (df['MACD'].shift(1) >= df['MACD_signal'].shift(1))
            df['hist_change'] = df['MACD_hist'] - df['MACD_hist'].shift(1)
            df['MACD_change'] = df['MACD'] - df['MACD'].shift(1)
            logger.debug(f"[MACDStrategy] MACD 컬럼 생성 여부: {'MACD' in df.columns}, 첫 5개: {df['MACD'].head().tolist()}")
            signals = []

            for i in range(len(df)):
                if i < 2:  # 최소 데이터 필요
                    continue

                current_row = df.iloc[i]
                prev_row = df.iloc[i - 1]

                # 필수 값 확인
                if pd.isna(current_row["MACD"]) or pd.isna(current_row["MACD_signal"]):
                    continue

                signal = None
                reason = ""
                confidence = 0.5

                # 매수 신호 조건들
                buy_conditions = []

                # 1. MACD 골든크로스
                if "macd_cross_above" in current_row and current_row["macd_cross_above"]:
                    buy_conditions.append("MACD 골든크로스")

                # 2. MACD 히스토그램 상승 전환
                if (
                    "MACD_hist" in current_row and "hist_change" in current_row and
                    current_row["MACD_hist"] > self.histogram_threshold
                    and prev_row["MACD_hist"] <= self.histogram_threshold
                    and current_row["hist_change"] > 0
                ):
                    buy_conditions.append("히스토그램 상승 전환")

                # 3. MACD 라인이 0선 위에서 상승
                if (
                    "MACD" in current_row and "MACD_change" in current_row and "MACD_signal" in current_row and
                    current_row["MACD"] > 0
                    and current_row["MACD_change"] > 0
                    and current_row["MACD"] > current_row["MACD_signal"]
                ):
                    buy_conditions.append("0선 위 MACD 상승")

                # 매도 신호 조건들
                sell_conditions = []

                # 1. MACD 데드크로스
                if "macd_cross_below" in current_row and current_row["macd_cross_below"]:
                    sell_conditions.append("MACD 데드크로스")

                # 2. MACD 히스토그램 하락 전환
                if (
                    "MACD_hist" in current_row and "hist_change" in current_row and
                    current_row["MACD_hist"] < -self.histogram_threshold
                    and prev_row["MACD_hist"] >= -self.histogram_threshold
                    and current_row["hist_change"] < 0
                ):
                    sell_conditions.append("히스토그램 하락 전환")

                # 3. MACD 라인이 0선 아래에서 하락
                if (
                    "MACD" in current_row and "MACD_change" in current_row and "MACD_signal" in current_row and
                    current_row["MACD"] < 0
                    and current_row["MACD_change"] < 0
                    and current_row["MACD"] < current_row["MACD_signal"]
                ):
                    sell_conditions.append("0선 아래 MACD 하락")

                # 신호 결정
                if buy_conditions:
                    signal_type = "BUY"
                    reason = " + ".join(buy_conditions)

                    # 추가 필터 적용
                    if self._apply_buy_filters(current_row):
                        confidence = self._calculate_buy_confidence(current_row)
                    else:
                        continue  # 필터 통과 실패

                elif sell_conditions:
                    signal_type = "SELL"
                    reason = " + ".join(sell_conditions)

                    # 추가 필터 적용
                    if self._apply_sell_filters(current_row):
                        confidence = self._calculate_sell_confidence(current_row)
                    else:
                        continue  # 필터 통과 실패

                else:
                    continue  # 신호 없음

                # TradeSignal 생성
                signal = TradeSignal(
                    timestamp=current_row.name,  # 인덱스에서 날짜 가져오기
                    symbol=symbol,
                    signal_type=signal_type,
                    price=current_row["close"],
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        "MACD": current_row.get("MACD", np.nan),
                        "MACD_signal": current_row.get("MACD_signal", np.nan),
                        "MACD_hist": current_row.get("MACD_hist", np.nan),
                        "RSI": current_row.get("RSI", np.nan),
                        "volume_ratio": current_row.get("volume_ratio", 1.0),
                    },
                    risk_level=self._assess_risk_level(current_row, confidence),
                )

                signals.append(signal)

            logger.debug(f"[MACDStrategy] 생성된 신호 수: {len(signals)}")
            return signals
        except Exception as e:
            logger.error(f"[MACDStrategy] 신호 생성 중 예외 발생: {e}")
            return []

    def _apply_buy_filters(self, row: pd.Series) -> bool:
        """매수 신호 추가 필터 (완화된 버전)"""
        filters_passed = []

        # 추세 필터 (완화됨)
        if self.trend_filter:
            if "SMA_50" in row and not pd.isna(row["SMA_50"]):
                # 50일선 근처도 허용 (5% 범위)
                trend_ok = row["close"] > row["SMA_50"] * 0.95
                filters_passed.append(trend_ok)

        # RSI 과매수 방지 (완화됨)
        if "RSI" in row and not pd.isna(row["RSI"]):
            rsi_ok = row["RSI"] < 85  # 85로 완화 (기존 70)
            filters_passed.append(rsi_ok)

        # 거래량 필터 (완화됨)
        if self.volume_filter and "volume_ratio" in row:
            volume_ok = row["volume_ratio"] > 0.7  # 0.7배로 완화 (기존 1.0)
            filters_passed.append(volume_ok)

        return all(filters_passed) if filters_passed else True

    def _apply_sell_filters(self, row: pd.Series) -> bool:
        """매도 신호 추가 필터 (완화된 버전)"""
        filters_passed = []

        # 추세 필터 (완화됨)
        if self.trend_filter:
            if "SMA_50" in row and not pd.isna(row["SMA_50"]):
                # 50일선 근처도 허용 (5% 범위)
                trend_ok = row["close"] < row["SMA_50"] * 1.05
                filters_passed.append(trend_ok)

        # RSI 과매도 방지 (완화됨)
        if "RSI" in row and not pd.isna(row["RSI"]):
            rsi_ok = row["RSI"] > 15  # 15로 완화 (기존 30)
            filters_passed.append(rsi_ok)

        # 거래량 필터 (완화됨)
        if self.volume_filter and "volume_ratio" in row:
            volume_ok = row["volume_ratio"] > 0.7  # 0.7배로 완화 (기존 1.0)
            filters_passed.append(volume_ok)

        return all(filters_passed) if filters_passed else True

    def _calculate_buy_confidence(self, row: pd.Series) -> float:
        """매수 신호 신뢰도 계산"""
        indicators = {
            "MACD": row["MACD"],
            "MACD_signal": row["MACD_signal"],
            "MACD_hist": row["MACD_hist"],
            "RSI": row["RSI"],
            "volume_ratio": row.get("volume_ratio", 1.0),
        }

        base_confidence = calculate_signal_confidence(
            indicators, self.confidence_thresholds
        )

        # MACD 특화 조정
        if row["MACD"] > 0 and row["MACD_hist"] > 0:
            base_confidence += 0.1  # 강세 구간에서 신뢰도 증가

        if row.get("volume_ratio", 1.0) > 1.5:
            base_confidence += 0.1  # 고거래량 시 신뢰도 증가

        return min(1.0, base_confidence)

    def _calculate_sell_confidence(self, row: pd.Series) -> float:
        """매도 신호 신뢰도 계산"""
        indicators = {
            "MACD": row["MACD"],
            "MACD_signal": row["MACD_signal"],
            "MACD_hist": row["MACD_hist"],
            "RSI": row["RSI"],
            "volume_ratio": row.get("volume_ratio", 1.0),
        }

        base_confidence = calculate_signal_confidence(
            indicators, self.confidence_thresholds
        )

        # MACD 특화 조정
        if row["MACD"] < 0 and row["MACD_hist"] < 0:
            base_confidence += 0.1  # 약세 구간에서 신뢰도 증가

        if row.get("volume_ratio", 1.0) > 1.5:
            base_confidence += 0.1  # 고거래량 시 신뢰도 증가

        return min(1.0, base_confidence)

    def _assess_risk_level(self, row: pd.Series, confidence: float) -> str:
        """리스크 레벨 평가"""
        risk_factors = []

        # 변동성 체크 (ATR 기반)
        if "ATR" in row and not pd.isna(row["ATR"]):
            atr_ratio = row["ATR"] / row["close"]
            if atr_ratio > 0.05:  # 5% 이상 변동성
                risk_factors.append("high_volatility")

        # RSI 극단치
        if "RSI" in row:
            if row["RSI"] > 80 or row["RSI"] < 20:
                risk_factors.append("extreme_rsi")

        # 신뢰도 기반
        if confidence < 0.4:
            risk_factors.append("low_confidence")

        # 리스크 레벨 결정
        if len(risk_factors) >= 2:
            return "HIGH"
        elif len(risk_factors) == 1:
            return "MEDIUM"
        else:
            return "LOW"

    def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """신호 유효성 검증 (완화된 버전)"""
        # 기본 검증 (완화됨)
        if signal.confidence < 0.2:  # 0.3에서 0.2로 완화
            return False

        # 고위험 신호 필터링 (완화됨)
        if signal.risk_level == "HIGH" and signal.confidence < 0.5:  # 0.7에서 0.5로 완화
            return False

        # 연속 동일 신호 방지 (완화됨: 7개 중 4개로 완화)
        if hasattr(self, "signals_history"):
            recent_signals = self.signals_history[-7:]  # 5에서 7로 확장
            same_type_count = sum(
                1 for s in recent_signals if s.signal_type == signal.signal_type
            )
            if same_type_count >= 4:  # 3에서 4로 완화
                return False

        return True

    def get_optimization_ranges(self) -> Dict[str, List]:
        """매개변수 최적화 범위 반환"""
        return {
            "fast_period": [8, 10, 12, 14],
            "slow_period": [21, 24, 26, 28, 30],
            "signal_period": [7, 8, 9, 10, 11],
            "histogram_threshold": [0.0, 0.1, 0.2],
        }

    def create_macd_strategy(
        fast: int = 12, slow: int = 26, signal: int = 9, use_filters: bool = True
    ) -> "MACDStrategy":
        """MACD 전략 팩토리 함수"""
        config = create_default_config(
            strategy_name=f"MACD_{fast}_{slow}_{signal}",
            parameters={
                "fast_period": fast,
                "slow_period": slow,
                "signal_period": signal,
                "histogram_threshold": 0.0,
                "use_trend_filter": use_filters,
                "use_volume_filter": use_filters,
                "rsi_period": 14,
                "volume_ma_period": 20,
            },
        )

        return MACDStrategy(config)

    def run_strategy(self, data: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """MACD 전략 실행 및 신호 생성 (generate_signals 래핑)"""
        try:
            return self.generate_signals(data, symbol)
        except Exception as e:
            logger.error(f"run_strategy 예외: {e}")
            return []


if __name__ == "__main__":
    # 테스트 코드
    strategy = create_macd_strategy()
    print(f"MACD 전략 생성: {strategy.get_strategy_info()}")
    print(f"최적화 범위: {strategy.get_optimization_ranges()}")
