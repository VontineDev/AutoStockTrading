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

class BollingerBandStrategy(BaseStrategy):
    """볼린저 밴드 기반 스윙 트레이딩 전략"""
    
    def __init__(self, config: Optional[BollingerBandConfig] = None):
        super().__init__(config or BollingerBandConfig())
        self.config: BollingerBandConfig = self.config
        logger.info(f"볼린저 밴드 전략 초기화: period={self.config.bb_period}, "
                   f"deviation={self.config.bb_deviation}")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        # 볼린저 밴드 계산
        df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(
            df['close'], 
            timeperiod=self.config.bb_period, 
            nbdevup=self.config.bb_deviation,
            nbdevdn=self.config.bb_deviation
        )
        
        # 볼린저 밴드 관련 지표
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
        
        # 밴드 터치/돌파 확인
        df['touching_upper'] = df['close'] >= df['BB_upper'] * 0.98
        df['touching_lower'] = df['close'] <= df['BB_lower'] * 1.02
        df['breaking_upper'] = df['close'] > df['BB_upper']
        df['breaking_lower'] = df['close'] < df['BB_lower']
        
        # 스퀴즈 감지 (밴드 폭 압축)
        df['BB_width_sma'] = talib.SMA(df['BB_width'], timeperiod=20)
        df['squeeze'] = df['BB_width'] < df['BB_width_sma'] * (1 - self.config.bb_squeeze_threshold)
        
        # RSI 필터 (선택적)
        if self.config.rsi_filter:
            df['RSI'] = talib.RSI(df['close'], timeperiod=self.config.rsi_period)
        
        # 거래량 지표
        if self.config.volume_confirmation:
            df['volume_sma'] = talib.SMA(df['volume'], timeperiod=20)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # 추가 보조 지표
        df['SMA_20'] = talib.SMA(df['close'], timeperiod=20)
        
        # 밴드 확장/압축 추세
        df['band_expanding'] = df['BB_width'] > df['BB_width'].shift(1)
        df['band_contracting'] = df['BB_width'] < df['BB_width'].shift(1)
        
        return df
    
    def _assess_risk_level(self, current_row: pd.Series, confidence: float) -> str:
        """리스크 레벨 평가"""
        bb_position = current_row.get('BB_position', 0.5)
        bb_width = current_row.get('BB_width', 0.05)
        
        # 밴드 극단에서는 고위험
        if bb_position > 0.9 or bb_position < 0.1:
            return 'HIGH'
        # 밴드 중앙 근처는 저위험
        elif 0.3 <= bb_position <= 0.7 and bb_width > 0.03:
            return 'LOW'
        else:
            return 'MEDIUM'
    
    def _generate_buy_signals(self, df: pd.DataFrame) -> List[TradeSignal]:
        """매수 신호 생성"""
        signals = []
        
        for i in range(len(df)):
            current_row = df.iloc[i]
            
            # 데이터 부족 시 건너뛰기
            if pd.isna(current_row.get('BB_lower')) or pd.isna(current_row.get('BB_position')):
                continue
            
            price = current_row['close']
            bb_position = current_row['BB_position']
            bb_width = current_row['BB_width']
            touching_lower = current_row.get('touching_lower', False)
            squeeze = current_row.get('squeeze', False)
            
            # 기본 매수 조건들
            buy_conditions = []
            confidence = 0.0
            reasons = []
            
            # 조건 1: 하단 밴드 터치 후 반등
            if touching_lower and bb_position > 0.1:
                buy_conditions.append(True)
                confidence += 40
                reasons.append("하단 밴드 터치 후 반등")
            
            # 조건 2: 스퀴즈 후 상승 돌파
            elif squeeze and current_row.get('band_expanding', False) and price > current_row['BB_middle']:
                buy_conditions.append(True)
                confidence += 35
                reasons.append("스퀴즈 후 상승 돌파")
            
            # 조건 3: 중간선 상승 돌파 (추세 추종)
            elif (price > current_row['BB_middle'] and 
                  current_row['close'] > current_row['SMA_20'] and
                  bb_width > 0.03):  # 충분한 변동성
                buy_conditions.append(True)
                confidence += 30
                reasons.append("중간선 상승 돌파")
            
            if not any(buy_conditions):
                continue
            
            # 추가 확인 조건들
            
            # RSI 필터 (과매수 구간 제외)
            if self.config.rsi_filter:
                rsi = current_row.get('RSI', 50)
                if rsi < self.config.rsi_overbought:
                    confidence += 15
                    reasons.append(f"RSI 적정 구간 ({rsi:.1f})")
                elif rsi > 75:  # 과매수 시 신뢰도 감소
                    confidence -= 10
            
            # 거래량 확인
            if self.config.volume_confirmation:
                volume_ratio = current_row.get('volume_ratio', 1.0)
                if volume_ratio >= self.config.volume_threshold:
                    confidence += 20
                    reasons.append(f"거래량 증가 ({volume_ratio:.1f}x)")
            
            # 밴드 확장 확인 (변동성 증가)
            if current_row.get('band_expanding', False):
                confidence += 10
                reasons.append("밴드 확장 (변동성 증가)")
            
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
                        'BB_upper': current_row['BB_upper'],
                        'BB_middle': current_row['BB_middle'],
                        'BB_lower': current_row['BB_lower'],
                        'BB_position': bb_position,
                        'BB_width': bb_width,
                        'RSI': current_row.get('RSI', 50),
                        'volume_ratio': current_row.get('volume_ratio', 1.0)
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
            if pd.isna(current_row.get('BB_upper')) or pd.isna(current_row.get('BB_position')):
                continue
            
            price = current_row['close']
            bb_position = current_row['BB_position']
            bb_width = current_row['BB_width']
            touching_upper = current_row.get('touching_upper', False)
            breaking_upper = current_row.get('breaking_upper', False)
            
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
            elif (price < current_row['BB_middle'] and 
                  current_row['close'] < current_row['SMA_20'] and
                  bb_width > 0.03):  # 충분한 변동성
                sell_conditions.append(True)
                confidence += 30
                reasons.append("중간선 하락 이탈")
            
            # 조건 3: 밴드 압축 시작 (변동성 감소)
            elif (current_row.get('band_contracting', False) and 
                  bb_position > 0.7 and bb_width < 0.025):
                sell_conditions.append(True)
                confidence += 25
                reasons.append("밴드 압축 시작")
            
            if not any(sell_conditions):
                continue
            
            # 추가 확인 조건들
            
            # RSI 필터 (과매도 구간 제외)
            if self.config.rsi_filter:
                rsi = current_row.get('RSI', 50)
                if rsi > self.config.rsi_oversold:
                    confidence += 15
                    reasons.append(f"RSI 적정 구간 ({rsi:.1f})")
                elif rsi < 25:  # 과매도 시 신뢰도 감소
                    confidence -= 10
            
            # 거래량 확인
            if self.config.volume_confirmation:
                volume_ratio = current_row.get('volume_ratio', 1.0)
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
                    symbol="",  # run_strategy에서 설정됨
                    signal_type='SELL',
                    price=price,
                    confidence=confidence,
                    reason=reason,
                    indicators={
                        'BB_upper': current_row['BB_upper'],
                        'BB_middle': current_row['BB_middle'],
                        'BB_lower': current_row['BB_lower'],
                        'BB_position': bb_position,
                        'BB_width': bb_width,
                        'RSI': current_row.get('RSI', 50),
                        'volume_ratio': current_row.get('volume_ratio', 1.0)
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
        
        logger.info(f"볼린저 밴드 전략으로 {len(all_signals)}개 신호 생성")
        return all_signals
    
    def validate_signal(self, signal: TradeSignal, data: pd.DataFrame) -> bool:
        """신호 검증"""
        # 기본 검증: 가격과 신뢰도 확인
        if signal.price <= 0 or signal.confidence < 50:
            return False
        
        # 볼린저 밴드 특화 검증
        bb_position = signal.indicators.get('BB_position', 0.5)
        bb_width = signal.indicators.get('BB_width', 0.05)
        
        # 밴드 폭이 너무 좁으면 (횡보 구간) 신호 무효
        if bb_width < 0.01:
            return False
        
        # 매수 신호 검증
        if signal.signal_type == 'BUY':
            return bb_position <= 0.8  # 상단 근처에서는 매수 금지
        
        # 매도 신호 검증
        elif signal.signal_type == 'SELL':
            return bb_position >= 0.2  # 하단 근처에서는 매도 금지
        
        return True 