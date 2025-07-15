 # -*- coding: utf-8 -*-
import sys
import os
import sqlite3
import pandas as pd
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import time

print(sys.stdout.encoding)

# pykrx 관련 import
try:
    from pykrx import stock
except ImportError:
    print("pykrx가 설치되지 않았습니다. 'pip install pykrx'로 설치해주세요.")
    sys.exit(1)

# 프로젝트 루트 디렉토리를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 로깅 설정
sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            PROJECT_ROOT / "logs" / "data_update.log", encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class StockDataUpdater:
    """주식 데이터 업데이트 클래스"""

    def __init__(self, db_path: str = None, config_path: str = None):
        """
        Args:
            db_path: SQLite 데이터베이스 경로
            config_path: 설정 파일 경로
        """
        self.db_path = db_path or str(PROJECT_ROOT / "data" / "trading.db")
        self.config_path = config_path or str(PROJECT_ROOT / "config.yaml")

        # 설정 로드
        self.config = self._load_config()

        # 데이터베이스 초기화
        self._init_database()

        logger.info(f"데이터 업데이터 초기화 완료: DB={self.db_path}")

    def _load_config(self) -> Dict:
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"설정 파일 로드 실패: {e}")

        # 기본 설정 반환
        return {
            "data_collection": {
                "api_delay": 1,
                "max_retries": 3,
                "default_symbols": ["005930", "000660", "035420"],
                "market_indices": ["KOSPI", "KOSDAQ"],
                "update_schedule": "daily",
            }
        }

    def _init_database(self):
        """데이터베이스 및 테이블 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # 종목 정보 테이블
            conn.execute(
                """
                    CREATE TABLE IF NOT EXISTS api_usage (
                        date TEXT PRIMARY KEY,
                        call_count INTEGER
                    )
                """
            )
            conn.commit()
            logger.info("데이터베이스 테이블 초기화 완료")

        # API 사용량 초기화
        self.api_calls_today = self._load_api_calls_today()
        self.api_call_limit = 5000  # 예시: 일일 API 호출 제한

    def _load_api_calls_today(self) -> int:
        """오늘의 API 호출 횟수를 로드하거나 0으로 초기화"""
        today_str = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT call_count FROM api_usage WHERE date = ?", (today_str,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                conn.execute("INSERT OR REPLACE INTO api_usage (date, call_count) VALUES (?, ?)", (today_str, 0))
                conn.commit()
                return 0

    def _increment_api_call(self):
        """API 호출 횟수 증가 및 DB에 반영"""
        self.api_calls_today += 1
        today_str = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE api_usage SET call_count = ? WHERE date = ?", (self.api_calls_today, today_str))
            conn.commit()

    def save_symbol_info(self, symbol_info: Dict):
        """종목 정보 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                        INSERT OR REPLACE INTO stock_info 
                        (symbol, name, market, sector, industry, listing_date, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        symbol_info["symbol"],
                        symbol_info["name"],
                        symbol_info["market"],
                        symbol_info["sector"],
                        symbol_info["industry"],
                        symbol_info["listing_date"],
                        datetime.now(),
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"종목 정보 저장 실패: {e}")

    def update_all_symbol_info_with_krx(
        self,
        kospi_csv: str = "krx_sector_kospi.csv",
        kosdaq_csv: str = "krx_sector_kosdaq.csv",
    ):
        """pykrx 종목정보와 KOSPI+KOSDAQ 업종분류 csv를 병합하여 stock_info를 갱신"""
        logger.info("pykrx 종목 정보 및 업종 분류 업데이트 시작...")
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 마지막 업데이트 날짜 확인
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT MAX(updated_at) FROM stock_info")
            last_updated_at = cursor.fetchone()[0]

        if last_updated_at and last_updated_at.startswith(today_str):
            logger.info(f"종목 정보가 이미 오늘({today_str}) 업데이트되었습니다. 업데이트를 건너뜁니다.")
            return

        logger.info(f"종목 정보 업데이트를 시작합니다. (마지막 업데이트: {last_updated_at or '없음'})")
        today = datetime.now().strftime("%Y%m%d")
        self._increment_api_call() # get_market_ticker_list 호출
        symbols = stock.get_market_ticker_list(today, market="ALL")
        self._increment_api_call() # get_market_ticker_list 호출
        kospi_symbols = set(stock.get_market_ticker_list(today, market="KOSPI"))
        pykrx_data = []
        total = len(symbols)
        for i, symbol in enumerate(symbols, 1):
            self._increment_api_call() # get_market_ticker_name 호출
            name = stock.get_market_ticker_name(symbol)
            market = "KOSPI" if symbol in kospi_symbols else "KOSDAQ"
            pykrx_data.append({"symbol": symbol, "name": name, "market": market})
            if i % 100 == 0 or i % max(1, total // 20) == 0 or i == total:
                percent = (i / total) * 100
                logger.info(
                    f"  - pykrx 종목정보 수집 진행도: {i}/{total} ({percent:.1f}%) 완료"
                )
        df_pykrx = pd.DataFrame(pykrx_data)

        # KOSPI/KOSDAQ 업종분류 csv 모두 필요
        # PROJECT_ROOT를 사용하여 절대 경로 지정
        kospi_csv_path = PROJECT_ROOT / kospi_csv
        kosdaq_csv_path = PROJECT_ROOT / kosdaq_csv

        if not os.path.exists(kospi_csv_path) or not os.path.exists(kosdaq_csv_path):
            logger.error(
                f"업종분류 csv 파일이 없습니다. 프로젝트 루트에 '{kospi_csv}', '{kosdaq_csv}' 두 파일을 모두 넣어주세요. (필수 컬럼: 종목코드, 업종명)"
            )
            return

        # 인코딩 자동 감지 함수
        def read_csv_auto_encoding(path):
            try:
                return pd.read_csv(path, dtype={"종목코드": str}, encoding="cp949")
            except UnicodeDecodeError:
                return pd.read_csv(path, dtype={"종목코드": str}, encoding="utf-8")

        df_kospi = read_csv_auto_encoding(kospi_csv_path)
        df_kosdaq = read_csv_auto_encoding(kosdaq_csv_path)

        for df, fname in zip([df_kospi, df_kosdaq], [kospi_csv, kosdaq_csv]):
            if "업종명" not in df.columns or "종목코드" not in df.columns:
                logger.error(
                    f"csv 파일에 '종목코드' 또는 '업종명' 컬럼이 없습니다: {fname}"
                )
                return
            df["종목코드"] = df["종목코드"].str.zfill(6)

        # 두 파일 병합
        df_krx = pd.concat([df_kospi, df_kosdaq], ignore_index=True)
        logger.info(f"csv 업종분류 데이터 사용: {kospi_csv}, {kosdaq_csv}")

        # 병합: symbol <-> 종목코드
        df_merged = pd.merge(
            df_pykrx,
            df_krx[["종목코드", "업종명"]],
            left_on="symbol",
            right_on="종목코드",
            how="left",
        )

        # DB에 저장 (진행도 표시)
        total = len(df_merged)
        with sqlite3.connect(self.db_path) as conn:
            for i, (_, row) in enumerate(df_merged.iterrows(), 1):
                conn.execute(
                    """
                        INSERT OR REPLACE INTO stock_info (symbol, name, market, sector, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        row["symbol"],
                        row["name"],
                        row["market"],
                        row["업종명"] if pd.notnull(row["업종명"]) else "",
                        datetime.now(),
                    ),
                )
                if i % 100 == 0 or i % max(1, total // 20) == 0 or i == total:
                    percent = (i / total) * 100
                    logger.info(
                        f"  - DB 저장 진행도: {i}/{total} ({percent:.1f}%) 완료"
                    )
        logger.info(f"병합된 종목 수: {total}")
        logger.info("[2] DB에 저장된 stock_info 샘플:")
        with sqlite3.connect(self.db_path) as conn:
            sample = pd.read_sql_query("SELECT * FROM stock_info LIMIT 10", conn)
            logger.info(f"\n{sample}")
        return df_merged

    def get_all_tickers(self) -> List[str]:
        """데이터베이스에서 모든 종목 티커를 가져옵니다. (구현 필요)"""
        # TODO: 실제 DB에서 모든 티커를 가져오는 로직 구현
        logger.warning("get_all_tickers: 실제 구현이 필요합니다. 현재는 빈 리스트를 반환합니다.")
        return []

    def get_kospi_top_symbols(self, limit: int) -> List[str]:
        """KOSPI 상위 N개 종목 티커를 가져옵니다. (구현 필요)"""
        # TODO: 실제 DB 또는 pykrx에서 KOSPI 상위 종목을 가져오는 로직 구현
        logger.warning("get_kospi_top_symbols: 실제 구현이 필요합니다. 현재는 빈 리스트를 반환합니다.")
        return []

    def get_api_usage_status(self) -> Dict:
        """API 사용량 현황을 반환합니다."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        return {
            "pykrx_calls_today": self.api_calls_today,
            "daily_limit": self.api_call_limit,
            "remaining_calls": max(0, self.api_call_limit - self.api_calls_today),
            "last_checked_date": today_str
        }

    def update_daily_market_data(self, date_str: str):
        """
        어제의 시장 전체 데이터를 업데이트합니다.
        가장 빠른 방법: stock.get_market_ohlcv(date, market="ALL")
        """
        logger.info(f"일별 시장 데이터 업데이트 시작: {date_str}")
        try:
            self._increment_api_call() # get_market_ohlcv 호출
            df = stock.get_market_ohlcv(date_str, market="ALL")
            logger.info(f"일별 시장 데이터 ({date_str}) 수집 완료. 샘플:\n{df.head()}")
            # TODO: 수집된 일별 시장 데이터를 데이터베이스에 저장하는 로직 추가
            # 예: conn.execute("INSERT OR REPLACE INTO daily_ohlcv ...")
        except Exception as e:
            logger.error(f"일별 시장 데이터 ({date_str}) 업데이트 실패: {e}")

    def update_specific_stock_data(self, ticker: str, start_date_str: str, end_date_str: str):
        """
        특정 종목의 기간 데이터를 업데이트합니다.
        가장 빠른 방법: stock.get_market_ohlcv(start_date, end_date, ticker)
        """
        logger.info(f"특정 종목 ({ticker}) 기간 데이터 업데이트 시작: {start_date_str} ~ {end_date_str})")
        try:
            self._increment_api_call() # get_market_ohlcv 호출
            df = stock.get_market_ohlcv(start_date_str, end_date_str, ticker)
            logger.info(f"종목 ({ticker}) 기간 데이터 수집 완료. 샘플:\n{df.head()}")
            # TODO: 수집된 특정 종목 기간 데이터를 데이터베이스에 저장하는 로직 추가
            # 예: conn.execute("INSERT OR REPLACE INTO stock_ohlcv ...")
        except Exception as e:
            logger.error(f"특정 종목 ({ticker}) 기간 데이터 업데이트 실패: {e}")

    def update_all_historical_data(self, start_date_str: str, end_date_str: str):
        """
        전체 종목의 기간 데이터를 업데이트합니다.
        가장 빠른 방법: 모든 티커를 순회하며 stock.get_market_ohlcv(start_date, end_date, ticker) 호출
        """
        logger.info(f"전체 종목 기간 데이터 업데이트 시작: {start_date_str} ~ {end_date_str}")
        today = datetime.now().strftime("%Y%m%d")
        self._increment_api_call() # get_market_ticker_list 호출
        all_tickers = stock.get_market_ticker_list(today, market="ALL")
        total_tickers = len(all_tickers)
        for i, ticker in enumerate(all_tickers, 1):
            try:
                self._increment_api_call() # get_market_ohlcv 호출
                df = stock.get_market_ohlcv(start_date_str, end_date_str, ticker)
                logger.info(f"  - ({i}/{total_tickers}) 종목 ({ticker}) 기간 데이터 수집 완료. 샘플:\n{df.head()}")
                # TODO: 수집된 전체 종목 기간 데이터를 데이터베이스에 저장하는 로직 추가
                # 예: conn.execute("INSERT OR REPLACE INTO stock_ohlcv ...")
                time.sleep(self.config["data_collection"]["api_delay"]) # 서버 부하 방지를 위한 지연
            except Exception as e:
                logger.error(f"  - ({i}/{total_tickers}) 종목 ({ticker}) 기간 데이터 업데이트 실패: {e}")
        logger.info("전체 종목 기간 데이터 업데이트 완료.")


def main():
    updater = StockDataUpdater()

    # 시나리오 1: 어제의 시장 전체 데이터 업데이트
    # 어제 날짜를 계산 (실제 사용 시에는 휴장일 등을 고려해야 함)
    # from datetime import timedelta
    # yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    # updater.update_daily_market_data(yesterday)

    # 시나리오 2: 특정 종목의 기간 데이터 업데이트 (예: 삼성전자, 2023년 전체)
    # updater.update_specific_stock_data("005930", "20230101", "20231231")

    # 시나리오 3: 전체 종목의 기간 데이터 업데이트 (주의: 매우 오래 걸릴 수 있음)
    # updater.update_all_historical_data("20220101", "20221231")

    # 기존 종목 정보 업데이트 (필요시)
    updater.update_all_symbol_info_with_krx(
        kospi_csv=str(PROJECT_ROOT / "krx_sector_kospi.csv"),
        kosdaq_csv=str(PROJECT_ROOT / "krx_sector_kosdaq.csv")
    )


if __name__ == "__main__":
    main()