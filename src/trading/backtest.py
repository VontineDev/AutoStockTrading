"""
스윙 트레이딩 백테스팅 엔진

TA-Lib 기반 매매 전략의 과거 성과를 검증하고 분석하는 백테스팅 시스템입니다.
100만원 규모 포트폴리오에 최적화되어 있습니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass, field
import copy

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """개별 거래 기록"""
    entry_date: datetime
    exit_date: datetime
    symbol: str
    trade_type: str  # 'LONG', 'SHORT'
    entry_price: float
    exit_price: float
    quantity: float
    entry_reason: str
    exit_reason: str
    commission: float = 0.0
    slippage: float = 0.0
    
    @property
def return_pct(self) -> float:
        """수익률 계산"""
        if self.trade_type == 'LONG':
            return (self.exit_price - self.entry_price) / self.entry_price
        else:  # SHORT
            return (self.entry_price - self.exit_price) / self.entry_price
    
    @property
def profit_loss(self) -> float:
        """손익 계산"""
        return self.quantity * (self.exit_price - self.entry_price) * (1 if self.trade_type == 'LONG' else -1)
    
    @property
def holding_days(self) -> int:
        """보유 기간"""
        return (self.exit_date - self.entry_date).days

@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    quantity: float
    entry_price: float
    entry_date: datetime
    stop_loss: float
    take_profit: float
    entry_reason: str
    position_type: str = 'LONG'  # 'LONG', 'SHORT'
    
    @property
def market_value(self) -> float:
        """현재 시장가치"""
        return self.quantity * self.entry_price
    
def current_return(self, current_price: float) -> float:
        """현재 수익률"""
        if self.position_type == 'LONG':
            return (current_price - self.entry_price) / self.entry_price
        else:
            return (self.entry_price - current_price) / self.entry_price

@dataclass
class BacktestConfig:
    """백테스팅 설정"""
    initial_capital: float = 1000000  # 초기 자본 100만원
    commission_rate: float = 0.00015  # 수수료율 (0.015%)
    slippage_rate: float = 0.001  # 슬리피지 (0.1%)
    position_size_method: str = 'fixed_amount'  # 'fixed_amount', 'percent', 'volatility'
    max_positions: int = 5  # 최대 동시 보유 종목 수
    risk_per_trade: float = 0.02  # 거래당 리스크 (2%)
    enable_stop_loss: bool = True
    enable_take_profit: bool = True
    rebalance_frequency: str = 'daily'  # 'daily', 'weekly', 'monthly'

class BacktestEngine:
    """백테스팅 엔진"""
    
def __init__(self, config: BacktestConfig = None):
        """백테스팅 엔진 초기화"""
        self.config = config or BacktestConfig()
        self.reset()
        
        logger.info(f"백테스팅 엔진 초기화: 초기자본 {self.config.initial_capital:,.0f}원")
    
def reset(self):
        """백테스트 상태 초기화"""
        self.cash = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        self.daily_returns: List[float] = []
        self.current_date: Optional[datetime] = None
        self._processed_signals = set()  # 신호 처리 기록 초기화
        
def run_backtest(self, strategy, data: Dict[str, pd.DataFrame], 
                     start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        백테스팅 실행
        
        Args:
            strategy: 매매 전략 객체
            data: 종목별 OHLCV 데이터 {symbol: DataFrame}
            start_date: 백테스팅 시작날짜 (YYYY-MM-DD), None이면 데이터 시작부터
            end_date: 백테스팅 종료날짜 (YYYY-MM-DD), None이면 데이터 끝까지
            
        Returns:
            백테스팅 결과
        """
        # 전체 날짜 범위 수집
        all_dates = set()
        for symbol, df in data.items():
            if 'date' in df.columns:
                all_dates.update(pd.to_datetime(df['date'], format='mixed', errors='coerce').dt.date)
            else:
                all_dates.update(pd.to_datetime(df.index, format='mixed', errors='coerce').date)
        
        # 날짜 범위 설정
        if not all_dates:
            logger.error("처리할 데이터가 없습니다.")
            return self._empty_results()
        
        sorted_dates = sorted(all_dates)
        
        if start_date:
            start_dt = pd.to_datetime(start_date, format='mixed', errors='coerce').date()
            sorted_dates = [d for d in sorted_dates if d >= start_dt]
        
        if end_date:
            end_dt = pd.to_datetime(end_date, format='mixed', errors='coerce').date()
            sorted_dates = [d for d in sorted_dates if d <= end_dt]
        
        if not sorted_dates:
            logger.error("날짜 범위에 해당하는 데이터가 없습니다.")
            return self._empty_results()
        
        # 백테스팅 실행
        for date in sorted_dates:
            self.current_date = pd.to_datetime(date, format='mixed', errors='coerce')
            self._process_daily_signals(strategy, data, date)
            self._update_positions(data, date)
            self._record_equity()
        
        # 미청산 포지션 정리
        if sorted_dates:
            self._close_all_positions(data, sorted_dates[-1])
        
        # 결과 분석
        results = self._analyze_results()
        logger.info(f"백테스팅 완료: 총 {len(self.trades)}개 거래, 최종 수익률 {results['total_return']:.2%}")
        
        return results
    
def _process_daily_signals(self, strategy, data: Dict[str, pd.DataFrame], date):
        """일별 매매 신호 처리"""
        for symbol, df in data.items():
            # 해당 날짜의 데이터 추출
            if 'date' in df.columns:
                day_data = df[df['date'].dt.date == date] if hasattr(df['date'], 'dt') else df[df['date'] == date]
            else:
                # date 컬럼이 없으면 인덱스 기반
                day_data = df[df.index.date == date] if hasattr(df.index, 'date') else pd.DataFrame()
            
            if day_data.empty:
                continue
            
            # 전략 실행 (충분한 과거 데이터 포함)
            try:
                historical_data = df[df.index <= pd.to_datetime(date, format='mixed', errors='coerce')] if 'date' not in df.columns else \
                                df[df['date'] <= pd.to_datetime(date, format='mixed', errors='coerce')]
                
                if len(historical_data) < strategy.config.min_data_length:
                    continue
                
                signals = strategy.run_strategy(historical_data, symbol)
                
                # 모든 신호 처리 (중복 방지)
                for signal in signals:
                    if hasattr(signal.timestamp, 'date'):
                        signal_date = signal.timestamp.date()
                    else:
                        signal_date = pd.to_datetime(signal.timestamp, format='mixed', errors='coerce').date()
                    
                    # 신호 날짜가 현재 처리 날짜보다 미래가 아니고, 아직 처리되지 않은 신호만 처리
                    if signal_date <= date:
                        signal_key = f"{symbol}_{signal_date}_{signal.signal_type}_{signal.price}"
                        
                        # 중복 처리 방지
                        if not hasattr(self, '_processed_signals'):
                            self._processed_signals = set()
                        
                        if signal_key not in self._processed_signals:
                            # 신호 날짜의 시장 데이터 찾기
                            if signal_date == date:
                                market_data = day_data.iloc[-1]
                            else:
                                # 과거 신호의 경우 해당 날짜 데이터 찾기
                                if 'date' in df.columns:
                                    signal_day_data = df[df['date'].dt.date == signal_date] if hasattr(df['date'], 'dt') else df[df['date'] == signal_date]
                                else:
                                    signal_day_data = df[df.index.date == signal_date] if hasattr(df.index, 'date') else pd.DataFrame()
                                
                                if not signal_day_data.empty:
                                    market_data = signal_day_data.iloc[-1]
                                else:
                                    continue
                            
                            # 신호 처리 및 기록
                            self._execute_signal(signal, market_data)
                            self._processed_signals.add(signal_key)
                            
                            logger.debug(f"신호 처리: {signal_date} {signal.signal_type} {symbol} @ {signal.price:.0f}원")
                        
            except Exception as e:
                logger.warning(f"신호 처리 중 오류 ({symbol}, {date}): {e}")
    
def _execute_signal(self, signal, market_data: pd.Series):
        """매매 신호 실행"""
        symbol = signal.symbol
        current_price = market_data['close']
        
        if signal.signal_type == 'BUY':
            self._process_buy_signal(signal, current_price, market_data)
        elif signal.signal_type == 'SELL':
            self._process_sell_signal(signal, current_price, market_data)
    
def _process_buy_signal(self, signal, current_price: float, market_data: pd.Series):
        """매수 신호 처리"""
        symbol = signal.symbol
        
        # 이미 보유 중인지 확인
        if symbol in self.positions:
            return
        
        # 최대 포지션 수 확인
        if len(self.positions) >= self.config.max_positions:
            return
        
        # 포지션 크기 계산
        position_size = self._calculate_position_size(current_price, signal, market_data)
        
        if position_size <= 0:
            return
        
        # 거래 비용 계산
        trade_value = position_size * current_price
        commission = trade_value * self.config.commission_rate
        slippage = trade_value * self.config.slippage_rate
        total_cost = trade_value + commission + slippage
        
        # 자금 확인
        if total_cost > self.cash:
            # 자금 부족 시 가능한 최대 수량으로 조정
            available_value = self.cash * 0.95  # 5% 버퍼
            adjusted_trade_value = available_value / (1 + self.config.commission_rate + self.config.slippage_rate)
            position_size = adjusted_trade_value / current_price
            
            if position_size < 1:  # 최소 거래 단위
                return
        
        # 손절/익절 가격 계산
        stop_loss = current_price * (1 - self.config.risk_per_trade)
        take_profit = current_price * (1 + self.config.risk_per_trade * 2)  # 리워드:리스크 = 2:1
        
        # 포지션 생성
        position = Position(
            symbol=symbol,
            quantity=position_size,
            entry_price=current_price,
            entry_date=self.current_date,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_reason=signal.reason,
            position_type='LONG'
        )
        
        self.positions[symbol] = position
        self.cash -= total_cost
        
        logger.debug(f"매수 실행: {symbol} {position_size:.2f}주 @ {current_price:,.0f}원")
    
def _process_sell_signal(self, signal, current_price: float, market_data: pd.Series):
        """매도 신호 처리"""
        symbol = signal.symbol
        
        # 보유 포지션 확인
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        self._close_position(symbol, current_price, signal.reason)
    
def _close_position(self, symbol: str, exit_price: float, exit_reason: str):
        """포지션 청산"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # 거래 기록 생성
        trade_value = position.quantity * exit_price
        commission = trade_value * self.config.commission_rate
        slippage = trade_value * self.config.slippage_rate
        net_proceeds = trade_value - commission - slippage
        
        trade = Trade(
            entry_date=position.entry_date,
            exit_date=self.current_date,
            symbol=symbol,
            trade_type=position.position_type,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            entry_reason=position.entry_reason,
            exit_reason=exit_reason,
            commission=commission * 2,  # 매수/매도 수수료
            slippage=slippage * 2
        )
        
        self.trades.append(trade)
        self.cash += net_proceeds
        del self.positions[symbol]
        
        logger.debug(f"매도 실행: {symbol} {position.quantity:.2f}주 @ {exit_price:,.0f}원, 수익률: {trade.return_pct:.2%}")
    
def _calculate_position_size(self, price: float, signal, market_data: pd.Series) -> float:
        """포지션 크기 계산"""
        if self.config.position_size_method == 'fixed_amount':
            # 고정 금액 방식 (포트폴리오의 20%)
            target_value = self.config.initial_capital * 0.2
            return target_value / price
            
        elif self.config.position_size_method == 'percent':
            # 비례 방식 (현재 자산의 일정 비율)
            portfolio_value = self.get_portfolio_value()
            target_value = portfolio_value * 0.2
            return target_value / price
            
        elif self.config.position_size_method == 'volatility':
            # 변동성 기반 방식
            if 'ATR' in market_data:
                atr = market_data['ATR']
                risk_amount = self.get_portfolio_value() * self.config.risk_per_trade
                position_size = risk_amount / atr
                return min(position_size, self.cash * 0.2 / price)
        
        # 기본값
        return self.cash * 0.2 / price
    
def _update_positions(self, data: Dict[str, pd.DataFrame], date):
        """포지션 업데이트 (손절/익절 체크)"""
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            if symbol not in data:
                continue
            
            # 현재 가격 조회
            df = data[symbol]
            if 'date' in df.columns:
                day_data = df[df['date'].dt.date == date] if hasattr(df['date'], 'dt') else df[df['date'] == date]
            else:
                day_data = df[df.index.date == date] if hasattr(df.index, 'date') else pd.DataFrame()
            
            if day_data.empty:
                continue
            
            current_price = day_data.iloc[-1]['close']
            high_price = day_data.iloc[-1]['high']
            low_price = day_data.iloc[-1]['low']
            
            # 손절 체크
            if self.config.enable_stop_loss and low_price <= position.stop_loss:
                positions_to_close.append((symbol, position.stop_loss, "손절"))
            
            # 익절 체크
            elif self.config.enable_take_profit and high_price >= position.take_profit:
                positions_to_close.append((symbol, position.take_profit, "익절"))
        
        # 포지션 청산
        for symbol, exit_price, reason in positions_to_close:
            self._close_position(symbol, exit_price, reason)
    
def _close_all_positions(self, data: Dict[str, pd.DataFrame], final_date):
        """모든 포지션 청산 (백테스트 종료 시)"""
        for symbol in list(self.positions.keys()):
            if symbol in data:
                df = data[symbol]
                if 'date' in df.columns:
                    final_data = df[df['date'].dt.date == final_date] if hasattr(df['date'], 'dt') else df[df['date'] == final_date]
                else:
                    final_data = df[df.index.date == final_date] if hasattr(df.index, 'date') else df.iloc[[-1]]
                
                if not final_data.empty:
                    final_price = final_data.iloc[-1]['close']
                    self._close_position(symbol, final_price, "백테스트 종료")
    
def _record_equity(self):
        """자산 곡선 기록"""
        portfolio_value = self.get_portfolio_value()
        
        equity_record = {
            'date': self.current_date,
            'cash': self.cash,
            'positions_value': portfolio_value - self.cash,
            'total_value': portfolio_value,
            'open_positions': len(self.positions)
        }
        
        self.equity_curve.append(equity_record)
        
        # 일일 수익률 계산
        if len(self.equity_curve) > 1:
            prev_value = self.equity_curve[-2]['total_value']
            daily_return = (portfolio_value - prev_value) / prev_value
            self.daily_returns.append(daily_return)
    
def get_portfolio_value(self) -> float:
        """현재 포트폴리오 가치"""
        return self.cash + sum(pos.market_value for pos in self.positions.values())
    
def _analyze_results(self) -> Dict[str, Any]:
        """백테스팅 결과 분석"""
        if not self.trades:
            return self._empty_results()
        
        # 기본 통계
        returns = [trade.return_pct for trade in self.trades]
        profits = [trade.profit_loss for trade in self.trades]
        
        winning_trades = [r for r in returns if r > 0]
        losing_trades = [r for r in returns if r < 0]
        
        # 수익률 통계
        total_return = (self.get_portfolio_value() - self.config.initial_capital) / self.config.initial_capital
        
        # 최대 낙폭 계산
        equity_values = [record['total_value'] for record in self.equity_curve]
        if equity_values:
            peak = equity_values[0]
            max_drawdown = 0
            for value in equity_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
        else:
            max_drawdown = 0
        
        # 샤프 비율
        if self.daily_returns and np.std(self.daily_returns) > 0:
            sharpe_ratio = np.mean(self.daily_returns) / np.std(self.daily_returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        results = {
            # 기본 정보
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.trades) if self.trades else 0,
            
            # 수익률
            'total_return': total_return,
            'avg_return_per_trade': np.mean(returns) if returns else 0,
            'avg_winning_return': np.mean(winning_trades) if winning_trades else 0,
            'avg_losing_return': np.mean(losing_trades) if losing_trades else 0,
            
            # 리스크 지표
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'volatility': np.std(returns) if returns else 0,
            
            # 거래 통계
            'avg_holding_days': np.mean([trade.holding_days for trade in self.trades]),
            'max_holding_days': max([trade.holding_days for trade in self.trades]) if self.trades else 0,
            'total_commission': sum([trade.commission for trade in self.trades]),
            
            # 자산 곡선
            'equity_curve': pd.DataFrame(self.equity_curve),
            'daily_returns': pd.Series(self.daily_returns),
            'trades': pd.DataFrame([{
                'entry_date': t.entry_date,
                'exit_date': t.exit_date,
                'symbol': t.symbol,
                'return_pct': t.return_pct,
                'profit_loss': t.profit_loss,
                'holding_days': t.holding_days
            } for t in self.trades])
        }
        
        return results
    
def _empty_results(self) -> Dict[str, Any]:
        """거래가 없을 때의 빈 결과"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_return': 0,
            'avg_return_per_trade': 0,
            'avg_winning_return': 0,
            'avg_losing_return': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'volatility': 0,
            'avg_holding_days': 0,
            'max_holding_days': 0,
            'total_commission': 0,
            'equity_curve': pd.DataFrame(),
            'daily_returns': pd.Series(),
            'trades': pd.DataFrame()
        }

def run_quick_backtest(strategy, data: Dict[str, pd.DataFrame], 
                      initial_capital: float = 1000000,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    간단한 백테스팅 실행 함수
    
    Args:
        strategy: 매매 전략
        data: 종목별 데이터
        initial_capital: 초기 자본
        start_date: 백테스팅 시작날짜 (YYYY-MM-DD)
        end_date: 백테스팅 종료날짜 (YYYY-MM-DD)
        
    Returns:
        백테스팅 결과
    """
    config = BacktestConfig(initial_capital=initial_capital)
    engine = BacktestEngine(config)
    return engine.run_backtest(strategy, data, start_date, end_date)

if __name__ == "__main__":
    # 테스트 코드
    config = BacktestConfig()
    engine = BacktestEngine(config)
    print(f"백테스팅 엔진 생성: 초기자본 {config.initial_capital:,}원") 