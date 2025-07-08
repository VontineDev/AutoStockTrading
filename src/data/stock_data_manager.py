import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pykrx import stock
import logging
import os
from src.data.database import DatabaseManager
from src.data.collector import StockCollector
from src.data.indicators import TechnicalIndicators

class StockDataManager:
    def __init__(self, db_path="stock_data.db", schema_path=None):
        self.db = DatabaseManager(db_path)
        if schema_path and os.path.exists(schema_path):
            self.db.initialize_schema(schema_path)
        self.collector = StockCollector()
        self.indicator = TechnicalIndicators()
        
    def add_stock(self, stock_code, stock_name, market="KOSPI", sector=None):
        """종목 정보 추가"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO stocks (stock_code, stock_name, market, sector)
            VALUES (?, ?, ?, ?)
            """, (stock_code, stock_name, market, sector)
        )
        
    def add_stock_by_code(self, stock_code):
        """종목코드로 한국거래소에서 정보를 조회하여 자동 추가"""
        try:
            stock_name = stock.get_market_ticker_name(stock_code)
            if stock_name:
                # 시장 구분 자동 판단
                market = "KOSPI"
                if stock_code in stock.get_market_ticker_list(market="KOSDAQ"):
                    market = "KOSDAQ"
                elif stock_code in stock.get_market_ticker_list(market="KONEX"):
                    market = "KONEX"
                
                self.add_stock(stock_code, stock_name, market)
                return True, f"{stock_code} - {stock_name} ({market}) 추가 완료"
            else:
                return False, f"종목코드 {stock_code}를 찾을 수 없습니다."
        except Exception as e:
            return False, f"종목 정보 조회 실패: {e}"
        
    def collect_and_save_daily(self, stock_code, start_date, end_date):
        df = self.collector.collect_daily_ohlcv(stock_code, start_date, end_date)
        if df is not None:
            # 등락률 계산
            df['change_rate'] = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1) * 100)
            
            # 기존 데이터 삭제 (중복 방지)
            self.db.execute(
                "DELETE FROM daily_ohlcv WHERE stock_code = ? AND date BETWEEN ? AND ?",
                (stock_code, start_date[:4] + '-' + start_date[4:6] + '-' + start_date[6:8], 
                 end_date[:4] + '-' + end_date[4:6] + '-' + end_date[6:8])
            )
            
            with sqlite3.connect(self.db.db_path) as conn:
                df.to_sql('daily_ohlcv', conn, if_exists='append', index=False)
            return True
        return False

    def calculate_and_save_indicators(self, stock_code):
        """기술적 지표 계산 및 저장"""
        df = self.db.fetchdf(
            """
            SELECT * FROM daily_ohlcv WHERE stock_code = ? ORDER BY date
            """, (stock_code,)
        )
        if df.empty:
            return False
        # ROC 및 이동평균 계산
        roc_periods = [5, 7, 10, 12, 14, 20, 25, 30, 50, 100, 200]
        for period in roc_periods:
            df[f'roc_{period}'] = self.indicator.calculate_roc(df, period)
        for window in [5, 10, 20, 60]:
            df[f'ma_{window}'] = self.indicator.calculate_moving_average(df, window)
        # 이동평균 기울기
        df['ma_slope_5'] = df['ma_5'].diff(5) / 5
        df['ma_slope_10'] = df['ma_10'].diff(5) / 5
        df['ma_slope_20'] = df['ma_20'].diff(5) / 5
        indicator_columns = ['stock_code', 'date'] + [f'roc_{p}' for p in roc_periods] + [
                             'ma_5', 'ma_10', 'ma_20', 'ma_60',
                             'ma_slope_5', 'ma_slope_10', 'ma_slope_20']
        df_indicators = df[indicator_columns].dropna()
        self.db.execute("DELETE FROM technical_indicators WHERE stock_code = ?", (stock_code,))
        with sqlite3.connect(self.db.db_path) as conn:
            df_indicators.to_sql('technical_indicators', conn, if_exists='append', index=False)
        return True

    def get_latest_data(self, stock_code, days=30):
        """최근 N일 데이터 조회"""
        return self.db.fetchdf(
            """
            SELECT d.*, t.roc_14, t.ma_20, t.ma_slope_20
            FROM daily_ohlcv d
            LEFT JOIN technical_indicators t ON d.stock_code = t.stock_code AND d.date = t.date
            WHERE d.stock_code = ?
            ORDER BY d.date DESC
            LIMIT ?
            """, (stock_code, days)
        )
        
    def get_data_summary(self):
        """데이터 현황 요약"""
        return self.db.fetchdf(
            """
            SELECT 
                s.stock_code,
                s.stock_name,
                COUNT(d.date) as total_days,
                MIN(d.date) as start_date,
                MAX(d.date) as end_date
            FROM stocks s
            LEFT JOIN daily_ohlcv d ON s.stock_code = d.stock_code
            GROUP BY s.stock_code, s.stock_name
            """
        )

# 사용 예시
if __name__ == "__main__":
    # 데이터 관리자 초기화
    dm = StockDataManager("stock_data.db")
    
    # 삼성전자 정보 추가
    dm.add_stock("005930", "삼성전자", "KOSPI", "반도체")
    
    # 1년치 데이터 수집
    start_date = "20230101"
    end_date = "20231231"
    dm.collect_and_save_daily("005930", start_date, end_date)
    
    # 지표 계산
    dm.calculate_and_save_indicators("005930")
    
    # 최근 30일 데이터 조회
    recent_data = dm.get_latest_data("005930", 30)
    print(recent_data.head())
    
    # 데이터 현황 확인
    summary = dm.get_data_summary()
    print(summary)