#!/usr/bin/env python3
"""
RSI (Relative Strength Index) Strategy
RSI 기반 스윙 트레이딩 전략
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
class RSIConfig(StrategyConfig):
    """RSI 전략 설정"""

    name: str = "RSI_SwingTrading"
    rsi_period: int = 14
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    min_data_length: int = 20
    stop_loss_pct: float = 0.04
    take_profit_pct: float = 0.08
    volume_filter: bool = False
    volume_threshold: float = 1.3
    
    def __post_init__(self):
        super().__post_init__()
        # RSI 특화 매개변수를 parameters에 저장
        if self.parameters is None:
            self.parameters = {}
        self.parameters.update({
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'volume_filter': self.volume_filter,
            'volume_threshold': self.volume_threshold
        })


class RSIStrategy(BaseStrategy):
    """RSI 기반 스윙 트레이딩 전략"""

    ConfigClass = RSIConfig

    def __init__(self, config: Optional[RSIConfig] = None):
        super().__init__(config or RSIConfig())
        self.config: RSIConfig = self.config
        logger.info(
            f"RSI 전략 초기화: period={self.config.rsi_period}, "
            f"oversold={self.config.rsi_oversold}, overbought={self.config.rsi_overbought}"
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        RSI 전략에 필요한 지표 계산 (base_strategy의 통합 지표 계산 활용)
        """
        # 통합 지표 계산 활용
        df = self.calculate_all_indicators(data)
        
        # RSI 관련 추가 지표 계산
        if 'RSI' in df.columns:
            # RSI 이동평균 (신호 평활화)
            df["RSI_SMA"] = df["RSI"].rolling(window=5).mean()
            
            # RSI 상승/하락 추세
            df["RSI_rising"] = df["RSI"] > df["RSI"].shift(1)
            df["RSI_falling"] = df["RSI"] < df["RSI"].shift(1)
        
        # 거래량 비율 계산 (volume_sma는 통합 지표에서 계산됨)
        if 'volume_sma' in df.columns:
            df["volume_ratio"] = df["volume"] / df["volume_sma"]
        elif 'SMA_20' in df.columns:  # fallback
            df["volume_sma"] = df["volume"].rolling(window=20).mean()
            df["volume_ratio"] = df["volume"] / df["volume_sma"]

        return df

    def _assess_risk_level(self, current_row: pd.Series, confidence: float) -> str:
        """리스크 레벨 평가"""
        rsi = current_row.get("RSI", 50)
        volume_ratio = current_row.get("volume_ratio", 1.0)
        
        # None 값 체크
        if rsi is None:
            rsi = 50
        if volume_ratio is None:
            volume_ratio = 1.0

        # 극단 RSI 구간은 고위험
        if rsi > 80 or rsi < 20:
            return "HIGH"
        # 적정 거래량과 적당한 RSI는 저위험
        elif 1.0 <= volume_ratio <= 2.0 and 35 <= rsi <= 65:
            return "LOW"
        else:
            return "MEDIUM"

    def _generate_buy_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매수 신호 생성"""
        signals = []

        for i in range(len(df)):
            current_row = df.iloc[i]

            # 데이터 부족 시 건너뛰기 (최소 요구사항 완화)
            if pd.isna(current_row.get("RSI")) or pd.isna(current_row.get("SMA_20")):
                continue

            rsi = current_row["RSI"]
            price = current_row["close"]
            sma_20 = current_row["SMA_20"]
            sma_50 = current_row.get("SMA_50", sma_20)
            volume_ratio = current_row.get("volume_ratio", 1.0)

            # 매수 조건들 (다양한 기회 제공)
            buy_conditions = []
            confidence = 0.0
            reasons = []

            # 조건 1: RSI 과매도 구간에서 반등
            if rsi <= self.config.rsi_oversold and current_row.get("RSI_rising", False):
                buy_conditions.append(True)
                confidence += 40
                reasons.append(f"RSI 과매도 반등 (RSI: {rsi:.1f})")

            # 조건 2: RSI 중간 구간에서 상승 추세
            elif 30 <= rsi <= 50 and current_row.get("RSI_rising", False):
                buy_conditions.append(True)
                confidence += 30
                reasons.append(f"RSI 중간 구간 상승 (RSI: {rsi:.1f})")

            # 조건 3: RSI가 50을 상향 돌파
            elif rsi > 50 and current_row.get("RSI", 0) > 50:
                buy_conditions.append(True)
                confidence += 25
                reasons.append(f"RSI 50 상향 돌파 (RSI: {rsi:.1f})")

            # 조건 4: 가격이 이동평균선 위에서 RSI 상승
            elif price > sma_20 and current_row.get("RSI_rising", False):
                buy_conditions.append(True)
                confidence += 20
                reasons.append("주가 > SMA20 + RSI 상승")

            if not any(buy_conditions):
                continue

            # 추가 확인 조건들

            # 가격 위치 필터 (선택적)
            if self.config.volume_filter:
                if price > sma_20:
                    confidence += 15
                    reasons.append("주가 > SMA20")
                elif price > sma_50:
                    confidence += 10
                    reasons.append("주가 > SMA50")

            # 거래량 확인
            if volume_ratio >= self.config.volume_threshold:
                confidence += 20
                reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")

            # RSI 추가 조건
            if rsi < 25:  # 매우 과매도
                confidence += 15
                reasons.append("매우 과매도 구간")
            elif rsi < 35:  # 과매도
                confidence += 10
                reasons.append("과매도 구간")

            # 신뢰도 임계점 확인 (완화)
            if confidence >= 50:  # 60에서 50으로 완화
                reason = "; ".join(reasons)

                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol="",  # run_strategy에서 설정됨
                    signal_type="BUY",
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        "RSI": rsi,
                        "RSI_SMA": current_row.get("RSI_SMA", rsi),
                        "SMA_20": sma_20,
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
            if pd.isna(current_row.get("RSI")):
                continue

            rsi = current_row["RSI"]
            price = current_row["close"]
            volume_ratio = current_row.get("volume_ratio", 1.0)

            # 기본 매도 조건: RSI 과매수 구간에서 하락
            overbought_decline = rsi >= self.config.rsi_overbought and current_row.get(
                "RSI_falling", False
            )

            if not overbought_decline:
                continue

            # 신뢰도 계산
            confidence = 50.0
            reasons = [f"RSI 과매수 하락 (RSI: {rsi:.1f})"]

            # RSI 극값 조건
            if rsi > 75:  # 매우 과매수
                confidence += 15
                reasons.append("매우 과매수 구간")

            # 거래량 확인
            if volume_ratio >= self.config.volume_threshold:
                confidence += 15
                reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")

            # 신뢰도 임계점 확인
            if confidence >= 60:
                reason = "; ".join(reasons)

                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol="",
                    signal_type="SELL",
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        "RSI": rsi,
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
            f"{symbol} RSI 신호 생성: 매수 {len(buy_signals)}개, 매도 {len(sell_signals)}개"
        )

        return all_signals

    def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """매매 신호 검증"""
        # 기본 검증
        if signal.confidence < 50:
            return False

        # RSI 값 검증
        rsi = signal.indicators.get("RSI", 50)
        if signal.signal_type == "BUY" and rsi > self.config.rsi_oversold + 10:
            return False
        if signal.signal_type == "SELL" and rsi < self.config.rsi_overbought - 10:
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
            f"{symbol} RSI 전략 완료: {len(validated_signals)}개 유효 신호 생성"
        )

        return validated_signals


def quick_rsi_signal(data: pd.DataFrame, period: int = 14, oversold: float = 30, overbought: float = 70) -> pd.Series:
    """간단한 RSI 신호 생성 (유틸리티 함수)"""
    try:
        rsi = talib.RSI(data['close'], timeperiod=period)
    except:
        # TA-Lib을 사용할 수 없는 경우 기본 RSI 계산
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
    
    buy_signal = rsi < oversold
    sell_signal = rsi > overbought
    
    signals = pd.Series('HOLD', index=data.index)
    signals[buy_signal] = 'BUY'
    signals[sell_signal] = 'SELL'
    
    return signals


if __name__ == "__main__":
    # 테스트 코드
    print("RSI Strategy 테스트")
    
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
    
    # RSI 전략 테스트
    config = RSIConfig()
    strategy = RSIStrategy(config)
    
    signals = strategy.run_strategy(sample_data, "TEST")
    print(f"생성된 신호 수: {len(signals)}")
