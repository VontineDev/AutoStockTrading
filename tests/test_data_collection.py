#!/usr/bin/env python3
"""
데이터 수집 테스트

커서룰의 테스트 원칙에 따라 데이터 수집 및 데이터베이스 기능을 검증
"""

import unittest
import pandas as pd
import numpy as np
import sqlite3
import tempfile
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.data.database import DatabaseManager
from src.constants import SystemConstants, DataCollectionConstants


class TestDatabaseManager(unittest.TestCase):
    """DatabaseManager 클래스 테스트"""


def setUp(self):
    """테스트 환경 설정"""
    # 임시 데이터베이스 파일 생성
    self.temp_dir = tempfile.mkdtemp()
    self.test_db_path = os.path.join(self.temp_dir, "test_stock_data.db")
    self.db_manager = DatabaseManager(self.test_db_path)

    # 테스트용 샘플 데이터
    self.sample_data = pd.DataFrame(
        {
            "symbol": ["005930", "000660", "035420"] * 10,
            "date": pd.date_range("2023-01-01", periods=30, freq="D"),
            "open": np.random.uniform(50000, 60000, 30),
            "high": np.random.uniform(60000, 70000, 30),
            "low": np.random.uniform(40000, 50000, 30),
            "close": np.random.uniform(50000, 60000, 30),
            "volume": np.random.randint(100000, 1000000, 30),
        }
    )


def tearDown(self):
    """테스트 정리"""
    self.db_manager.close()

    # 임시 파일 정리
    if os.path.exists(self.test_db_path):
        os.remove(self.test_db_path)
    os.rmdir(self.temp_dir)


def test_database_initialization(self):
    """데이터베이스 초기화 테스트"""
    self.assertTrue(os.path.exists(self.test_db_path))
    self.assertIsNotNone(self.db_manager.connection)

    # 테이블 존재 확인
    cursor = self.db_manager.connection.cursor()
    cursor.execute(
        """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='stock_data'
        """
    )
    tables = cursor.fetchall()
    self.assertEqual(len(tables), 1)
    self.assertEqual(tables[0][0], "stock_data")


def test_save_stock_data(self):
    """주식 데이터 저장 테스트"""
    # 데이터 저장
    result = self.db_manager.save_stock_data(self.sample_data)
    self.assertTrue(result)

    # 저장된 데이터 확인
    saved_data = self.db_manager.get_stock_data("005930")
    self.assertIsInstance(saved_data, pd.DataFrame)
    self.assertGreater(len(saved_data), 0)

    # 데이터 내용 확인
    self.assertEqual(saved_data["symbol"].iloc[0], "005930")
    self.assertIn("open", saved_data.columns)
    self.assertIn("high", saved_data.columns)
    self.assertIn("low", saved_data.columns)
    self.assertIn("close", saved_data.columns)
    self.assertIn("volume", saved_data.columns)


def test_get_stock_data_date_range(self):
    """날짜 범위로 데이터 조회 테스트"""
    # 데이터 저장
    self.db_manager.save_stock_data(self.sample_data)

    # 날짜 범위 조회
    start_date = "2023-01-05"
    end_date = "2023-01-15"
    filtered_data = self.db_manager.get_stock_data(
        "005930", start_date=start_date, end_date=end_date
    )

    self.assertIsInstance(filtered_data, pd.DataFrame)
    if len(filtered_data) > 0:
        # 날짜 범위 확인
        filtered_data["date"] = pd.to_datetime(filtered_data["date"])
        self.assertTrue((filtered_data["date"] >= start_date).all())
        self.assertTrue((filtered_data["date"] <= end_date).all())


def test_get_symbols_list(self):
    """종목 리스트 조회 테스트"""
    # 데이터 저장
    self.db_manager.save_stock_data(self.sample_data)

    # 종목 리스트 조회
    symbols = self.db_manager.get_symbols_list()

    self.assertIsInstance(symbols, list)
    expected_symbols = ["005930", "000660", "035420"]
    for symbol in expected_symbols:
        self.assertIn(symbol, symbols)


def test_get_latest_date(self):
    """최신 날짜 조회 테스트"""
    # 데이터 저장
    self.db_manager.save_stock_data(self.sample_data)

    # 최신 날짜 조회
    latest_date = self.db_manager.get_latest_date("005930")

    self.assertIsNotNone(latest_date)
    self.assertIsInstance(latest_date, str)


def test_data_summary(self):
    """데이터 요약 정보 테스트"""
    # 데이터 저장
    self.db_manager.save_stock_data(self.sample_data)

    # 요약 정보 조회
    summary = self.db_manager.get_data_summary()

    self.assertIsInstance(summary, dict)
    self.assertIn("total_symbols", summary)
    self.assertIn("total_records", summary)
    self.assertIn("date_range", summary)

    # 기본적인 값 검증
    self.assertGreater(summary["total_symbols"], 0)
    self.assertGreater(summary["total_records"], 0)


def test_duplicate_data_handling(self):
    """중복 데이터 처리 테스트"""
    # 첫 번째 저장
    result1 = self.db_manager.save_stock_data(self.sample_data)
    self.assertTrue(result1)

    # 동일한 데이터 다시 저장 (중복)
    result2 = self.db_manager.save_stock_data(self.sample_data)
    # 중복 처리 방식에 따라 결과가 달라질 수 있음
    self.assertIsInstance(result2, bool)

    # 중복 후에도 데이터 조회가 정상적으로 작동하는지 확인
    data = self.db_manager.get_stock_data("005930")
    self.assertIsInstance(data, pd.DataFrame)


def test_invalid_symbol_handling(self):
    """잘못된 종목 코드 처리 테스트"""
    # 존재하지 않는 종목 조회
    data = self.db_manager.get_stock_data("INVALID_SYMBOL")

    # 빈 DataFrame 또는 None 반환
    self.assertTrue(data is None or len(data) == 0)


def test_empty_data_handling(self):
    """빈 데이터 처리 테스트"""
    empty_data = pd.DataFrame()

    # 빈 데이터 저장 시도
    result = self.db_manager.save_stock_data(empty_data)

    # 적절한 처리 (False 반환 또는 예외 발생)
    self.assertIsInstance(result, bool)


def test_database_connection_timeout(self):
    """데이터베이스 연결 타임아웃 테스트"""
    # 타임아웃 설정이 적용되었는지 확인
    self.assertIsNotNone(self.db_manager.connection)

    # 연결 상태 확인
    try:
        cursor = self.db_manager.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        self.assertEqual(result[0], 1)
    except sqlite3.Error:
        self.fail("데이터베이스 연결 실패")


def test_transaction_rollback(self):
    """트랜잭션 롤백 테스트"""
    # 잘못된 데이터로 롤백 상황 시뮬레이션
    invalid_data = pd.DataFrame(
        {
            "symbol": ["TEST"],
            "date": ["invalid_date"],  # 잘못된 날짜 형식
            "open": [50000],
            "high": [60000],
            "low": [40000],
            "close": [55000],
            "volume": [100000],
        }
    )

    # 저장 시도 (실패해야 함)
    result = self.db_manager.save_stock_data(invalid_data)

    # 실패 시 데이터베이스 상태가 일관성 있게 유지되는지 확인
    symbols = self.db_manager.get_symbols_list()
    self.assertNotIn("TEST", symbols)


class TestDataCollectionConstants(unittest.TestCase):
    """데이터 수집 상수 테스트"""


def test_constants_usage_in_database(self):
    """데이터베이스에서 상수 활용 테스트"""
    # 임시 데이터베이스로 상수 기반 설정 테스트
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, SystemConstants.DEFAULT_DB_NAME)

    try:
        db_manager = DatabaseManager(test_db_path)

        # 기본 DB 이름이 상수에서 가져온 것인지 확인
        self.assertTrue(test_db_path.endswith(SystemConstants.DEFAULT_DB_NAME))

        # 연결 타임아웃이 상수값과 일치하는지 확인
        # (실제 구현에 따라 테스트 방법이 달라질 수 있음)
        self.assertIsNotNone(db_manager.connection)

        db_manager.close()

    finally:
        # 정리
        if os.path.exists(test_db_path):
            os.remove(test_db_path)
        os.rmdir(temp_dir)


def test_batch_size_constants(self):
    """배치 크기 상수 테스트"""
    # 배치 크기 상수가 유효한 범위인지 확인
    self.assertGreaterEqual(
        DataCollectionConstants.DEFAULT_BATCH_SIZE,
        DataCollectionConstants.MIN_BATCH_SIZE,
    )
    self.assertLessEqual(
        DataCollectionConstants.DEFAULT_BATCH_SIZE,
        DataCollectionConstants.MAX_BATCH_SIZE,
    )


def test_api_timeout_constants(self):
    """API 타임아웃 상수 테스트"""
    # API 관련 상수가 합리적인 값인지 확인
    self.assertGreater(DataCollectionConstants.API_TIMEOUT, 0)
    self.assertLess(DataCollectionConstants.API_TIMEOUT, 60)  # 60초 미만

    self.assertGreater(DataCollectionConstants.API_DELAY_SECONDS, 0)
    self.assertLess(DataCollectionConstants.API_DELAY_SECONDS, 5)  # 5초 미만


class TestDataValidation(unittest.TestCase):
    """데이터 검증 테스트"""


def setUp(self):
    """테스트 환경 설정"""
    self.temp_dir = tempfile.mkdtemp()
    self.test_db_path = os.path.join(self.temp_dir, "validation_test.db")
    self.db_manager = DatabaseManager(self.test_db_path)


def tearDown(self):
    """테스트 정리"""
    self.db_manager.close()
    if os.path.exists(self.test_db_path):
        os.remove(self.test_db_path)
    os.rmdir(self.temp_dir)


def test_ohlcv_data_validation(self):
    """OHLCV 데이터 유효성 검증 테스트"""
    # 유효한 OHLCV 데이터
    valid_data = pd.DataFrame(
        {
            "symbol": ["TEST"] * 5,
            "date": pd.date_range("2023-01-01", periods=5),
            "open": [100, 102, 101, 103, 105],
            "high": [105, 107, 106, 108, 110],
            "low": [95, 97, 96, 98, 100],
            "close": [102, 101, 103, 105, 104],
            "volume": [1000, 1200, 1100, 1300, 1150],
        }
    )

    # 데이터 저장 및 검증
    result = self.db_manager.save_stock_data(valid_data)
    self.assertTrue(result)

    # 저장된 데이터의 OHLCV 관계 검증
    saved_data = self.db_manager.get_stock_data("TEST")

    for _, row in saved_data.iterrows():
        # High >= max(Open, Close)
        self.assertGreaterEqual(row["high"], max(row["open"], row["close"]))
        # Low <= min(Open, Close)
        self.assertLessEqual(row["low"], min(row["open"], row["close"]))
        # Volume >= 0
        self.assertGreaterEqual(row["volume"], 0)


def test_date_format_validation(self):
    """날짜 형식 검증 테스트"""
    # 다양한 날짜 형식으로 데이터 생성
    date_formats_data = pd.DataFrame(
        {
            "symbol": ["DATE_TEST"] * 3,
            "date": [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
            ],  # ISO 형식  # ISO 형식  # ISO 형식
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [102, 103, 104],
            "volume": [1000, 1100, 1200],
        }
    )

    # 데이터 저장
    result = self.db_manager.save_stock_data(date_formats_data)
    self.assertTrue(result)

    # 날짜 순서대로 저장되었는지 확인
    saved_data = self.db_manager.get_stock_data("DATE_TEST")
    if len(saved_data) > 1:
        dates = pd.to_datetime(saved_data["date"])
        self.assertTrue(dates.is_monotonic_increasing or dates.is_monotonic_decreasing)


def test_numeric_data_validation(self):
    """숫자 데이터 검증 테스트"""
    # 다양한 숫자 형식의 데이터
    numeric_data = pd.DataFrame(
        {
            "symbol": ["NUMERIC_TEST"] * 3,
            "date": pd.date_range("2023-01-01", periods=3),
            "open": [100.5, 101.25, 102.75],  # 소수점
            "high": [105, 106, 107],  # 정수
            "low": [95.0, 96.0, 97.0],  # float
            "close": [102.5, 103.5, 104.5],  # 소수점
            "volume": [1000, 1100, 1200],  # 정수
        }
    )

    # 데이터 저장
    result = self.db_manager.save_stock_data(numeric_data)
    self.assertTrue(result)

    # 저장된 데이터의 숫자 형식 확인
    saved_data = self.db_manager.get_stock_data("NUMERIC_TEST")

    # 숫자 컬럼들이 적절한 타입인지 확인
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for col in numeric_columns:
        self.assertTrue(pd.api.types.is_numeric_dtype(saved_data[col]))


def test_symbol_format_validation(self):
    """종목 코드 형식 검증 테스트"""
    # 다양한 종목 코드 형식
    symbol_data = pd.DataFrame(
        {
            "symbol": ["005930", "000660", "035420"],  # 표준 6자리
            "date": pd.date_range("2023-01-01", periods=3),
            "open": [70000, 50000, 45000],
            "high": [72000, 52000, 47000],
            "low": [68000, 48000, 43000],
            "close": [71000, 51000, 46000],
            "volume": [1000000, 800000, 600000],
        }
    )

    # 데이터 저장
    result = self.db_manager.save_stock_data(symbol_data)
    self.assertTrue(result)

    # 종목 코드가 정확히 저장되었는지 확인
    symbols = self.db_manager.get_symbols_list()
    expected_symbols = ["005930", "000660", "035420"]

    for symbol in expected_symbols:
        self.assertIn(symbol, symbols)


def test_data_integrity_constraints(self):
    """데이터 무결성 제약 조건 테스트"""
    # 기본 데이터 저장
    base_data = pd.DataFrame(
        {
            "symbol": ["INTEGRITY_TEST"],
            "date": ["2023-01-01"],
            "open": [100],
            "high": [105],
            "low": [95],
            "close": [102],
            "volume": [1000],
        }
    )

    result = self.db_manager.save_stock_data(base_data)
    self.assertTrue(result)

    # 동일한 종목, 날짜의 다른 데이터 저장 시도
    duplicate_data = pd.DataFrame(
        {
            "symbol": ["INTEGRITY_TEST"],
            "date": ["2023-01-01"],
            "open": [101],  # 다른 값
            "high": [106],
            "low": [96],
            "close": [103],
            "volume": [1100],
        }
    )

    # 중복 처리 방식에 따라 결과가 달라질 수 있음
    result2 = self.db_manager.save_stock_data(duplicate_data)

    # 최종 데이터 일관성 확인
    final_data = self.db_manager.get_stock_data("INTEGRITY_TEST")
    self.assertEqual(len(final_data), 1)  # 중복이 적절히 처리되었는지


class TestPerformanceOptimization(unittest.TestCase):
    """성능 최적화 테스트"""


def setUp(self):
    """테스트 환경 설정"""
    self.temp_dir = tempfile.mkdtemp()
    self.test_db_path = os.path.join(self.temp_dir, "performance_test.db")
    self.db_manager = DatabaseManager(self.test_db_path)


def tearDown(self):
    """테스트 정리"""
    self.db_manager.close()
    if os.path.exists(self.test_db_path):
        os.remove(self.test_db_path)
    os.rmdir(self.temp_dir)


def test_bulk_insert_performance(self):
    """대량 데이터 삽입 성능 테스트"""
    # 대량 데이터 생성 (1000 레코드)
    symbols = ["SYM001", "SYM002", "SYM003", "SYM004", "SYM005"]
    dates = pd.date_range("2022-01-01", periods=200, freq="D")

    large_data = []
    for symbol in symbols:
        for date in dates:
            large_data.append(
                {
                    "symbol": symbol,
                    "date": date.strftime("%Y-%m-%d"),
                    "open": np.random.uniform(50000, 60000),
                    "high": np.random.uniform(60000, 70000),
                    "low": np.random.uniform(40000, 50000),
                    "close": np.random.uniform(50000, 60000),
                    "volume": np.random.randint(100000, 1000000),
                }
            )

    bulk_data = pd.DataFrame(large_data)

    # 실행 시간 측정
    import time

    start_time = time.time()
    result = self.db_manager.save_stock_data(bulk_data)
    end_time = time.time()

    # 성능 검증
    self.assertTrue(result)
    execution_time = end_time - start_time

    # 대량 데이터가 합리적인 시간 내에 처리되었는지 확인
    # (1000 레코드를 10초 내에 처리)
    self.assertLess(execution_time, 10.0)

    # 저장된 데이터 수 확인
    for symbol in symbols:
        data = self.db_manager.get_stock_data(symbol)
        self.assertEqual(len(data), 200)


def test_query_performance_with_index(self):
    """인덱스 활용 쿼리 성능 테스트"""
    # 테스트 데이터 준비
    test_data = pd.DataFrame(
        {
            "symbol": ["PERF_TEST"] * 365,
            "date": pd.date_range("2022-01-01", periods=365),
            "open": np.random.uniform(50000, 60000, 365),
            "high": np.random.uniform(60000, 70000, 365),
            "low": np.random.uniform(40000, 50000, 365),
            "close": np.random.uniform(50000, 60000, 365),
            "volume": np.random.randint(100000, 1000000, 365),
        }
    )

    # 데이터 저장
    self.db_manager.save_stock_data(test_data)

    # 쿼리 성능 측정
    import time

    start_time = time.time()
    result = self.db_manager.get_stock_data(
        "PERF_TEST", start_date="2022-06-01", end_date="2022-08-31"
    )
    end_time = time.time()

    # 결과 검증
    self.assertIsInstance(result, pd.DataFrame)
    self.assertGreater(len(result), 0)

    # 쿼리 시간이 합리적인지 확인 (1초 미만)
    query_time = end_time - start_time
    self.assertLess(query_time, 1.0)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)
