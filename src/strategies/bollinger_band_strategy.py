#!/usr/bin/env python3
"""
Bollinger Bands Strategy
볼린저 밴드 기반 스윙 트레이딩 전략
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
class BollingerBandConfig(StrategyConfig):
    """볼린저 밴드 전략 설정"""

    name: str = "BollingerBand_SwingTrading"
    bb_period: int = 20
    bb_deviation: float = 2.0
    min_data_length: int = 50

    # 신호 조건
    bb_squeeze_threshold: float = 0.02  # 밴드 폭 압축 기준 (2%)
    volume_confirmation: bool = True
    rsi_filter: bool = True

    # 리스크 관리
    stop_loss_pct: float = 0.04  # 4% 손절
    take_profit_pct: float = 0.08  # 8% 익절

    # 추가 필터
    volume_threshold: float = 1.3  # 평균 거래량 대비
    rsi_period: int = 14
    rsi_oversold: float = 35
    rsi_overbought: float = 65

    def __post_init__(self):
        if getattr(self, 'risk_management', None) is None:
            self.risk_management = {}
        if getattr(self, 'parameters', None) is None:
            self.parameters = {}


class BollingerBandStrategy(BaseStrategy):
    """볼린저 밴드 기반 스윙 트레이딩 전략"""

    ConfigClass = BollingerBandConfig

    def __init__(self, config: Optional[BollingerBandConfig] = None):
        super().__init__(config or BollingerBandConfig())
        self.config: BollingerBandConfig = self.config
        logger.info(
            f"볼린저 밴드 전략 초기화: period={self.config.bb_period}, "
            f"deviation={self.config.bb_deviation}"
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        볼린저 밴드 전략에 필요한 지표 계산 (base_strategy의 통합 지표 계산 활용)
        """
        # 통합 지표 계산 활용 - 모든 표준 지표를 한번에 계산
        df = self.calculate_all_indicators(data)

        # 볼린저 밴드 특화 추가 지표 (이미 BB는 통합 지표에서 계산됨)
        if 'BB_upper' in df.columns and 'BB_lower' in df.columns and 'BB_middle' in df.columns:
            # 밴드 폭 계산
            df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / df["BB_middle"] * 100
            
            # 가격의 밴드 내 위치 (%B)
            df["BB_percent"] = (df["close"] - df["BB_lower"]) / (df["BB_upper"] - df["BB_lower"])
            
            # 밴드 수축/확장 감지
            df["BB_squeeze"] = df["BB_width"] < df["BB_width"].rolling(window=20).mean() * 0.8
            
            # 밴드 터치 감지
            df["BB_touch_upper"] = df["close"] >= df["BB_upper"] * 0.98
            df["BB_touch_lower"] = df["close"] <= df["BB_lower"] * 1.02

        # 기존 중복 코드 제거 - 통합 지표 활용
        # RSI, SMA, volume 등은 이미 계산됨
        
        return df

    def _assess_risk_level(self, current_row: pd.Series, confidence: float) -> str:
        """리스크 레벨 평가"""
        bb_position = current_row.get("BB_position", 0.5)
        bb_width = current_row.get("BB_width", 0.05)

        # 밴드 극단에서는 고위험
        if bb_position > 0.9 or bb_position < 0.1:
            return "HIGH"
        # 밴드 중앙 근처는 저위험
        elif 0.3 <= bb_position <= 0.7 and bb_width > 0.03:
            return "LOW"
        else:
            return "MEDIUM"

    def _generate_buy_signals(self, df: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """매수 신호 생성"""
        signals = []

        for i in range(len(df)):
            current_row = df.iloc[i]

            # 데이터 부족 시 건너뛰기 (완화된 검증)
            if pd.isna(current_row.get("BB_lower")) or pd.isna(current_row.get("close")):
                continue

            price = current_row["close"]
            bb_position = current_row.get("BB_position", 0.5)
            bb_width = current_row.get("BB_width", 0.05)
            touching_lower = current_row.get("BB_touch_lower", False)
            squeeze = current_row.get("BB_squeeze", False)

            # 매수 조건들 (다양한 기회 제공)
            buy_conditions = []
            confidence = 0.0
            reasons = []

            # 조건 1: 하단 밴드 터치 후 반등
            if touching_lower and bb_position > 0.1:
                buy_conditions.append(True)
                confidence += 40
                reasons.append("하단 밴드 터치 후 반등")

            # 조건 2: 스퀴즈 후 상승 돌파
            elif squeeze and current_row.get("band_expanding", False) and price > current_row.get("BB_middle", price):
                buy_conditions.append(True)
                confidence += 35
                reasons.append("스퀴즈 후 상승 돌파")

            # 조건 3: 중간선 상승 돌파 (추세 추종)
            elif (price > current_row.get("BB_middle", price) and 
                  current_row.get("close", 0) > current_row.get("SMA_20", 0) and 
                  bb_width > 0.03):
                buy_conditions.append(True)
                confidence += 30
                reasons.append("중간선 상승 돌파")

            # 조건 4: 밴드 중앙 근처에서 상승 추세
            elif 0.3 <= bb_position <= 0.7 and price > current_row.get("close", price):
                buy_conditions.append(True)
                confidence += 25
                reasons.append("밴드 중앙 상승 추세")

            # 조건 5: 밴드 하단 근처에서 반등
            elif bb_position < 0.3 and price > current_row.get("BB_lower", price):
                buy_conditions.append(True)
                confidence += 20
                reasons.append("밴드 하단 근처 반등")

            if not any(buy_conditions):
                continue

            # 추가 확인 조건들

            # RSI 필터 (과매수 구간 제외)
            if self.config.rsi_filter:
                rsi = current_row.get("RSI", 50)
                if rsi < self.config.rsi_overbought:
                    confidence += 15
                    reasons.append(f"RSI 적정 구간 ({rsi:.1f})")
                elif rsi > 75:  # 과매수 시 신뢰도 감소
                    confidence -= 10

            # 거래량 확인
            if self.config.volume_confirmation:
                volume_ratio = current_row.get("volume_ratio", 1.0)
                if volume_ratio >= self.config.volume_threshold:
                    confidence += 20
                    reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")

            # 밴드 확장 확인 (변동성 증가)
            if current_row.get("band_expanding", False):
                confidence += 10
                reasons.append("밴드 확장 (변동성 증가)")

            # 신뢰도 임계점 확인 (완화)
            if confidence >= 50:  # 60에서 50으로 완화
                reason = "; ".join(reasons)

                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol=symbol,  # 실제 심볼 할당
                    signal_type="BUY",
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        "BB_upper": current_row.get("BB_upper", price),
                        "BB_middle": current_row.get("BB_middle", price),
                        "BB_lower": current_row.get("BB_lower", price),
                        "BB_position": bb_position,
                        "BB_width": bb_width,
                        "RSI": current_row.get("RSI", 50),
                        "volume_ratio": current_row.get("volume_ratio", 1.0),
                    },
                    risk_level=self._assess_risk_level(current_row, confidence),
                )
                signals.append(signal)

        return signals

    def _generate_sell_signals(self, df: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """매도 신호 생성"""
        signals = []

        for i in range(len(df)):
            current_row = df.iloc[i]

            # 데이터 부족 시 건너뛰기
            if pd.isna(current_row.get("BB_upper")) or pd.isna(
                current_row.get("BB_position")
            ):
                continue

            price = current_row["close"]
            bb_position = current_row["BB_position"]
            bb_width = current_row["BB_width"]
            touching_upper = current_row.get("touching_upper", False)
            breaking_upper = current_row.get("breaking_upper", False)

            # 기본 매도 조건들
            sell_conditions = []
            confidence = 0.0
            reasons = []

            # 조건 1: 상단 밴드 터치/돌파 후 하락
            if (touching_upper or breaking_upper) and bb_position > 0.8:
                sell_conditions.append(True)
                confidence += 40
                reasons.append("상단 밴드 터치 후 하락")

            # 조건 2: 중간선 하락 이탈 (추세 전환)
            elif (
                price < current_row["BB_middle"]
                and current_row["close"] < current_row["SMA_20"]
                and bb_width > 0.03
            ):  # 충분한 변동성
                sell_conditions.append(True)
                confidence += 30
                reasons.append("중간선 하락 이탈")

            # 조건 3: 밴드 압축 시작 (변동성 감소)
            elif (
                current_row.get("band_contracting", False)
                and bb_position > 0.7
                and bb_width < 0.025
            ):
                sell_conditions.append(True)
                confidence += 25
                reasons.append("밴드 압축 시작")

            if not any(sell_conditions):
                continue

            # 추가 확인 조건들

            # RSI 필터 (과매도 구간 제외)
            if self.config.rsi_filter:
                rsi = current_row.get("RSI", 50)
                if rsi > self.config.rsi_oversold:
                    confidence += 15
                    reasons.append(f"RSI 적정 구간 ({rsi:.1f})")
                elif rsi < 25:  # 과매도 시 신뢰도 감소
                    confidence -= 10

            # 거래량 확인
            if self.config.volume_confirmation:
                volume_ratio = current_row.get("volume_ratio", 1.0)
                if volume_ratio >= self.config.volume_threshold:
                    confidence += 20
                    reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")

            # 밴드 위치 극단 확인
            if bb_position > 0.9:
                confidence += 15
                reasons.append("밴드 상단 극단")

            # 신뢰도 임계점 확인
            if confidence >= 60:
                reason = "; ".join(reasons)

                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol=symbol,  # 실제 심볼 할당
                    signal_type="SELL",
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        "BB_upper": current_row["BB_upper"],
                        "BB_middle": current_row["BB_middle"],
                        "BB_lower": current_row["BB_lower"],
                        "BB_position": bb_position,
                        "BB_width": bb_width,
                        "RSI": current_row.get("RSI", 50),
                        "volume_ratio": current_row.get("volume_ratio", 1.0),
                    },
                    risk_level=self._assess_risk_level(current_row, confidence),
                )
                signals.append(signal)

        return signals

    def generate_signals(self, data: pd.DataFrame, symbol: str = None) -> list:
        """Bollinger Band 신호 생성: 데이터 컬럼 체크 및 예외 발생 시 빈 리스트 반환, 상세 로깅"""
        logger.debug(f"[BollingerBandStrategy] 입력 데이터 shape: {data.shape}, 컬럼: {list(data.columns)}")
        required_cols = ['close']
        for col in required_cols:
            if col not in data.columns:
                logger.error(f"[BollingerBandStrategy] 필수 컬럼 누락: {col}")
                return []
        
        try:
            # symbol이 None이면 데이터에서 추출하거나 기본값 사용
            if symbol is None:
                symbol = data['symbol'].iloc[0] if 'symbol' in data.columns else 'Unknown'
            
            # 지표 계산
            df = self.calculate_indicators(data)

            # 매수/매도 신호 생성
            buy_signals = self._generate_buy_signals(df, symbol)
            sell_signals = self._generate_sell_signals(df, symbol)

            # 신호 합치고 시간순 정렬
            all_signals = buy_signals + sell_signals
            all_signals.sort(key=lambda x: x.timestamp)

            logger.info(f"{symbol} 볼린저밴드 전략 신호 생성: 매수 {len(buy_signals)}개, 매도 {len(sell_signals)}개")
            logger.debug(f"[BollingerBandStrategy] 생성된 신호 수: {len(all_signals)}")
            return all_signals
        except Exception as e:
            logger.error(f"[BollingerBandStrategy] 신호 생성 중 예외 발생: {e}")
            return []

    def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """신호 검증"""
        # 기본 검증: 가격과 신뢰도 확인
        if signal.price <= 0 or signal.confidence < 50:
            return False

        # 볼린저 밴드 특화 검증
        bb_position = signal.indicators.get("BB_position", 0.5)
        bb_width = signal.indicators.get("BB_width", 0.05)

        # 밴드 폭이 너무 좁으면 (횡보 구간) 신호 무효
        if bb_width < 0.01:
            return False

        # 매수 신호 검증
        if signal.signal_type == "BUY":
            return bb_position <= 0.8  # 상단 근처에서는 매수 금지

        # 매도 신호 검증
        elif signal.signal_type == "SELL":
            return bb_position >= 0.2  # 하단 근처에서는 매도 금지

        return True

    def create_bollinger_band_strategy(
        self, period: int = 20, deviation: float = 2.0, use_filters: bool = True
    ) -> "BollingerBandStrategy":
        # Implementation of create_bollinger_band_strategy method
        pass

    def run_strategy(self, df: pd.DataFrame, symbol: str) -> List[TradeSignal]:
        """볼린저밴드 전략 실행 및 신호 생성"""
        # 기존 run_strategy 코드에서 symbol 인자를 추가로 받도록 수정
        # symbol 인자가 필요 없으면 무시해도 됨
        # ... 기존 run_strategy 코드 ...
