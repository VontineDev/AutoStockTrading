import pandas as pd
from typing import Optional
from pykrx import stock
from datetime import datetime, timedelta

class StockCollector:
    def __init__(self):
        pass

    def collect_daily_ohlcv(self, stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        df = stock.get_market_ohlcv(start_date, end_date, stock_code)
        if df.empty:
            return None
        df.reset_index(inplace=True)
        df['stock_code'] = stock_code
        df['date'] = df['날짜'].dt.strftime('%Y-%m-%d')
        df_clean = df[['stock_code', 'date', '시가', '고가', '저가', '종가', '거래량']].copy()
        df_clean.columns = ['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume']
        return df_clean
    
    def get_stock_data(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """
        백테스팅용 주식 데이터 수집
        
        Args:
            symbol: 종목 코드
            days: 수집할 일수
            
        Returns:
            OHLCV 데이터 DataFrame
        """
        try:
            # 종료일: 오늘
            end_date = datetime.now()
            # 시작일: days 일 전 (주말/공휴일 고려하여 여유있게)
            start_date = end_date - timedelta(days=days + 30)
            
            # 날짜를 문자열로 변환
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            # 데이터 수집
            df = self.collect_daily_ohlcv(symbol, start_str, end_str)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 최근 days 개 데이터만 반환
            df = df.tail(days).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            print(f"데이터 수집 실패 ({symbol}): {e}")
            return pd.DataFrame() 