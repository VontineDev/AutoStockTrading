"""
백테스트 서비스
백테스팅 관련 로직을 처리하는 서비스
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import numpy as np

from src.trading.backtest import BacktestEngine, BacktestConfig
from src.strategies.base_strategy import BaseStrategy


class BacktestService:
    """백테스트 관련 서비스"""
    
    def __init__(self):
        self.engine = None
    
    def create_backtest_config(
        self,
        initial_capital: float = 1000000,
        commission_rate: float = 0.00015,
        slippage_rate: float = 0.001,
        max_positions: int = 5,
        risk_per_trade: float = 0.02
    ) -> BacktestConfig:
        """백테스트 설정 생성"""
        config = BacktestConfig(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage_rate=slippage_rate,
            max_positions=max_positions,
            risk_per_trade=risk_per_trade
        )
        return config
    
    def run_backtest(
        self,
        strategy: BaseStrategy,
        data: Dict[str, pd.DataFrame],
        config: BacktestConfig
    ) -> Optional[Dict[str, Any]]:
        """백테스트 실행"""
        try:
            self.engine = BacktestEngine(config)
            results = self.engine.run_backtest(strategy, data)
            return results
            
        except Exception as e:
            logging.error(f"백테스트 실행 실패: {e}")
            return None
    
    @st.cache_data
    def run_simple_backtest(
        _self,
        strategy_name: str,
        symbols: List[str],
        data: Dict[str, pd.DataFrame],
        initial_capital: float = 1000000,
        **strategy_params
    ) -> Optional[Dict[str, Any]]:
        """간단한 백테스트 실행"""
        try:
            from src.ui.services.strategy_service import get_strategy_service
            
            strategy_service = get_strategy_service()
            strategy = strategy_service.get_strategy_instance(strategy_name, **strategy_params)
            
            if strategy is None:
                return None
            
            config = _self.create_backtest_config(initial_capital=initial_capital)
            return _self.run_backtest(strategy, data, config)
            
        except Exception as e:
            logging.error(f"간단 백테스트 실행 실패: {e}")
            return None
    
    def calculate_performance_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """성능 지표 계산 (equity_curve['total_value'] 사용)"""
        try:
            if not isinstance(results, dict) or 'equity_curve' not in results:
                return {}
            portfolio_values = results['equity_curve']['total_value']
            if isinstance(portfolio_values, pd.DataFrame):
                if portfolio_values.shape[1] == 1:
                    portfolio_values = portfolio_values.iloc[:, 0]
                else:
                    portfolio_values = portfolio_values.iloc[:, 0]
            elif isinstance(portfolio_values, (list, np.ndarray)):
                portfolio_values = pd.Series(portfolio_values)
            elif not isinstance(portfolio_values, pd.Series):
                portfolio_values = pd.Series(portfolio_values)
            if portfolio_values.empty or len(portfolio_values) < 2:
                return {}
            returns = portfolio_values.pct_change().dropna()
            total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0] - 1) * 100
            metrics = {}
            
            # 기본 수익률 지표
            metrics['총 수익률 (%)'] = float(round(total_return, 2))
            
            # 연간 수익률
            days = len(portfolio_values)
            annual_return = ((portfolio_values.iloc[-1] / portfolio_values.iloc[0]) ** (252 / days) - 1) * 100
            metrics['연간 수익률 (%)'] = float(round(annual_return, 2))
            
            # 변동성 (연환산)
            volatility = returns.std() * (252 ** 0.5) * 100
            metrics['변동성 (%)'] = float(round(volatility, 2))
            
            # 샤프 비율 (무위험 수익률 3% 가정)
            excess_returns = returns - (0.03 / 252)
            if returns.std() != 0:
                sharpe_ratio = (excess_returns.mean() / returns.std()) * (252 ** 0.5)
                metrics['샤프 비율'] = float(round(sharpe_ratio, 2))
            else:
                metrics['샤프 비율'] = 0.0
            
            # 최대 낙폭 (MDD)
            peak = portfolio_values.expanding().max()
            drawdown = (portfolio_values - peak) / peak
            max_drawdown = drawdown.min() * 100
            metrics['최대 낙폭 (%)'] = float(round(max_drawdown, 2))
            
            # 승률
            trades = results.get('trades', None)
            if trades is not None:
                if isinstance(trades, (pd.DataFrame, pd.Series)):
                    if not trades.empty:
                        if isinstance(trades, pd.DataFrame):
                            profitable_trades = (trades['pnl'] > 0).sum() if 'pnl' in trades.columns else 0
                            total_trades = len(trades)
                        else:  # Series
                            profitable_trades = (trades > 0).sum()
                            total_trades = len(trades)
                        win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
                        metrics['승률 (%)'] = float(round(win_rate, 2))
                        metrics['총 거래 횟수'] = int(total_trades)
                elif isinstance(trades, list):
                    if len(trades) > 0:
                        profitable_trades = sum(1 for trade in trades if isinstance(trade, dict) and trade.get('pnl', 0) > 0)
                        total_trades = len(trades)
                        win_rate = (profitable_trades / total_trades) * 100 if total_trades > 0 else 0
                        metrics['승률 (%)'] = float(round(win_rate, 2))
                        metrics['총 거래 횟수'] = int(total_trades)
            
            return metrics
            
        except Exception as e:
            logging.error(f"성능 지표 계산 실패: {e}")
            return {}
    
    def compare_strategies(
        self,
        strategies: List[Tuple[str, Dict[str, Any]]],
        data: Dict[str, pd.DataFrame],
        initial_capital: float = 1000000
    ) -> pd.DataFrame:
        """여러 전략 비교"""
        try:
            results = []
            for strategy_name, params in strategies:
                backtest_result = self.run_simple_backtest(
                    strategy_name=strategy_name,
                    symbols=list(data.keys()),
                    data=data,
                    initial_capital=initial_capital,
                    **params
                )
                if backtest_result:
                    metrics = self.calculate_performance_metrics(backtest_result)
                    # metrics['전략'] = strategy_name  # float dict에 str 금지, 아래에서 DataFrame에 추가
                    results.append((strategy_name, metrics))
            if results:
                df = pd.DataFrame([m for _, m in results])
                df['전략'] = [s for s, _ in results]
                df.set_index('전략', inplace=True)
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logging.error(f"전략 비교 실패: {e}")
            return pd.DataFrame()
    
    def optimize_parameters(
        self,
        strategy_name: str,
        data: Dict[str, pd.DataFrame],
        param_ranges: Dict[str, List],
        metric: str = '샤프 비율',
        initial_capital: float = 1000000
    ) -> Dict[str, Any]:
        """매개변수 최적화"""
        try:
            from itertools import product
            
            best_params = None
            best_score = float('-inf') if metric != '최대 낙폭 (%)' else 0
            best_result = None
            all_results = []
            
            # 모든 매개변수 조합 생성
            param_names = list(param_ranges.keys())
            param_values = list(param_ranges.values())
            
            for combination in product(*param_values):
                params = dict(zip(param_names, combination))
                
                result = self.run_simple_backtest(
                    strategy_name=strategy_name,
                    symbols=list(data.keys()),
                    data=data,
                    initial_capital=initial_capital,
                    **params
                )
                
                if result:
                    metrics = self.calculate_performance_metrics(result)
                    score = metrics.get(metric, float('-inf'))
                    
                    # 최대 낙폭은 낮을수록 좋음
                    if metric == '최대 낙폭 (%)':
                        if score > best_score:  # 낙폭이 작을수록 좋음 (음수이므로)
                            best_score = score
                            best_params = params
                            best_result = result
                    else:
                        if score > best_score:
                            best_score = score
                            best_params = params
                            best_result = result
                    
                    all_results.append({
                        'params': params,
                        'metrics': metrics,
                        'score': score
                    })
            
            return {
                'best_params': best_params,
                'best_score': best_score,
                'best_result': best_result,
                'all_results': all_results
            }
            
        except Exception as e:
            logging.error(f"매개변수 최적화 실패: {e}")
            return {}


# 싱글톤 인스턴스
_backtest_service_instance = None

def get_backtest_service() -> BacktestService:
    """백테스트 서비스 싱글톤 인스턴스 반환"""
    global _backtest_service_instance
    if _backtest_service_instance is None:
        _backtest_service_instance = BacktestService()
    return _backtest_service_instance 