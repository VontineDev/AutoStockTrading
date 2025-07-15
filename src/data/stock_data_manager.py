import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from src.data.database import DatabaseManager
from src.data.updater import StockDataUpdater
from src.data.indicators import TechnicalIndicators

from src.utils.constants import PROJECT_ROOT  # PROJECT_ROOT 임포트 추가


class StockDataManager:
    def __init__(self, db_path="stock_data.db", schema_path=None):
        # PROJECT_ROOT를 사용하여 스키마 파일 경로 설정
        default_schema_path = PROJECT_ROOT / "data" / "schema.sql"

        self.db = DatabaseManager(db_path)

        # schema_path가 제공되지 않으면 기본 스키마 경로 사용
        if schema_path is None:
            schema_path = default_schema_path

        if schema_path and os.path.exists(schema_path):
            self.db.initialize_schema(str(schema_path))  # Path 객체를 문자열로 변환
        self.updater = StockDataUpdater(db_path=self.db.db_path)
        self.indicator = TechnicalIndicators()

    def add_stock(self, stock_code, stock_name, market="KOSPI", sector=None):
        """종목 정보 추가"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO stocks (stock_code, stock_name, market, sector)
            VALUES (?, ?, ?, ?)
            """,
            (stock_code, stock_name, market, sector),
        )

    def add_stock_by_code(self, stock_code):
        """종목코드로 한국거래소에서 정보를 조회하여 자동 추가"""
        try:
            symbol_info = self.updater.get_symbol_info(stock_code)
            if symbol_info and symbol_info["name"]:
                stock_name = symbol_info["name"]
                market = symbol_info["market"]

                self.add_stock(stock_code, stock_name, market)
                return True, f"{stock_code} - {stock_name} ({market}) 추가 완료"
            else:
                return False, f"종목코드 {stock_code}를 찾을 수 없습니다."
        except Exception as e:
            return False, f"종목 정보 조회 실패: {e}"

    def collect_and_save_daily(self, stock_code, start_date, end_date, source="pykrx"):
        """StockDataUpdater를 사용하여 일별 OHLCV 데이터를 수집하고 저장"""
        # StockDataUpdater의 update_symbol 메서드를 사용하여 데이터 수집 및 저장
        # update_symbol은 내부적으로 데이터베이스에 저장하므로 별도의 저장 로직 불필요
        success = self.updater.update_symbol(
            symbol=stock_code,
            start_date=start_date,
            end_date=end_date,
            force_update=True,  # 강제 업데이트 (기존 데이터 덮어쓰기)
            source=source,
        )

        if success:
            # 데이터가 성공적으로 업데이트되었는지 확인하기 위해 다시 로드
            df = self.db.fetchdf(
                """
                SELECT * FROM stock_data WHERE symbol = ? AND date BETWEEN ? AND ? ORDER BY date
                """,
                (
                    stock_code,
                    start_date[:4] + "-" + start_date[4:6] + "-" + start_date[6:8],
                    end_date[:4] + "-" + end_date[4:6] + "-" + end_date[6:8],
                ),
            )
            if not df.empty:
                # 등락률 계산 (StockDataUpdater에서 처리하지 않는 경우)
                df["change_rate"] = (
                    (df["close"] - df["close"].shift(1)) / df["close"].shift(1) * 100
                )
                # 업데이트된 데이터로 DB에 다시 저장 (등락률 포함)
                with sqlite3.connect(self.db.db_path) as conn:
                    df.to_sql("stock_data", conn, if_exists="replace", index=False)
                return True
        return False

    def calculate_and_save_indicators(self, stock_code):
        """기술적 지표 계산 및 저장"""
        df = self.db.fetchdf(
            """
            SELECT symbol, date, open, high, low, close, volume FROM stock_data WHERE symbol = ? ORDER BY date
            """,
            (stock_code,),
        )
        if df.empty:
            return False
        # symbol 컬럼이 object 타입이 아닐 경우를 대비하여 명시적으로 변환
        df["symbol"] = df["symbol"].astype(str)

        # ROC 및 이동평균 계산
        roc_periods = [5, 7, 10, 12, 14, 20, 25, 30, 50, 100, 200]
        for period in roc_periods:
            df[f"roc_{period}"] = self.indicator.calculate_roc(df, period)
        for window in [5, 10, 20, 60]:
            df[f"ma_{window}"] = self.indicator.calculate_moving_average(df, window)
        # 이동평균 기울기
        df["ma_slope_5"] = df["ma_5"].diff(5) / 5
        df["ma_slope_10"] = df["ma_10"].diff(5) / 5
        df["ma_slope_20"] = df["ma_20"].diff(5) / 5

        # 필요한 컬럼들을 명시적으로 선택
        # 'symbol'과 'date'는 항상 포함
        selected_columns = ["symbol", "date"]

        # 계산된 지표 컬럼 추가
        for p in roc_periods:
            selected_columns.append(f"roc_{p}")
        selected_columns.extend(
            [
                "ma_5",
                "ma_10",
                "ma_20",
                "ma_60",
                "ma_slope_5",
                "ma_slope_10",
                "ma_slope_20",
            ]
        )

        # 실제 df에 존재하는 컬럼만 선택
        # df에 없는 컬럼은 selected_columns에서 제거
        final_selected_columns = [col for col in selected_columns if col in df.columns]
        df_indicators = df[
            final_selected_columns
        ].copy()  # .copy()를 사용하여 원본 DataFrame에 영향 주지 않음

        self.db.execute(
            "DELETE FROM technical_indicators WHERE symbol = ?", (stock_code,)
        )
        with sqlite3.connect(self.db.db_path) as conn:
            df_indicators.dropna().to_sql(
                "technical_indicators", conn, if_exists="append", index=False
            )
        return True

    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """특정 기간의 특정 종목 데이터를 데이터베이스에서 조회합니다."""
        query = """
        SELECT date, open, high, low, close, volume
        FROM stock_data 
        WHERE symbol = ? AND date BETWEEN ? AND ?
        ORDER BY date
        """
        df = self.db.fetchdf(query, params=(symbol, start_date, end_date))
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        return df

    def get_all_symbols(self) -> list:
        """데이터베이스에 저장된 모든 고유 종목 코드를 반환합니다."""
        query = "SELECT DISTINCT symbol FROM stock_data ORDER BY symbol"
        results = self.db.fetchall(query)
        return [row[0] for row in results]

    def get_available_symbols_for_backtest(self, min_data_days: int = 30) -> pd.DataFrame:
        """
        백테스팅에 사용 가능한 종목 목록을 데이터 수, 기간 등과 함께 반환합니다.
        Args:
            min_data_days (int): 백테스팅에 필요한 최소 데이터 일수
        Returns:
            pd.DataFrame: 사용 가능한 종목 정보
        """
        query = f"""
        SELECT 
            si.symbol, 
            si.name, 
            si.market,
            COUNT(sd.date) as data_count,
            MIN(sd.date) as earliest_date,
            MAX(sd.date) as latest_date
        FROM stock_info si
        JOIN stock_data sd ON si.symbol = sd.symbol
        GROUP BY si.symbol
        HAVING data_count >= ?
        ORDER BY data_count DESC
        """
        df = self.db.fetchdf(query, params=(min_data_days,))
        if not df.empty:
            df['display_name'] = df.apply(
                lambda row: f"{row['symbol']} ({row['name']}) - {row['data_count']}일",
                axis=1
            )
        return df

    def get_top_market_cap_symbols(self, top_n: int, market: str = 'KOSPI'):
        """시가총액 상위 N개 종목 코드를 반환합니다."""
        return self.updater.get_kospi_top_symbols(top_n) # 혹은 get_kosdaq_top_symbols

    def update_and_calculate_indicators(self, symbols: list, start_date: str, end_date: str, force_update: bool = False):
        """데이터 업데이트와 기술적 지표 계산을 함께 수행합니다."""
        logging.info("=== 데이터 업데이트 및 지표 계산 시작 ===")
        results = self.updater.update_multiple_symbols(symbols, start_date, end_date, force_update)
        
        success_count = sum(1 for success in results.values() if success)
        logging.info(f"데이터 업데이트 성공: {success_count}/{len(symbols)} 종목")

        indicator_success_count = 0
        for symbol, updated in results.items():
            if updated:
                try:
                    if self.calculate_and_save_indicators(symbol):
                        indicator_success_count += 1
                except Exception as e:
                    logging.error(f"{symbol} 지표 계산 실패: {e}")
        
        logging.info(f"기술적 지표 계산 성공: {indicator_success_count}/{success_count} 종목")
        return results


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
