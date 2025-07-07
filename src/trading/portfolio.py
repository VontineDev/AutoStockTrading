#!/usr/bin/env python3
"""
포트폴리오 관리 모듈
- 포지션 관리 및 추적
- 자산 평가 및 수익률 계산
- 매매 기록 관리
- 리스크 메트릭 계산
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
import pandas as pd
import numpy as np
from dataclasses import dataclass

@dataclass
class Position:
    """개별 포지션 정보"""
    symbol: str
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0
    
    @property
    def market_value(self) -> float:
        """현재 시장 가치"""
        return self.quantity * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        """미실현 손익"""
        return (self.current_price - self.entry_price) * self.quantity
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """미실현 손익 비율"""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price

@dataclass
class Trade:
    """매매 기록"""
    symbol: str
    action: str  # 'BUY' or 'SELL'
    quantity: int
    price: float
    date: datetime
    commission: float = 0.0
    tax: float = 0.0
    
    @property
    def gross_amount(self) -> float:
        """수수료 제외 금액"""
        return self.quantity * self.price
    
    @property
    def net_amount(self) -> float:
        """수수료 포함 순 금액"""
        return self.gross_amount + self.commission + self.tax

class Portfolio:
    """포트폴리오 관리 클래스"""
    
    def __init__(self, initial_cash: float = 1000000.0, commission_rate: float = 0.00015, tax_rate: float = 0.0025):
        """
        포트폴리오 초기화
        
        Args:
            initial_cash: 초기 현금
            commission_rate: 매매 수수료율 (기본: 0.015%)
            tax_rate: 거래세율 (기본: 0.25%, 매도시만 적용)
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate
        self.tax_rate = tax_rate
        
        # 포지션 관리
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        
        # 성과 추적
        self.portfolio_values: List[Tuple[datetime, float]] = []
        self.daily_returns: List[float] = []
        
        # 로깅
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 초기 포트폴리오 가치 기록
        self.portfolio_values.append((datetime.now(), initial_cash))
    
    def buy(self, symbol: str, quantity: int, price: float, date: datetime = None) -> bool:
        """매수 주문 실행"""
        if date is None:
            date = datetime.now()
        
        # 필요 금액 계산 (수수료 포함)
        gross_amount = quantity * price
        commission = gross_amount * self.commission_rate
        total_cost = gross_amount + commission
        
        # 현금 부족 확인
        if total_cost > self.cash:
            self.logger.warning(f"현금 부족: 필요 {total_cost:,.0f}원, 보유 {self.cash:,.0f}원")
            return False
        
        # 매수 실행
        self.cash -= total_cost
        
        # 포지션 업데이트
        if symbol in self.positions:
            # 기존 포지션에 추가
            existing_pos = self.positions[symbol]
            total_quantity = existing_pos.quantity + quantity
            avg_price = ((existing_pos.quantity * existing_pos.entry_price) + 
                        (quantity * price)) / total_quantity
            
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=total_quantity,
                entry_price=avg_price,
                entry_date=existing_pos.entry_date,
                current_price=price
            )
        else:
            # 신규 포지션
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                entry_price=price,
                entry_date=date,
                current_price=price
            )
        
        # 매매 기록
        trade = Trade(
            symbol=symbol,
            action='BUY',
            quantity=quantity,
            price=price,
            date=date,
            commission=commission
        )
        self.trades.append(trade)
        
        self.logger.info(f"매수 완료: {symbol} {quantity}주 @ {price:,.0f}원 (수수료: {commission:,.0f}원)")
        return True
    
    def sell(self, symbol: str, quantity: int, price: float, date: datetime = None) -> bool:
        """매도 주문 실행"""
        if date is None:
            date = datetime.now()
        
        # 보유 수량 확인
        if symbol not in self.positions:
            self.logger.warning(f"보유하지 않은 종목: {symbol}")
            return False
        
        position = self.positions[symbol]
        if position.quantity < quantity:
            self.logger.warning(f"보유 수량 부족: 요청 {quantity}주, 보유 {position.quantity}주")
            return False
        
        # 매도 금액 계산 (수수료 및 세금 포함)
        gross_amount = quantity * price
        commission = gross_amount * self.commission_rate
        tax = gross_amount * self.tax_rate  # 매도시만 거래세 적용
        net_amount = gross_amount - commission - tax
        
        # 매도 실행
        self.cash += net_amount
        
        # 포지션 업데이트
        if position.quantity == quantity:
            # 전량 매도 - 포지션 제거
            del self.positions[symbol]
        else:
            # 일부 매도 - 수량만 감소
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=position.quantity - quantity,
                entry_price=position.entry_price,
                entry_date=position.entry_date,
                current_price=price
            )
        
        # 매매 기록
        trade = Trade(
            symbol=symbol,
            action='SELL',
            quantity=quantity,
            price=price,
            date=date,
            commission=commission,
            tax=tax
        )
        self.trades.append(trade)
        
        self.logger.info(f"매도 완료: {symbol} {quantity}주 @ {price:,.0f}원 (수수료: {commission:,.0f}원, 세금: {tax:,.0f}원)")
        return True
    
    def update_prices(self, prices: Dict[str, float], date: datetime = None):
        """현재 가격 업데이트"""
        if date is None:
            date = datetime.now()
        
        for symbol, price in prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
        
        # 포트폴리오 가치 기록
        total_value = self.get_total_value()
        self.portfolio_values.append((date, total_value))
        
        # 일간 수익률 계산
        if len(self.portfolio_values) > 1:
            prev_value = self.portfolio_values[-2][1]
            daily_return = (total_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)
    
    def get_total_value(self) -> float:
        """총 포트폴리오 가치"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
    
    def get_positions_summary(self) -> pd.DataFrame:
        """포지션 요약 정보"""
        if not self.positions:
            return pd.DataFrame()
        
        data = []
        for pos in self.positions.values():
            data.append({
                '종목코드': pos.symbol,
                '수량': pos.quantity,
                '평균단가': pos.entry_price,
                '현재가': pos.current_price,
                '평가금액': pos.market_value,
                '손익금액': pos.unrealized_pnl,
                '손익률': pos.unrealized_pnl_pct * 100,
                '진입일': pos.entry_date.strftime('%Y-%m-%d')
            })
        
        return pd.DataFrame(data)
    
    def get_trades_summary(self) -> pd.DataFrame:
        """매매 기록 요약"""
        if not self.trades:
            return pd.DataFrame()
        
        data = []
        for trade in self.trades:
            data.append({
                '날짜': trade.date.strftime('%Y-%m-%d %H:%M:%S'),
                '종목코드': trade.symbol,
                '매매구분': trade.action,
                '수량': trade.quantity,
                '체결가': trade.price,
                '거래금액': trade.gross_amount,
                '수수료': trade.commission,
                '세금': trade.tax,
                '순거래금액': trade.net_amount if trade.action == 'SELL' else -trade.net_amount
            })
        
        return pd.DataFrame(data)
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """성과 지표 계산"""
        if len(self.portfolio_values) < 2:
            return {}
        
        # 기본 지표
        current_value = self.get_total_value()
        total_return = (current_value - self.initial_cash) / self.initial_cash
        
        # 일간 수익률 기반 지표
        if not self.daily_returns:
            return {
                'total_return': total_return,
                'current_value': current_value,
                'total_pnl': current_value - self.initial_cash
            }
        
        returns_array = np.array(self.daily_returns)
        
        # 연환산 수익률 및 변동성
        trading_days = 252
        annualized_return = np.mean(returns_array) * trading_days
        annualized_volatility = np.std(returns_array) * np.sqrt(trading_days)
        
        # 샤프 비율 (무위험 수익률 3% 가정)
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility if annualized_volatility > 0 else 0
        
        # 최대 낙폭 (MDD) 계산
        values = [v[1] for v in self.portfolio_values]
        peak = values[0]
        max_drawdown = 0
        
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # 승률 계산
        profitable_trades = 0
        total_completed_trades = 0
        
        # 매도 거래 기준으로 손익 계산
        for trade in self.trades:
            if trade.action == 'SELL':
                total_completed_trades += 1
                # 해당 종목의 이전 매수 거래 찾기 (단순화)
                for prev_trade in reversed(self.trades):
                    if prev_trade.symbol == trade.symbol and prev_trade.action == 'BUY' and prev_trade.date < trade.date:
                        if trade.price > prev_trade.price:
                            profitable_trades += 1
                        break
        
        win_rate = profitable_trades / total_completed_trades if total_completed_trades > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'current_value': current_value,
            'total_pnl': current_value - self.initial_cash,
            'cash': self.cash,
            'total_trades': len(self.trades),
            'completed_trades': total_completed_trades
        }
    
    def get_equity_curve(self) -> pd.DataFrame:
        """자산 곡선 데이터"""
        if not self.portfolio_values:
            return pd.DataFrame()
        
        data = []
        for date, value in self.portfolio_values:
            data.append({
                'date': date,
                'portfolio_value': value,
                'return_pct': (value - self.initial_cash) / self.initial_cash * 100
            })
        
        return pd.DataFrame(data)
    
    def reset(self):
        """포트폴리오 초기화"""
        self.cash = self.initial_cash
        self.positions.clear()
        self.trades.clear()
        self.portfolio_values = [(datetime.now(), self.initial_cash)]
        self.daily_returns.clear()
        self.logger.info("포트폴리오 초기화 완료")

# 하위 호환성을 위한 별칭
PortfolioManager = Portfolio 