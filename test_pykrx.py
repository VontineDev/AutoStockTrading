import pandas as pd
from pykrx import stock
from datetime import datetime


def test_pykrx_columns():
    today = datetime.now().strftime("%Y%m%d")

    print("--- Testing get_market_ohlcv_by_ticker ---")
    try:
        ohlcv_df = stock.get_market_ohlcv_by_ticker(today, market="KOSPI")
        print(f"get_market_ohlcv_by_ticker columns: {ohlcv_df.columns.tolist()}")
        print(f"get_market_ohlcv_by_ticker head:\n{ohlcv_df.head()}")
    except Exception as e:
        print(f"Error with get_market_ohlcv_by_ticker: {e}")

    print("\n--- Testing get_market_cap_by_ticker ---")
    try:
        cap_df = stock.get_market_cap_by_ticker(today, market="KOSPI")
        print(f"get_market_cap_by_ticker columns: {cap_df.columns.tolist()}")
        print(f"get_market_cap_by_ticker head:\n{cap_df.head()}")
    except Exception as e:
        print(f"Error with get_market_cap_by_ticker: {e}")


if __name__ == "__main__":
    test_pykrx_columns()
