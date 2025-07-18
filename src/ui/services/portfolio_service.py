"""
포트폴리오 서비스
포트폴리오 관리 관련 로직을 처리하는 서비스
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging


class PortfolioService:
    """포트폴리오 관련 서비스"""
    
    def __init__(self):
        self.max_portfolio_value = 1000000  # 100만원
        self.max_positions = 5  # 최대 5종목
        self.max_position_size = 0.25  # 종목당 최대 25%
    
    def calculate_position_size(
        self,
        stock_price: float,
        portfolio_value: float,
        risk_level: str = 'medium'
    ) -> Tuple[int, float]:
        """포지션 크기 계산"""
        try:
            # 리스크 레벨별 최대 투자 비율
            risk_multipliers = {
                'low': 0.15,      # 15%
                'medium': 0.20,   # 20%
                'high': 0.25      # 25%
            }
            
            max_investment_ratio = risk_multipliers.get(risk_level, 0.20)
            max_investment = portfolio_value * max_investment_ratio
            
            # 매수 가능 수량 계산
            max_shares = int(max_investment // stock_price)
            actual_investment = max_shares * stock_price
            
            return max_shares, actual_investment
            
        except Exception as e:
            logging.error(f"포지션 크기 계산 실패: {e}")
            return 0, 0.0
    
    def calculate_portfolio_metrics(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """포트폴리오 지표 계산"""
        try:
            if not positions:
                return {
                    'total_value': 0,
                    'total_cost': 0,
                    'total_pnl': 0,
                    'total_pnl_percent': 0,
                    'position_count': 0,
                    'largest_position': 0,
                    'portfolio_concentration': 0
                }
            
            total_value = 0
            total_cost = 0
            position_values = []
            
            for symbol, position in positions.items():
                shares = position.get('shares', 0)
                avg_price = position.get('avg_price', 0)
                current_price = position.get('current_price', 0)
                
                position_cost = shares * avg_price
                position_value = shares * current_price
                
                total_cost += position_cost
                total_value += position_value
                position_values.append(position_value)
            
            total_pnl = total_value - total_cost
            total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0
            
            # 집중도 계산 (가장 큰 포지션의 비율)
            largest_position = max(position_values) if position_values else 0
            portfolio_concentration = (largest_position / total_value * 100) if total_value > 0 else 0
            
            return {
                'total_value': round(total_value, 0),
                'total_cost': round(total_cost, 0),
                'total_pnl': round(total_pnl, 0),
                'total_pnl_percent': round(total_pnl_percent, 2),
                'position_count': len(positions),
                'largest_position': round(largest_position, 0),
                'portfolio_concentration': round(portfolio_concentration, 2)
            }
            
        except Exception as e:
            logging.error(f"포트폴리오 지표 계산 실패: {e}")
            return {}
    
    def check_risk_limits(self, positions: Dict[str, Dict], new_investment: float) -> Tuple[bool, str]:
        """리스크 한도 체크"""
        try:
            current_metrics = self.calculate_portfolio_metrics(positions)
            current_value = current_metrics.get('total_value', 0)
            
            # 총 포트폴리오 가치 체크
            if current_value + new_investment > self.max_portfolio_value:
                return False, f"포트폴리오 한도 초과: {self.max_portfolio_value:,.0f}원"
            
            # 포지션 수 체크
            if len(positions) >= self.max_positions:
                return False, f"최대 포지션 수 초과: {self.max_positions}개"
            
            # 개별 포지션 크기 체크
            if current_value > 0:
                position_ratio = new_investment / (current_value + new_investment)
                if position_ratio > self.max_position_size:
                    return False, f"개별 포지션 크기 초과: 최대 {self.max_position_size*100}%"
            
            return True, "리스크 한도 내"
            
        except Exception as e:
            logging.error(f"리스크 한도 체크 실패: {e}")
            return False, f"리스크 체크 실패: {e}"
    
    def suggest_rebalancing(self, positions: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """리밸런싱 제안"""
        try:
            suggestions = []
            metrics = self.calculate_portfolio_metrics(positions)
            
            if not positions:
                return suggestions
            
            total_value = metrics.get('total_value', 0)
            concentration = metrics.get('portfolio_concentration', 0)
            
            # 집중도가 높은 경우
            if concentration > 40:
                suggestions.append({
                    'type': 'concentration_risk',
                    'message': f"포트폴리오 집중도가 {concentration:.1f}%로 높습니다. 분산투자를 권장합니다.",
                    'priority': 'high'
                })
            
            # 개별 포지션 체크
            for symbol, position in positions.items():
                shares = position.get('shares', 0)
                current_price = position.get('current_price', 0)
                position_value = shares * current_price
                position_ratio = (position_value / total_value * 100) if total_value > 0 else 0
                
                if position_ratio > 30:
                    suggestions.append({
                        'type': 'position_size',
                        'symbol': symbol,
                        'message': f"{symbol} 포지션이 {position_ratio:.1f}%로 과도합니다. 일부 매도를 고려하세요.",
                        'priority': 'medium'
                    })
            
            # 포지션 수가 적은 경우
            if len(positions) < 3 and total_value > 500000:
                suggestions.append({
                    'type': 'diversification',
                    'message': f"포지션 수가 {len(positions)}개로 적습니다. 추가 분산투자를 권장합니다.",
                    'priority': 'low'
                })
            
            return suggestions
            
        except Exception as e:
            logging.error(f"리밸런싱 제안 실패: {e}")
            return []
    
    @st.cache_data
    def calculate_optimal_allocation(_self, symbols: List[str], data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """최적 자산 배분 계산 (균등가중)"""
        try:
            if not symbols or not data:
                return {}
            
            # 단순 균등 가중 (동일한 비중)
            equal_weight = 1.0 / len(symbols)
            allocation = {symbol: equal_weight for symbol in symbols}
            
            return allocation
            
        except Exception as e:
            logging.error(f"최적 배분 계산 실패: {e}")
            return {}
    
    def simulate_portfolio(
        self,
        allocation: Dict[str, float],
        data: Dict[str, pd.DataFrame],
        initial_capital: float = 1000000
    ) -> pd.Series:
        """포트폴리오 시뮬레이션"""
        try:
            if not allocation or not data:
                return pd.Series()
            
            # 모든 데이터의 공통 날짜 인덱스 찾기
            common_dates = None
            for symbol in allocation.keys():
                if symbol in data:
                    if common_dates is None:
                        common_dates = data[symbol].index
                    else:
                        common_dates = common_dates.intersection(data[symbol].index)
            
            if common_dates is None or len(common_dates) == 0:
                return pd.Series()
            
            # 수익률 계산
            returns = pd.DataFrame(index=common_dates)
            for symbol, weight in allocation.items():
                if symbol in data:
                    symbol_data = data[symbol].reindex(common_dates)
                    symbol_returns = symbol_data['close'].pct_change()
                    returns[symbol] = symbol_returns * weight
            
            # 포트폴리오 수익률
            portfolio_returns = returns.sum(axis=1)
            
            # 누적 수익률로 포트폴리오 가치 계산
            portfolio_value = initial_capital * (1 + portfolio_returns).cumprod()
            
            return portfolio_value
            
        except Exception as e:
            logging.error(f"포트폴리오 시뮬레이션 실패: {e}")
            return pd.Series()


# 싱글톤 인스턴스
_portfolio_service_instance = None

def get_portfolio_service() -> PortfolioService:
    """포트폴리오 서비스 싱글톤 인스턴스 반환"""
    global _portfolio_service_instance
    if _portfolio_service_instance is None:
        _portfolio_service_instance = PortfolioService()
    return _portfolio_service_instance 