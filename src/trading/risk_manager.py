#!/usr/bin/env python3
"""
위험 관리 모듈
- 포지션 크기 제한
- 손절매/익절매 관리
- 포트폴리오 리스크 제한
- 최대 손실 제한
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

@dataclass
class RiskParams:
    """위험 관리 매개변수"""
    max_position_size: float = 0.2  # 종목당 최대 투자 비중 (20%)
    max_portfolio_risk: float = 0.1  # 포트폴리오 최대 위험도 (10%)
    stop_loss_pct: float = 0.03     # 손절매 비율 (3%)
    take_profit_pct: float = 0.06   # 익절매 비율 (6%)
    max_daily_loss: float = 0.05    # 일일 최대 손실 (5%)
    max_drawdown: float = 0.15      # 최대 낙폭 제한 (15%)
    max_positions: int = 5          # 최대 보유 종목 수
    min_cash_ratio: float = 0.1     # 최소 현금 비율 (10%)

class RiskManager:
    """위험 관리 클래스"""
    
def __init__(self, risk_params: Optional[RiskParams] = None):
        """
        위험 관리자 초기화
        
        Args:
            risk_params: 위험 관리 매개변수
        """
        self.risk_params = risk_params or RiskParams()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 성과 추적
        self.daily_pnl: List[Tuple[datetime, float]] = []
        self.max_portfolio_value = 0.0
        
        self.logger.info("위험 관리자 초기화 완료")
    
def check_position_size_limit(self, symbol: str, order_amount: float, portfolio_value: float) -> bool:
        """포지션 크기 제한 확인"""
        position_ratio = order_amount / portfolio_value
        
        if position_ratio > self.risk_params.max_position_size:
            self.logger.warning(
                f"포지션 크기 제한 위반: {symbol} - "
                f"요청 비중 {position_ratio:.1%} > 제한 {self.risk_params.max_position_size:.1%}"
            )
            return False
        
        return True
    
def check_max_positions_limit(self, current_positions: int) -> bool:
        """최대 보유 종목 수 제한 확인"""
        if current_positions >= self.risk_params.max_positions:
            self.logger.warning(
                f"최대 보유 종목 수 초과: {current_positions} >= {self.risk_params.max_positions}"
            )
            return False
        
        return True
    
def check_cash_ratio_limit(self, cash: float, portfolio_value: float) -> bool:
        """최소 현금 비율 확인"""
        cash_ratio = cash / portfolio_value
        
        if cash_ratio < self.risk_params.min_cash_ratio:
            self.logger.warning(
                f"최소 현금 비율 미달: {cash_ratio:.1%} < {self.risk_params.min_cash_ratio:.1%}"
            )
            return False
        
        return True
    
def check_daily_loss_limit(self, portfolio_value: float, initial_value: float) -> bool:
        """일일 손실 제한 확인"""
        daily_return = (portfolio_value - initial_value) / initial_value
        
        if daily_return < -self.risk_params.max_daily_loss:
            self.logger.warning(
                f"일일 손실 제한 초과: {daily_return:.1%} < -{self.risk_params.max_daily_loss:.1%}"
            )
            return False
        
        return True
    
def check_drawdown_limit(self, current_value: float) -> bool:
        """최대 낙폭 제한 확인"""
        if current_value > self.max_portfolio_value:
            self.max_portfolio_value = current_value
        
        if self.max_portfolio_value > 0:
            drawdown = (self.max_portfolio_value - current_value) / self.max_portfolio_value
            
            if drawdown > self.risk_params.max_drawdown:
                self.logger.warning(
                    f"최대 낙폭 제한 초과: {drawdown:.1%} > {self.risk_params.max_drawdown:.1%}"
                )
                return False
        
        return True
    
def calculate_position_size(self, symbol: str, entry_price: float, portfolio_value: float, 
                              volatility: float = 0.02) -> int:
        """적정 포지션 크기 계산 (Kelly Criterion 기반)"""
        # 기본 포지션 크기 (포트폴리오 대비 비율)
        base_position_ratio = self.risk_params.max_position_size
        
        # 변동성 조정 (높은 변동성일수록 포지션 크기 감소)
        volatility_adjustment = min(1.0, 0.02 / max(volatility, 0.01))
        
        # 조정된 포지션 비율
        adjusted_ratio = base_position_ratio * volatility_adjustment
        
        # 투자 금액 계산
        investment_amount = portfolio_value * adjusted_ratio
        
        # 주식 수량 계산 (100주 단위로 반올림)
        quantity = int(investment_amount / entry_price / 100) * 100
        
        self.logger.info(
            f"포지션 크기 계산: {symbol} - "
            f"투자금액 {investment_amount:,.0f}원, 수량 {quantity}주"
        )
        
        return quantity
    
def calculate_stop_loss_price(self, symbol: str, entry_price: float, side: str) -> float:
        """손절매 가격 계산"""
        if side.upper() == 'BUY':
            stop_price = entry_price * (1 - self.risk_params.stop_loss_pct)
        else:  # SELL
            stop_price = entry_price * (1 + self.risk_params.stop_loss_pct)
        
        self.logger.info(f"손절매 가격 계산: {symbol} {side} - {stop_price:,.0f}원")
        return stop_price
    
def calculate_take_profit_price(self, symbol: str, entry_price: float, side: str) -> float:
        """익절매 가격 계산"""
        if side.upper() == 'BUY':
            profit_price = entry_price * (1 + self.risk_params.take_profit_pct)
        else:  # SELL
            profit_price = entry_price * (1 - self.risk_params.take_profit_pct)
        
        self.logger.info(f"익절매 가격 계산: {symbol} {side} - {profit_price:,.0f}원")
        return profit_price
    
def should_stop_loss(self, symbol: str, current_price: float, entry_price: float, side: str) -> bool:
        """손절매 조건 확인"""
        stop_price = self.calculate_stop_loss_price(symbol, entry_price, side)
        
        if side.upper() == 'BUY':
            should_stop = current_price <= stop_price
        else:  # SELL
            should_stop = current_price >= stop_price
        
        if should_stop:
            loss_pct = abs(current_price - entry_price) / entry_price
            self.logger.warning(
                f"손절매 신호: {symbol} - 현재가 {current_price:,.0f}원, "
                f"손실률 {loss_pct:.1%}"
            )
        
        return should_stop
    
def should_take_profit(self, symbol: str, current_price: float, entry_price: float, side: str) -> bool:
        """익절매 조건 확인"""
        profit_price = self.calculate_take_profit_price(symbol, entry_price, side)
        
        if side.upper() == 'BUY':
            should_profit = current_price >= profit_price
        else:  # SELL
            should_profit = current_price <= profit_price
        
        if should_profit:
            profit_pct = abs(current_price - entry_price) / entry_price
            self.logger.info(
                f"익절매 신호: {symbol} - 현재가 {current_price:,.0f}원, "
                f"수익률 {profit_pct:.1%}"
            )
        
        return should_profit
    
def evaluate_portfolio_risk(self, positions: Dict[str, Any], market_data: Dict[str, float]) -> Dict[str, float]:
        """포트폴리오 위험도 평가"""
        total_value = 0
        total_risk = 0
        concentration_risk = 0
        
        # 종목별 위험도 계산
        for symbol, position in positions.items():
            if symbol not in market_data:
                continue
            
            market_value = position.quantity * market_data[symbol]
            total_value += market_value
            
            # 개별 종목 리스크 (변동성 기반)
            individual_risk = market_value * 0.02  # 기본 2% 변동성 가정
            total_risk += individual_risk
        
        # 집중도 위험 (종목 수가 적을수록 높음)
        num_positions = len(positions)
        if num_positions > 0:
            concentration_risk = 1.0 / num_positions
        
        # 전체 위험도
        portfolio_risk = (total_risk / max(total_value, 1)) + concentration_risk
        
        risk_metrics = {
            'total_value': total_value,
            'total_risk': total_risk,
            'portfolio_risk': portfolio_risk,
            'concentration_risk': concentration_risk,
            'num_positions': num_positions,
            'avg_position_size': total_value / max(num_positions, 1)
        }
        
        self.logger.info(f"포트폴리오 위험도: {portfolio_risk:.2%}")
        return risk_metrics
    
def check_correlation_risk(self, symbols: List[str], sector_map: Dict[str, str] = None) -> bool:
        """상관관계 위험 확인 (같은 섹터 비중 제한)"""
        if not sector_map:
            return True  # 섹터 정보가 없으면 통과
        
        sector_count = {}
        for symbol in symbols:
            sector = sector_map.get(symbol, 'Unknown')
            sector_count[sector] = sector_count.get(sector, 0) + 1
        
        # 같은 섹터 종목이 전체의 50% 이상이면 위험
        max_sector_ratio = 0.5
        total_positions = len(symbols)
        
        for sector, count in sector_count.items():
            ratio = count / total_positions
            if ratio > max_sector_ratio:
                self.logger.warning(
                    f"섹터 집중도 위험: {sector} 섹터 {ratio:.1%} > {max_sector_ratio:.1%}"
                )
                return False
        
        return True
    
def get_risk_summary(self) -> Dict[str, Any]:
        """위험 관리 현황 요약"""
        return {
            'risk_params': {
                'max_position_size': f"{self.risk_params.max_position_size:.1%}",
                'stop_loss_pct': f"{self.risk_params.stop_loss_pct:.1%}",
                'take_profit_pct': f"{self.risk_params.take_profit_pct:.1%}",
                'max_daily_loss': f"{self.risk_params.max_daily_loss:.1%}",
                'max_drawdown': f"{self.risk_params.max_drawdown:.1%}",
                'max_positions': self.risk_params.max_positions,
                'min_cash_ratio': f"{self.risk_params.min_cash_ratio:.1%}"
            },
            'current_state': {
                'max_portfolio_value': self.max_portfolio_value,
                'daily_pnl_records': len(self.daily_pnl)
            }
        }
    
def update_daily_pnl(self, date: datetime, pnl: float):
        """일일 손익 업데이트"""
        self.daily_pnl.append((date, pnl))
        
        # 과거 30일 데이터만 유지
        if len(self.daily_pnl) > 30:
            self.daily_pnl = self.daily_pnl[-30:]
    
def reset(self):
        """위험 관리자 초기화"""
        self.daily_pnl.clear()
        self.max_portfolio_value = 0.0
        self.logger.info("위험 관리자 초기화 완료") 