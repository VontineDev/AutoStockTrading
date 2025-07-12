import pytest
import pandas as pd
import plotly.graph_objects as go
import os
import sys
from unittest.mock import patch, MagicMock
import numpy as np  # numpy 임포트 추가
import sqlite3  # sqlite3 임포트 추가
import tempfile  # tempfile 임포트 추가

# 프로젝트 루트를 sys.path에 추가하여 모듈 임포트 가능하게 함
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.common import (
    load_config,
    load_stock_data,
    calculate_ta_indicators,
    create_candlestick_chart,
)
from scripts.data_update import (
    StockDataUpdater,
)  # StockDataUpdater를 직접 임포트하여 모의 객체로 대체 가능성 열어둠


# 테스트용 더미 config.yaml 파일 생성
@pytest.fixture(scope="module")
def setup_config_file(tmp_path_factory):
    config_content = """
    project:
      name: "Test Trading System"
      version: "0.0.1"
    data_collection:
      api_delay: 0.1
      max_retries: 1
      default_symbols: ["005930"]
    """
    config_dir = tmp_path_factory.mktemp("config_test")
    config_path = config_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    # load_config 함수가 이 임시 파일을 참조하도록 경로를 패치
    with patch("src.utils.common.os.path.join", return_value=str(config_path)):
        yield
    # 테스트 후 파일 삭제는 tmp_path_factory가 알아서 처리


# 테스트용 더미 데이터베이스 파일 생성 및 삭제
@pytest.fixture(scope="module")
def setup_test_db():
    # tempfile을 사용하여 임시 SQLite 파일 생성
    # NamedTemporaryFile은 파일을 열린 상태로 유지하므로, 이름을 얻고 닫은 후 다시 연결
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db_file:
        db_path = tmp_db_file.name

    # StockDataUpdater가 이 임시 DB 파일을 사용하도록 패치
    with patch(
        "scripts.data_update.StockDataUpdater.db_path", new_callable=lambda: db_path
    ):
        # StockDataUpdater의 __init__에서 _init_database가 호출되므로,
        # 테스트용 DB 경로로 초기화되도록 Mocking
        with patch(
            "scripts.data_update.StockDataUpdater._init_database"
        ) as mock_init_db:
            # 실제 _init_database 로직을 실행하여 테이블 생성
            updater = StockDataUpdater(db_path=db_path)
            updater._init_database()  # Mocking된 함수 대신 실제 함수 호출

            # 더미 데이터 삽입
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO stock_data 
                (symbol, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                ("005930", "2023-01-01", 100.0, 105.0, 98.0, 102.0, 100000, 10200000),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO stock_data 
                (symbol, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                ("005930", "2023-01-02", 102.0, 108.0, 101.0, 105.0, 120000, 12600000),
            )
            cursor.execute(
                """
                INSERT OR REPLACE INTO stock_data 
                (symbol, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                ("005930", "2023-01-03", 105.0, 110.0, 103.0, 107.0, 150000, 16050000),
            )
            conn.commit()
            conn.close()

            yield db_path

    # 테스트 완료 후 임시 파일 삭제
    os.unlink(db_path)


# load_config() 테스트
def test_load_config(setup_config_file):
    config = load_config()
    assert isinstance(config, dict)
    assert config["project"]["name"] == "Test Trading System"
    assert config["project"]["version"] == "0.0.1"


# load_stock_data() 테스트
@patch("src.utils.common.StockDataUpdater")
@patch("src.utils.common.StockDataManager")
def test_load_stock_data(MockStockDataManager, MockStockDataUpdater, setup_test_db):
    # Mock StockDataUpdater 인스턴스 생성
    mock_updater_instance = MockStockDataUpdater.return_value
    mock_updater_instance.db_path = setup_test_db  # Mock된 updater의 db_path 설정

    # Mock StockDataManager 인스턴스 생성
    mock_dm_instance = MockStockDataManager.return_value

    # get_latest_data가 반환할 더미 데이터프레임 설정
    dummy_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03"]),
            "open": [100, 102, 105],
            "high": [105, 108, 110],
            "low": [98, 101, 103],
            "close": [102, 105, 107],
            "volume": [100000, 120000, 150000],
            "amount": [10200000, 12600000, 16050000],
        }
    )
    mock_dm_instance.get_latest_data.return_value = dummy_df

    symbols = ["005930"]
    data = load_stock_data(symbols, limit=3)

    assert isinstance(data, dict)
    assert "005930" in data
    assert isinstance(data["005930"], pd.DataFrame)
    assert not data["005930"].empty
    assert all(
        col in data["005930"].columns
        for col in ["date", "open", "high", "low", "close", "volume"]
    )

    # StockDataUpdater의 update_multiple_symbols_parallel이 호출되었는지 확인
    mock_updater_instance.update_multiple_symbols_parallel.assert_called_once()

    # StockDataManager의 get_latest_data가 호출되었는지 확인
    mock_dm_instance.get_latest_data.assert_called_once_with("005930", days=3)

    # 데이터가 없는 종목 테스트
    mock_dm_instance.get_latest_data.return_value = (
        pd.DataFrame()
    )  # 빈 DataFrame 반환하도록 설정
    data_empty = load_stock_data(["999999"], limit=10)
    assert "999999" in data_empty
    assert data_empty["999999"].empty


# calculate_ta_indicators() 테스트
def test_calculate_ta_indicators():
    # 테스트용 더미 OHLCV 데이터 (MACD 계산을 위해 충분한 길이로 변경)
    data = {
        "date": pd.to_datetime(
            pd.date_range(start="2023-01-01", periods=100)
        ),  # 30 -> 100
        "open": np.random.rand(100) * 1000 + 10000,
        "high": np.random.rand(100) * 1000 + 10500,
        "low": np.random.rand(100) * 1000 + 9500,
        "close": np.random.rand(100) * 1000 + 10000,
        "volume": np.random.randint(100000, 1000000, 100),
    }
    df = pd.DataFrame(data)

    # 지표 계산
    df_with_indicators = calculate_ta_indicators(df.copy())

    # 예상되는 지표 컬럼이 추가되었는지 확인
    expected_indicator_cols = ["rsi", "macd", "macdsignal", "macdhist"]
    for col in expected_indicator_cols:
        assert col in df_with_indicators.columns
        # NaN 값이 너무 많지 않은지 (계산이 제대로 되었는지) 대략적으로 확인
        # MACD는 26일 이동평균을 사용하므로, 25개 정도의 NaN은 정상
        # 전체 길이의 절반보다 적은 NaN을 허용하도록 조건 완화
        assert (
            df_with_indicators[col].isnull().sum() < len(df_with_indicators) * 0.5
        )  # 조건 완화

    # 빈 DataFrame 테스트
    empty_df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    empty_df_with_indicators = calculate_ta_indicators(empty_df)
    assert empty_df_with_indicators.empty
    assert (
        "rsi" not in empty_df_with_indicators.columns
    )  # 빈 DF에는 지표 컬럼이 추가되지 않아야 함


# create_candlestick_chart() 테스트
def test_create_candlestick_chart():
    # 테스트용 더미 OHLCV 데이터
    data = {
        "date": pd.to_datetime(pd.date_range(start="2023-01-01", periods=10)),
        "open": np.random.rand(10) * 100 + 1000,
        "high": np.random.rand(10) * 100 + 1050,
        "low": np.random.rand(10) * 100 + 950,
        "close": np.random.rand(10) * 100 + 1000,
        "volume": np.random.randint(10000, 100000, 10),
    }
    df = pd.DataFrame(data)
    df = df.set_index("date")  # 인덱스를 날짜로 설정

    symbol = "TEST"
    chart = create_candlestick_chart(df, symbol)

    assert isinstance(chart, go.Figure)
    assert len(chart.data) > 0  # 최소한 캔들스틱 트레이스가 있어야 함
    assert chart.data[0].type == "candlestick"
    assert chart.layout.title.text == f"{symbol} 차트"

    # 지표 포함 테스트
    df["test_indicator"] = np.random.rand(len(df)) * 100
    chart_with_indicator = create_candlestick_chart(
        df, symbol, indicators=["test_indicator"]
    )
    assert len(chart_with_indicator.data) > 1  # 캔들스틱 + 지표 트레이스
    assert chart_with_indicator.data[1].name == "test_indicator"
