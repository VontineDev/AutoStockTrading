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
    oversold: float = 30.0
    overbought: float = 70.0
    rsi_sma_period: int = 5  # RSI 스무딩용
    min_data_length: int = 50
    
    # 리스크 관리
    stop_loss_pct: float = 0.03  # 3% 손절
    take_profit_pct: float = 0.06  # 6% 익절
    
    # 추가 필터
    volume_threshold: float = 1.2  # 평균 거래량 대비
    price_filter: bool = True  # 가격 위치 필터

class RSIStrategy(BaseStrategy):
    """RSI 기반 스윙 트레이딩 전략"""
    
def __init__(self, config: Optional[RSIConfig] = None):
        super().__init__(config or RSIConfig())
        self.config: RSIConfig = self.config
        logger.info(f"RSI 전략 초기화: period={self.config.rsi_period}, "
                   f"oversold={self.config.oversold}, overbought={self.config.overbought}")
    
def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        # 기본 RSI 계산
        df['RSI'] = talib.RSI(df['close'], timeperiod=self.config.rsi_period)
        
        # RSI 스무딩 (5일 이동평균)
        df['RSI_SMA'] = talib.SMA(df['RSI'], timeperiod=self.config.rsi_sma_period)
        
        # RSI 추세 확인
        df['RSI_rising'] = df['RSI'] > df['RSI'].shift(1)
        df['RSI_falling'] = df['RSI'] < df['RSI'].shift(1)
        
        # 추가 보조 지표
        df['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
        df['SMA_50'] = talib.SMA(df['close'], timeperiod=50)
        
        # 거래량 지표
        df['volume_sma'] = talib.SMA(df['volume'], timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
def _assess_risk_level(self, current_row: pd.Series, confidence: float) -> str:
        """리스크 레벨 평가"""
        rsi = current_row.get('RSI', 50)
        volume_ratio = current_row.get('volume_ratio', 1.0)
        
        # 극단 RSI 구간은 고위험
        if rsi > 80 or rsi < 20:
            return 'HIGH'
        # 적정 거래량과 적당한 RSI는 저위험
        elif 1.0 <= volume_ratio <= 2.0 and 35 <= rsi <= 65:
            return 'LOW'
        else:
            return 'MEDIUM'
    
def _generate_buy_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매수 신호 생성"""
        signals = []
        
        for i in range(len(df)):
            current_row = df.iloc[i]
            
            # 데이터 부족 시 건너뛰기
            if pd.isna(current_row.get('RSI')) or pd.isna(current_row.get('SMA_20')):
                continue
            
            rsi = current_row['RSI']
            price = current_row['close']
            sma_20 = current_row['SMA_20']
            sma_50 = current_row['SMA_50']
            volume_ratio = current_row.get('volume_ratio', 1.0)
            
            # 기본 매수 조건: RSI 과매도 구간에서 반등
            oversold_bounce = (
                rsi <= self.config.oversold and  # 과매도 구간
                current_row.get('RSI_rising', False)  # RSI 상승 중
            )
            
            if not oversold_bounce:
                continue
            
            # 추가 확인 조건들
            confidence = 50.0
            reasons = [f"RSI 과매도 반등 (RSI: {rsi:.1f})"]
            
            # 가격 위치 필터 (선택적)
            if self.config.price_filter:
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
            
            # 신뢰도 임계점 확인
            if confidence >= 60:
                reason = "; ".join(reasons)
                
                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol="",  # run_strategy에서 설정됨
                    signal_type='BUY',
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        'RSI': rsi,
                        'RSI_SMA': current_row.get('RSI_SMA', rsi),
                        'SMA_20': sma_20,
                        'SMA_50': sma_50,
                        'volume_ratio': volume_ratio
                    },
                    risk_level=self._assess_risk_level(current_row, confidence)
                )
                signals.append(signal)
        
        return signals
    
def _generate_sell_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매도 신호 생성"""
        signals = []
        
        for i in range(len(df)):
            current_row = df.iloc[i]
            
            # 데이터 부족 시 건너뛰기
            if pd.isna(current_row.get('RSI')) or pd.isna(current_row.get('SMA_20')):
                continue
            
            rsi = current_row['RSI']
            price = current_row['close']
            sma_20 = current_row['SMA_20']
            sma_50 = current_row['SMA_50']
            volume_ratio = current_row.get('volume_ratio', 1.0)
            
            # 기본 매도 조건: RSI 과매수 구간에서 하락
            overbought_decline = (
                rsi >= self.config.overbought and  # 과매수 구간
                current_row.get('RSI_falling', False)  # RSI 하락 중
            )
            
            if not overbought_decline:
                continue
            
            # 추가 확인 조건들
            confidence = 50.0
            reasons = [f"RSI 과매수 하락 (RSI: {rsi:.1f})"]
            
            # 가격 위치 필터 (선택적)
            if self.config.price_filter:
                if price < sma_20:
                    confidence += 15
                    reasons.append("주가 < SMA20")
                elif price < sma_50:
                    confidence += 10
                    reasons.append("주가 < SMA50")
            
            # 거래량 확인
            if volume_ratio >= self.config.volume_threshold:
                confidence += 20
                reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")
            
            # RSI 추가 조건
            if rsi > 75:  # 매우 과매수
                confidence += 15
                reasons.append("매우 과매수 구간")
            
            # 신뢰도 임계점 확인
            if confidence >= 60:
                reason = "; ".join(reasons)
                
                signal = TradeSignal(
                    timestamp=current_row.name,
                    symbol="",  # run_strategy에서 설정됨
                    signal_type='SELL',
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        'RSI': rsi,
                        'RSI_SMA': current_row.get('RSI_SMA', rsi),
                        'SMA_20': sma_20,
                        'SMA_50': sma_50,
                        'volume_ratio': volume_ratio
                    },
                    risk_level=self._assess_risk_level(current_row, confidence)
                )
                signals.append(signal)
        
        return signals
    
def generate_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매매 신호 생성 (메인 로직)"""
        # 지표 계산
        df = self.calculate_indicators(df)
        
        # 매수/매도 신호 생성
        buy_signals = self._generate_buy_signals(df)
        sell_signals = self._generate_sell_signals(df)
        
        # 신호 합치고 시간순 정렬
        all_signals = buy_signals + sell_signals
        all_signals.sort(key=lambda x: x.timestamp)
        
        logger.info(f"RSI 전략으로 {len(all_signals)}개 신호 생성")
        return all_signals
    
def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """신호 검증"""
        # 기본 검증: 가격과 신뢰도 확인
        if signal.price <= 0 or signal.confidence < 50:
            return False
        
        # RSI 특화 검증
        rsi = signal.indicators.get('RSI', 50)
        
        # 매수 신호 검증
        if signal.signal_type == 'BUY':
            return rsi <= 40  # RSI가 너무 높지 않은 경우만
        
        # 매도 신호 검증
        elif signal.signal_type == 'SELL':
            return rsi >= 60  # RSI가 너무 낮지 않은 경우만
        
        return True 