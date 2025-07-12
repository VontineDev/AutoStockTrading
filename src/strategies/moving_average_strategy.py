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

class MovingAverageStrategy(BaseStrategy):
    """이동평균 기반 스윙 트레이딩 전략"""
    
def __init__(self, config: Optional[MovingAverageConfig] = None):
        super().__init__(config or MovingAverageConfig())
        self.config: MovingAverageConfig = self.config
        logger.info(f"이동평균 전략 초기화: fast={self.config.fast_period}, "
                   f"slow={self.config.slow_period}, long={self.config.long_period}")
    
def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        # 이동평균선들
        df['SMA_fast'] = talib.SMA(df['close'], timeperiod=self.config.fast_period)
        df['SMA_slow'] = talib.SMA(df['close'], timeperiod=self.config.slow_period)
        df['EMA_fast'] = talib.EMA(df['close'], timeperiod=self.config.fast_period)
        df['EMA_slow'] = talib.EMA(df['close'], timeperiod=self.config.slow_period)
        
        if self.config.use_triple_ma:
            df['SMA_long'] = talib.SMA(df['close'], timeperiod=self.config.long_period)
            df['EMA_long'] = talib.EMA(df['close'], timeperiod=self.config.long_period)
        
        # 골든크로스/데드크로스 감지
        df['golden_cross'] = (df['SMA_fast'] > df['SMA_slow']) & (df['SMA_fast'].shift(1) <= df['SMA_slow'].shift(1))
        df['dead_cross'] = (df['SMA_fast'] < df['SMA_slow']) & (df['SMA_fast'].shift(1) >= df['SMA_slow'].shift(1))
        
        # EMA 크로스도 확인
        df['ema_golden_cross'] = (df['EMA_fast'] > df['EMA_slow']) & (df['EMA_fast'].shift(1) <= df['EMA_slow'].shift(1))
        df['ema_dead_cross'] = (df['EMA_fast'] < df['EMA_slow']) & (df['EMA_fast'].shift(1) >= df['EMA_slow'].shift(1))
        
        # 이동평균 기울기 계산
        df['sma_fast_slope'] = (df['SMA_fast'] - df['SMA_fast'].shift(5)) / df['SMA_fast'].shift(5)
        df['sma_slow_slope'] = (df['SMA_slow'] - df['SMA_slow'].shift(5)) / df['SMA_slow'].shift(5)
        
        # 이동평균선 배열 확인
        if self.config.use_triple_ma:
            df['bullish_alignment'] = (df['SMA_fast'] > df['SMA_slow']) & (df['SMA_slow'] > df['SMA_long'])
            df['bearish_alignment'] = (df['SMA_fast'] < df['SMA_slow']) & (df['SMA_slow'] < df['SMA_long'])
        else:
            df['bullish_alignment'] = df['SMA_fast'] > df['SMA_slow']
            df['bearish_alignment'] = df['SMA_fast'] < df['SMA_slow']
        
        # 가격과 이동평균 관계
        df['price_above_fast'] = df['close'] > df['SMA_fast']
        df['price_above_slow'] = df['close'] > df['SMA_slow']
        
        # ATR 필터 (선택적)
        if self.config.atr_filter:
            df['ATR'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=self.config.atr_period)
            df['atr_ratio'] = df['ATR'] / df['close']
        
        # 거래량 지표
        if self.config.volume_confirmation:
            df['volume_sma'] = talib.SMA(df['volume'], timeperiod=20)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # 이동평균 간 거리 (모멘텀 확인)
        df['ma_distance'] = (df['SMA_fast'] - df['SMA_slow']) / df['SMA_slow']
        
        return df
    
def _assess_risk_level(self, current_row: pd.Series, confidence: float) -> str:
        """리스크 레벨 평가"""
        ma_distance = abs(current_row.get('ma_distance', 0))
        atr_ratio = current_row.get('atr_ratio', 0.02)
        
        # 이동평균 간 거리가 클수록 추세가 강함 (저위험)
        if ma_distance > 0.03 and atr_ratio < 0.03:
            return 'LOW'
        # 이동평균이 거의 붙어있으면 고위험 (횡보)
        elif ma_distance < 0.005 or atr_ratio > 0.05:
            return 'HIGH'
        else:
            return 'MEDIUM'
    
def _generate_buy_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매수 신호 생성"""
        signals = []
        
        for i in range(len(df)):
            current_row = df.iloc[i]
            
            # 데이터 부족 시 건너뛰기
            if pd.isna(current_row.get('SMA_fast')) or pd.isna(current_row.get('SMA_slow')):
                continue
            
            price = current_row['close']
            sma_fast = current_row['SMA_fast']
            sma_slow = current_row['SMA_slow']
            
            # 기본 매수 조건들
            buy_conditions = []
            confidence = 0.0
            reasons = []
            
            # 조건 1: 골든크로스
            if current_row.get('golden_cross', False):
                buy_conditions.append(True)
                confidence += 40
                reasons.append("SMA 골든크로스")
            
            # 조건 2: EMA 골든크로스 (추가 확인)
            elif current_row.get('ema_golden_cross', False):
                buy_conditions.append(True)
                confidence += 35
                reasons.append("EMA 골든크로스")
            
            # 조건 3: 강세 배열에서 가격이 빠른 이동평균 위로 복귀
            elif (current_row.get('bullish_alignment', False) and 
                  current_row.get('price_above_fast', False) and
                  not df.iloc[i-1]['price_above_fast'] if i > 0 else False):
                buy_conditions.append(True)
                confidence += 30
                reasons.append("강세 배열에서 가격 복귀")
            
            if not any(buy_conditions):
                continue
            
            # 추가 확인 조건들
            
            # 이동평균 기울기 확인
            fast_slope = current_row.get('sma_fast_slope', 0)
            slow_slope = current_row.get('sma_slow_slope', 0)
            
            if fast_slope > self.config.slope_threshold:
                confidence += 15
                reasons.append("빠른 MA 상승")
            
            if slow_slope > self.config.slope_threshold:
                confidence += 10
                reasons.append("느린 MA 상승")
            
            # 3중 이동평균 배열 확인
            if self.config.use_triple_ma and current_row.get('bullish_alignment', False):
                confidence += 15
                reasons.append("강세 3중 배열")
            
            # 거래량 확인
            if self.config.volume_confirmation:
                volume_ratio = current_row.get('volume_ratio', 1.0)
                if volume_ratio >= self.config.volume_threshold:
                    confidence += 20
                    reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")
            
            # ATR 필터 (충분한 변동성)
            if self.config.atr_filter:
                atr_ratio = current_row.get('atr_ratio', 0.02)
                if atr_ratio >= self.config.min_atr_ratio:
                    confidence += 10
                    reasons.append("적정 변동성")
            
            # 가격 위치 확인
            if price > sma_fast and price > sma_slow:
                confidence += 10
                reasons.append("가격 > 이동평균")
            
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
                        'SMA_fast': sma_fast,
                        'SMA_slow': sma_slow,
                        'SMA_long': current_row.get('SMA_long', 0),
                        'ma_distance': current_row.get('ma_distance', 0),
                        'fast_slope': fast_slope,
                        'slow_slope': slow_slope,
                        'volume_ratio': current_row.get('volume_ratio', 1.0),
                        'ATR': current_row.get('ATR', 0)
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
            if pd.isna(current_row.get('SMA_fast')) or pd.isna(current_row.get('SMA_slow')):
                continue
            
            price = current_row['close']
            sma_fast = current_row['SMA_fast']
            sma_slow = current_row['SMA_slow']
            
            # 기본 매도 조건들
            sell_conditions = []
            confidence = 0.0
            reasons = []
            
            # 조건 1: 데드크로스
            if current_row.get('dead_cross', False):
                sell_conditions.append(True)
                confidence += 40
                reasons.append("SMA 데드크로스")
            
            # 조건 2: EMA 데드크로스 (추가 확인)
            elif current_row.get('ema_dead_cross', False):
                sell_conditions.append(True)
                confidence += 35
                reasons.append("EMA 데드크로스")
            
            # 조건 3: 약세 배열에서 가격이 빠른 이동평균 아래로 이탈
            elif (current_row.get('bearish_alignment', False) and 
                  not current_row.get('price_above_fast', False) and
                  df.iloc[i-1]['price_above_fast'] if i > 0 else False):
                sell_conditions.append(True)
                confidence += 30
                reasons.append("약세 배열에서 가격 이탈")
            
            if not any(sell_conditions):
                continue
            
            # 추가 확인 조건들
            
            # 이동평균 기울기 확인
            fast_slope = current_row.get('sma_fast_slope', 0)
            slow_slope = current_row.get('sma_slow_slope', 0)
            
            if fast_slope < -self.config.slope_threshold:
                confidence += 15
                reasons.append("빠른 MA 하락")
            
            if slow_slope < -self.config.slope_threshold:
                confidence += 10
                reasons.append("느린 MA 하락")
            
            # 3중 이동평균 배열 확인
            if self.config.use_triple_ma and current_row.get('bearish_alignment', False):
                confidence += 15
                reasons.append("약세 3중 배열")
            
            # 거래량 확인
            if self.config.volume_confirmation:
                volume_ratio = current_row.get('volume_ratio', 1.0)
                if volume_ratio >= self.config.volume_threshold:
                    confidence += 20
                    reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")
            
            # ATR 필터 (충분한 변동성)
            if self.config.atr_filter:
                atr_ratio = current_row.get('atr_ratio', 0.02)
                if atr_ratio >= self.config.min_atr_ratio:
                    confidence += 10
                    reasons.append("적정 변동성")
            
            # 가격 위치 확인
            if price < sma_fast and price < sma_slow:
                confidence += 10
                reasons.append("가격 < 이동평균")
            
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
                        'SMA_fast': sma_fast,
                        'SMA_slow': sma_slow,
                        'SMA_long': current_row.get('SMA_long', 0),
                        'ma_distance': current_row.get('ma_distance', 0),
                        'fast_slope': fast_slope,
                        'slow_slope': slow_slope,
                        'volume_ratio': current_row.get('volume_ratio', 1.0),
                        'ATR': current_row.get('ATR', 0)
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
        
        logger.info(f"이동평균 전략으로 {len(all_signals)}개 신호 생성")
        return all_signals
    
def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """신호 검증"""
        # 기본 검증: 가격과 신뢰도 확인
        if signal.price <= 0 or signal.confidence < 50:
            return False
        
        # 이동평균 특화 검증
        ma_distance = abs(signal.indicators.get('ma_distance', 0))
        atr_ratio = signal.indicators.get('ATR', 0) / signal.price if signal.price > 0 else 0
        
        # 이동평균이 너무 붙어있으면 (횡보) 신호 무효
        if ma_distance < 0.002:
            return False
        
        # 변동성이 너무 낮으면 신호 무효
        if self.config.atr_filter and atr_ratio < self.config.min_atr_ratio:
            return False
        
        # 매수/매도 신호 모두 추세 확인
        fast_slope = signal.indicators.get('fast_slope', 0)
        
        if signal.signal_type == 'BUY':
            return fast_slope >= 0  # 빠른 이동평균이 상승 중
        elif signal.signal_type == 'SELL':
            return fast_slope <= 0  # 빠른 이동평균이 하락 중
        
        return True 