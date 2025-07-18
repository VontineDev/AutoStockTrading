#!/usr/bin/env python3
"""
Moving Average Strategy
이동평균 기반 스윙 트레이딩 전략
"""

import pandas as pd
import numpy as np
import talib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .base_strategy import BaseStrategy, StrategyConfig, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class MovingAverageConfig(StrategyConfig):
    """이동평균 전략 설정"""

    name: str = "MovingAverage_SwingTrading"
    fast_period: int = 10
    slow_period: int = 20
    long_period: int = 50
    min_data_length: int = 60

    # 신호 조건
    use_triple_ma: bool = True  # 3중 이동평균 사용
    slope_threshold: float = 0.001  # 기울기 임계값
    volume_confirmation: bool = True
    atr_filter: bool = True  # ATR 필터 사용

    # 리스크 관리
    stop_loss_pct: float = 0.035  # 3.5% 손절
    take_profit_pct: float = 0.07  # 7% 익절

    # 추가 필터
    volume_threshold: float = 1.1  # 평균 거래량 대비
    atr_period: int = 14
    min_atr_ratio: float = 0.015  # 최소 ATR 비율

    def __post_init__(self):
        super().__post_init__()
        # MA 특화 매개변수를 parameters에 저장
        if self.parameters is None:
            self.parameters = {}
        self.parameters.update({
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'long_period': self.long_period,
            'use_triple_ma': self.use_triple_ma,
            'slope_threshold': self.slope_threshold,
            'volume_confirmation': self.volume_confirmation,
            'atr_filter': self.atr_filter,
            'volume_threshold': self.volume_threshold,
            'atr_period': self.atr_period,
            'min_atr_ratio': self.min_atr_ratio
        })


class MovingAverageStrategy(BaseStrategy):
    """이동평균 기반 스윙 트레이딩 전략"""

    ConfigClass = MovingAverageConfig

    def __init__(self, config: Optional[MovingAverageConfig] = None):
        super().__init__(config or MovingAverageConfig())
        self.config: MovingAverageConfig = self.config
        logger.info(
            f"이동평균 전략 초기화: fast={self.config.fast_period}, "
            f"slow={self.config.slow_period}, long={self.config.long_period}"
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        이동평균 전략에 필요한 지표 계산 (base_strategy의 통합 지표 계산 활용)
        """
        # 통합 지표 계산 활용 - 모든 표준 지표를 한번에 계산
        df = self.calculate_all_indicators(data)
        
        # 전략별 특화 이동평균 계산 (커스텀 기간)
        df["SMA_fast"] = df["close"].rolling(window=self.config.fast_period).mean()
        df["SMA_slow"] = df["close"].rolling(window=self.config.slow_period).mean()
        df["EMA_fast"] = df["close"].ewm(span=self.config.fast_period).mean()
        df["EMA_slow"] = df["close"].ewm(span=self.config.slow_period).mean()

        if self.config.use_triple_ma:
            df["SMA_long"] = df["close"].rolling(window=self.config.long_period).mean()
            df["EMA_long"] = df["close"].ewm(span=self.config.long_period).mean()

        # 골든크로스/데드크로스 시그널
        df["golden_cross"] = (df["SMA_fast"] > df["SMA_slow"]) & (
            df["SMA_fast"].shift(1) <= df["SMA_slow"].shift(1)
        )
        df["dead_cross"] = (df["SMA_fast"] < df["SMA_slow"]) & (
            df["SMA_fast"].shift(1) >= df["SMA_slow"].shift(1)
        )

        # EMA 크로스도 확인
        df["ema_golden_cross"] = (df["EMA_fast"] > df["EMA_slow"]) & (
            df["EMA_fast"].shift(1) <= df["EMA_slow"].shift(1)
        )
        df["ema_dead_cross"] = (df["EMA_fast"] < df["EMA_slow"]) & (
            df["EMA_fast"].shift(1) >= df["EMA_slow"].shift(1)
        )

        # 이동평균 기울기 계산
        df["sma_fast_slope"] = (df["SMA_fast"] - df["SMA_fast"].shift(5)) / df[
            "SMA_fast"
        ].shift(5)
        df["sma_slow_slope"] = (df["SMA_slow"] - df["SMA_slow"].shift(5)) / df[
            "SMA_slow"
        ].shift(5)

        # 이동평균선 배열 확인
        if self.config.use_triple_ma:
            df["bullish_alignment"] = (df["SMA_fast"] > df["SMA_slow"]) & (
                df["SMA_slow"] > df["SMA_long"]
            )
            df["bearish_alignment"] = (df["SMA_fast"] < df["SMA_slow"]) & (
                df["SMA_slow"] < df["SMA_long"]
            )
        else:
            df["bullish_alignment"] = df["SMA_fast"] > df["SMA_slow"]
            df["bearish_alignment"] = df["SMA_fast"] < df["SMA_slow"]

        # 가격과 이동평균 관계
        df["price_above_fast"] = df["close"] > df["SMA_fast"]
        df["price_above_slow"] = df["close"] > df["SMA_slow"]

        # 거래량 지표 (통합 지표에서 가져오거나 계산)
        if self.config.volume_confirmation and 'volume_sma' not in df.columns:
            df["volume_sma"] = df["volume"].rolling(window=20).mean()
        
        if 'volume_sma' in df.columns:
            df["volume_ratio"] = df["volume"] / df["volume_sma"]

        # 이동평균 간 거리 (모멘텀 확인)
        df["ma_distance"] = (df["SMA_fast"] - df["SMA_slow"]) / df["SMA_slow"]

        return df

    def _assess_risk_level(self, current_row: pd.Series, confidence: float) -> str:
        """리스크 레벨 평가"""
        ma_distance_val = current_row.get("ma_distance", 0)
        atr_ratio = current_row.get("atr_ratio", 0.02)
        
        # None 값 체크 및 타입 변환
        if ma_distance_val is None:
            ma_distance_val = 0
        if atr_ratio is None:
            atr_ratio = 0.02
            
        ma_distance = abs(float(ma_distance_val))

        # 이동평균 간 거리가 클수록 추세가 강함 (저위험)
        if ma_distance > 0.03 and atr_ratio < 0.03:
            return "LOW"
        # 이동평균이 거의 붙어있으면 고위험 (횡보)
        elif ma_distance < 0.005 or atr_ratio > 0.05:
            return "HIGH"
        else:
            return "MEDIUM"

    def _generate_buy_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매수 신호 생성"""
        signals = []

        for i in range(len(df)):
            current_row = df.iloc[i]

            # 데이터 부족 시 건너뛰기
            if pd.isna(current_row.get("SMA_fast")) or pd.isna(current_row.get("SMA_slow")):
                continue

            # 기본 매수 조건들
            golden_cross = current_row.get("golden_cross", False)
            ema_golden_cross = current_row.get("ema_golden_cross", False)
            bullish_alignment = current_row.get("bullish_alignment", False)
            price_above_fast = current_row.get("price_above_fast", False)

            # 주요 매수 신호 조건
            if not (golden_cross or ema_golden_cross or (bullish_alignment and price_above_fast)):
                continue

            # 신뢰도 계산
            confidence = 40.0
            reasons = []

            # 신호 타입별 가중치
            if golden_cross:
                confidence += 25
                reasons.append("SMA 골든크로스")
            if ema_golden_cross:
                confidence += 20
                reasons.append("EMA 골든크로스")
            if bullish_alignment:
                confidence += 15
                reasons.append("상승 정렬")
            if price_above_fast:
                confidence += 10
                reasons.append("주가 > 단기MA")

            # 추가 확인 조건들
            sma_fast_slope = current_row.get("sma_fast_slope", 0)
            volume_ratio = current_row.get("volume_ratio", 1.0)
            atr_ratio = current_row.get("atr_ratio", 0.02)

            # 기울기 확인
            if sma_fast_slope and sma_fast_slope > self.config.slope_threshold:
                confidence += 10
                reasons.append("상승 추세")

            # 거래량 확인
            if self.config.volume_confirmation and volume_ratio:
                if volume_ratio >= self.config.volume_threshold:
                    confidence += 15
                    reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")

            # ATR 필터
            if self.config.atr_filter and atr_ratio:
                if atr_ratio >= self.config.min_atr_ratio:
                    confidence += 10
                    reasons.append("충분한 변동성")

            # 신뢰도 임계점 확인
            if confidence >= 60:
                reason = "; ".join(reasons)
                price = current_row["close"]

                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol="",  # run_strategy에서 설정
                    signal_type="BUY",
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        "SMA_fast": current_row["SMA_fast"],
                        "SMA_slow": current_row["SMA_slow"],
                        "ma_distance": current_row.get("ma_distance", 0),
                        "volume_ratio": volume_ratio,
                    },
                    risk_level=self._assess_risk_level(current_row, confidence),
                )
                signals.append(signal)

        return signals

    def _generate_sell_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매도 신호 생성"""
        signals = []

        for i in range(len(df)):
            current_row = df.iloc[i]

            # 데이터 부족 시 건너뛰기
            if pd.isna(current_row.get("SMA_fast")) or pd.isna(current_row.get("SMA_slow")):
                continue

            # 기본 매도 조건들
            dead_cross = current_row.get("dead_cross", False)
            ema_dead_cross = current_row.get("ema_dead_cross", False)
            bearish_alignment = current_row.get("bearish_alignment", False)
            price_below_fast = not current_row.get("price_above_fast", True)

            # 주요 매도 신호 조건
            if not (dead_cross or ema_dead_cross or (bearish_alignment and price_below_fast)):
                continue

            # 신뢰도 계산
            confidence = 40.0
            reasons = []

            # 신호 타입별 가중치
            if dead_cross:
                confidence += 25
                reasons.append("SMA 데드크로스")
            if ema_dead_cross:
                confidence += 20
                reasons.append("EMA 데드크로스")
            if bearish_alignment:
                confidence += 15
                reasons.append("하락 정렬")
            if price_below_fast:
                confidence += 10
                reasons.append("주가 < 단기MA")

            # 추가 확인 조건들
            sma_fast_slope = current_row.get("sma_fast_slope", 0)
            volume_ratio = current_row.get("volume_ratio", 1.0)

            # 기울기 확인 (하락 추세)
            if sma_fast_slope and sma_fast_slope < -self.config.slope_threshold:
                confidence += 10
                reasons.append("하락 추세")

            # 거래량 확인
            if self.config.volume_confirmation and volume_ratio:
                if volume_ratio >= self.config.volume_threshold:
                    confidence += 15
                    reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")

            # 신뢰도 임계점 확인
            if confidence >= 60:
                reason = "; ".join(reasons)
                price = current_row["close"]

                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol="",
                    signal_type="SELL",
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        "SMA_fast": current_row["SMA_fast"],
                        "SMA_slow": current_row["SMA_slow"],
                        "ma_distance": current_row.get("ma_distance", 0),
                        "volume_ratio": volume_ratio,
                    },
                    risk_level=self._assess_risk_level(current_row, confidence),
                )
                signals.append(signal)

        return signals

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """매매 신호 생성"""
        df = self.calculate_indicators(data)

        buy_signals = self._generate_buy_signals(df)
        sell_signals = self._generate_sell_signals(df)

        all_signals = buy_signals + sell_signals
        
        # 심볼 설정
        for signal in all_signals:
            signal.symbol = symbol

        # 신호 정렬 (시간순)
        all_signals.sort(key=lambda x: x.timestamp)

        logger.info(
            f"{symbol} MA 신호 생성: 매수 {len(buy_signals)}개, 매도 {len(sell_signals)}개"
        )

        return all_signals

    def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """매매 신호 검증"""
        # 기본 검증
        if signal.confidence < 50:
            return False

        # 이동평균 관계 검증
        sma_fast = signal.indicators.get("SMA_fast", 0)
        sma_slow = signal.indicators.get("SMA_slow", 0)
        
        if signal.signal_type == "BUY" and sma_fast <= sma_slow:
            return False
        if signal.signal_type == "SELL" and sma_fast >= sma_slow:
            return False

        # 고위험 신호 필터링
        if signal.risk_level == "HIGH" and signal.confidence < 80:
            return False

        return True

    def run_strategy(self, data: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """전략 실행"""
        # 데이터 전처리
        prepared_data = self.prepare_data(data)

        # 신호 생성
        signals = self.generate_signals(prepared_data, symbol)

        # 신호 검증 및 필터링
        validated_signals = [
            signal for signal in signals if self.validate_signal(signal, prepared_data)
        ]

        # 신호 히스토리에 추가
        self.signals_history.extend(validated_signals)

        logger.info(
            f"{symbol} MA 전략 완료: {len(validated_signals)}개 유효 신호 생성"
        )

        return validated_signals


def quick_ma_signal(data: pd.DataFrame, fast_period: int = 10, slow_period: int = 20) -> pd.Series:
    """간단한 이동평균 신호 생성 (유틸리티 함수)"""
    df = data.copy()
    df['sma_fast'] = df['close'].rolling(window=fast_period).mean()
    df['sma_slow'] = df['close'].rolling(window=slow_period).mean()
    
    golden_cross = (df['sma_fast'] > df['sma_slow']) & (df['sma_fast'].shift(1) <= df['sma_slow'].shift(1))
    dead_cross = (df['sma_fast'] < df['sma_slow']) & (df['sma_fast'].shift(1) >= df['sma_slow'].shift(1))
    
    signals = pd.Series('HOLD', index=data.index)
    signals[golden_cross] = 'BUY'
    signals[dead_cross] = 'SELL'
    
    return signals


if __name__ == "__main__":
    # 테스트 코드
    print("Moving Average Strategy 테스트")
    
    # 샘플 데이터 생성
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    sample_data = pd.DataFrame({
        'date': dates,
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 105,
        'low': np.random.randn(100).cumsum() + 95,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # MA 전략 테스트
    config = MovingAverageConfig()
    strategy = MovingAverageStrategy(config)
    
    signals = strategy.run_strategy(sample_data, "TEST")
    print(f"생성된 신호 수: {len(signals)}")
