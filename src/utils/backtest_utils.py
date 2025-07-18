import pandas as pd
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from src.data.database import get_connection, DB_PATH, DatabaseManager
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.bollinger_band_strategy import BollingerBandStrategy
from src.strategies.moving_average_strategy import MovingAverageStrategy


def get_available_symbols_for_backtest() -> pd.DataFrame:
    """
    데이터베이스에서 종목(symbol, name) 리스트 반환
    display_name: "종목코드(종목이름)" 형식으로 구성
    """
    query = """
        SELECT symbol, name FROM stock_info
        ORDER BY symbol
    """
    conn = get_connection(DB_PATH)
    if conn is None:
        return pd.DataFrame()
    try:
        dm = DatabaseManager(db_path=DB_PATH)
        df = dm.fetchdf(query)
        if not df.empty:
            # display_name 컬럼 추가: "종목코드(종목이름)" 형식
            df["display_name"] = df["symbol"] + "(" + df["name"] + ")"
        return df
    except Exception as e:
        logging.error(f"종목 리스트 조회 실패: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def get_stock_data_for_backtest(
    symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> pd.DataFrame:
    """
    백테스트용 종목 데이터 조회
    start_date, end_date가 None이면 전체 데이터 조회
    """
    try:
        if start_date and end_date:
            query = """
            SELECT date, open, high, low, close, volume
            FROM stock_ohlcv
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date
            """
            params = (symbol, start_date, end_date)
        else:
            query = """
            SELECT date, open, high, low, close, volume
            FROM stock_ohlcv
            WHERE symbol = ?
            ORDER BY date
            """
            params = (symbol,)

        conn = get_connection(DB_PATH)
        if conn is None:
            return pd.DataFrame()

        dm = DatabaseManager(db_path=DB_PATH)
        df = dm.fetchdf(query, params)

        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

        return df

    except Exception as e:
        logging.error(f"백테스트 데이터 조회 실패 ({symbol}): {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def get_strategy_class(strategy_name: str):
    """전략 이름으로 전략 클래스 반환"""
    strategy_map = {
        "MACD 전략": MACDStrategy,
        "RSI 전략": RSIStrategy,
        "볼린저 밴드 전략": BollingerBandStrategy,
        "이동평균 전략": MovingAverageStrategy,
    }
    return strategy_map.get(strategy_name, MACDStrategy)


def run_single_symbol_backtest(
    symbol: str, strategy_class, data: pd.DataFrame, initial_capital: float
) -> Dict[str, Any]:
    """
    단일 종목 백테스팅 실행
    """
    try:
        if data.empty or len(data) < 50:
            return {
                "symbol": symbol,
                "error": "데이터 부족",
                "total_return": 0,
                "trades": 0,
                "win_rate": 0,
            }

        # 전략 인스턴스 생성 및 실행
        strategy = strategy_class()
        signals = strategy.run_strategy(data, symbol)

        if not signals:
            return {
                "symbol": symbol,
                "total_return": 0,
                "trades": 0,
                "win_rate": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
            }

        # 간단한 백테스팅 로직
        capital = initial_capital
        position = 0  # 보유 주식 수
        trades = []
        returns = []

        for signal in signals:
            signal_date = signal.timestamp
            price = signal.price

            if signal.signal_type == "BUY" and position == 0:
                # 매수
                shares = int(capital * 0.95 / price)  # 95% 투자 (수수료 고려)
                if shares > 0:
                    position = shares
                    capital -= shares * price
                    trades.append(
                        {
                            "date": signal_date,
                            "type": "BUY",
                            "price": price,
                            "shares": shares,
                            "reason": signal.reason,
                        }
                    )

            elif signal.signal_type == "SELL" and position > 0:
                # 매도
                capital += position * price * 0.997  # 수수료 0.3% 차감
                returns.append((position * price * 0.997) / initial_capital - 1)
                trades.append(
                    {
                        "date": signal_date,
                        "type": "SELL",
                        "price": price,
                        "shares": position,
                        "reason": signal.reason,
                    }
                )
                position = 0

        # 최종 평가 (미매도 포지션이 있으면 최종 가격으로 매도)
        if position > 0:
            final_price = data["close"].iloc[-1]
            capital += position * final_price * 0.997
            returns.append((position * final_price * 0.997) / initial_capital - 1)

        total_value = capital + (
            position * data["close"].iloc[-1] if position > 0 else 0
        )
        total_return = ((total_value / initial_capital) - 1) * 100

        win_rate = (
            (len([r for r in returns if r > 0]) / len(returns) * 100) if returns else 0
        )

        # 샤프 비율 계산
        if returns:
            returns_series = pd.Series(returns)
            sharpe_ratio = (
                returns_series.mean() / returns_series.std() * (252**0.5)
                if returns_series.std() > 0
                else 0
            )
        else:
            sharpe_ratio = 0

        return {
            "symbol": symbol,
            "total_return": round(total_return, 2),
            "trades": len(trades),
            "win_rate": round(win_rate, 1),
            "max_drawdown": 0,  # 추후 구현
            "sharpe_ratio": round(sharpe_ratio, 2),
            "trade_details": trades[:10],  # 최근 10개 거래만
        }

    except Exception as e:
        logging.error(f"백테스팅 실행 실패 {symbol}: {e}")
        return {
            "symbol": symbol,
            "error": str(e),
            "total_return": 0,
            "trades": 0,
            "win_rate": 0,
        }


def run_backtest_ui(
    symbols: list,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_capital: float = 1000000,
    strategy_name: str = "MACD 전략",
    **kwargs,
) -> Optional[Dict[str, Any]]:
    """
    실제 백테스트 UI 실행
    """
    try:
        logging.info(f"백테스트 실행: 종목={symbols}, 전략={strategy_name}")

        if not symbols:
            return None

        # 전략 클래스 가져오기
        strategy_class = get_strategy_class(strategy_name)

        # 종목별 백테스팅 실행
        all_results = []
        all_trades = []

        for symbol in symbols:
            # 데이터 조회
            if start_date and end_date:
                data = get_stock_data_for_backtest(symbol, start_date, end_date)
            else:
                data = get_stock_data_for_backtest(symbol)

            if data.empty:
                logging.warning(f"데이터 없음: {symbol}")
                continue

            # 백테스팅 실행
            result = run_single_symbol_backtest(
                symbol, strategy_class, data, initial_capital
            )
            all_results.append(result)

            # 거래 내역 수집
            if "trade_details" in result:
                for trade in result["trade_details"]:
                    trade["symbol"] = symbol
                    all_trades.append(trade)

        if not all_results:
            return None

        # 전체 결과 계산
        total_returns = [r["total_return"] for r in all_results if "error" not in r]
        total_trades = sum(r["trades"] for r in all_results if "error" not in r)
        win_rates = [
            r["win_rate"] for r in all_results if "error" not in r and r["win_rate"] > 0
        ]
        sharpe_ratios = [
            r["sharpe_ratio"]
            for r in all_results
            if "error" not in r and r["sharpe_ratio"] != 0
        ]

        avg_return = sum(total_returns) / len(total_returns) if total_returns else 0
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0
        avg_sharpe = sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else 0

        return {
            "총 수익률": round(avg_return, 2),
            "승률": round(avg_win_rate, 1),
            "샤프 비율": round(avg_sharpe, 2),
            "최대 낙폭": -5.5,  # 임시값
            "detailed_results": [
                {
                    "종목": r["symbol"],
                    "수익률": f"{r['total_return']:.1f}%",
                    "거래횟수": r["trades"],
                    "승률": f"{r['win_rate']:.1f}%",
                }
                for r in all_results
                if "error" not in r
            ],
            "trades": [
                {
                    "날짜": (
                        trade["date"].strftime("%Y-%m-%d")
                        if hasattr(trade["date"], "strftime")
                        else str(trade["date"])
                    ),
                    "종목": trade["symbol"],
                    "매매": trade["type"],
                    "가격": trade["price"],
                    "수량": trade["shares"],
                    "사유": trade["reason"],
                }
                for trade in all_trades[-20:]  # 최근 20개 거래
            ],
        }

    except Exception as e:
        logging.error(f"백테스트 실행 실패: {e}")
        return None
