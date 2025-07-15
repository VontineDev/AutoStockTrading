import os
import pandas as pd
from typing import Dict, Any, Optional
import yaml
import numpy as np
import plotly.graph_objects as go
from src.utils.dataframe_utils import standardize_dataframe
from src.data.updater import StockDataUpdater
from src.data.stock_data_manager import StockDataManager  # StockDataManager 추가 임포트
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import logging


def load_config() -> Dict[str, Any]:
    """
    환경설정 파일(config.yaml) 로드
    """
    config_path = os.path.join(os.path.dirname(__file__), "../../config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def load_stock_data(symbols: list, limit: int = 500) -> Dict[str, pd.DataFrame]:
    """
    종목별 주가 데이터 로드 (StockDataUpdater 사용)
    """
    updater = StockDataUpdater()
    dm = StockDataManager(db_path=updater.db_path)

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=limit + 30)).strftime(
        "%Y%m%d"
    )  # 여유 기간 추가

    # StockDataUpdater를 사용하여 데이터 업데이트 (필요시)
    # force_update=False로 설정하여 이미 최신 데이터가 있으면 건너뛰도록 함
    updater.update_multiple_symbols_parallel(
        symbols=symbols, start_date=start_date, end_date=end_date, force_update=False
    )

    data = {}
    for symbol in symbols:
        # StockDataManager를 사용하여 데이터베이스에서 데이터 로드
        df = dm.get_latest_data(symbol, days=limit)
        if not df.empty:
            data[symbol] = standardize_dataframe(df)
        else:
            data[symbol] = pd.DataFrame()
    return data


def calculate_ta_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    주요 기술적 지표(TA-Lib) 계산 (예시)
    """
    import talib

    if df.empty:
        return df
    close = df["종가"] if "종가" in df else df["close"]
    df["rsi"] = talib.RSI(close, timeperiod=14)
    df["macd"], df["macdsignal"], df["macdhist"] = talib.MACD(
        close, fastperiod=12, slowperiod=26, signalperiod=9
    )
    return df


def create_candlestick_chart(
    df: pd.DataFrame, symbol: str, indicators: Optional[list] = None
) -> Any:
    """
    캔들차트 + 보조지표 시각화 (Plotly)
    """
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name=symbol,
        )
    )
    if indicators:
        for ind in indicators:
            if ind in df.columns:
                fig.add_trace(go.Scatter(x=df.index, y=df[ind], name=ind))
    fig.update_layout(title=f"{symbol} 차트", xaxis_title="날짜", yaxis_title="가격")
    return fig


def load_csv(filepath: str, **kwargs) -> pd.DataFrame:
    """
    공통 CSV 로딩 함수 (표준화 적용)
    """
    df = pd.read_csv(filepath, **kwargs)
    df = standardize_dataframe(df)
    return df


def load_favorite_groups_from_db(db_path: str = "data/trading.db") -> dict:
    """
    DB에서 관심종목 그룹 및 종목을 불러온다.
    Returns: {group_name: [symbol, ...], ...}
    """
    groups = {}
    try:
        with sqlite3.connect(db_path) as conn:
            # 그룹명과 id 매핑
            group_rows = conn.execute("SELECT id, name FROM favorite_groups").fetchall()
            group_id_name = {gid: name for gid, name in group_rows}
            # 각 그룹별 종목(정렬)
            symbol_rows = conn.execute(
                "SELECT group_id, symbol FROM favorite_symbols ORDER BY group_id, position ASC, id ASC"
            ).fetchall()
            for gid, symbol in symbol_rows:
                group = group_id_name.get(gid)
                if group:
                    groups.setdefault(group, []).append(symbol)
    except Exception as e:
        logging.error(f"관심종목 그룹 불러오기 실패: {e}")
    return groups


def save_favorite_groups_to_db(groups: dict, db_path: str = "data/trading.db") -> bool:
    """
    관심종목 그룹 및 종목을 DB에 저장한다. (전체 삭제 후 재삽입)
    Args: groups: {group_name: [symbol, ...], ...}
    Returns: 성공 여부
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            # 기존 데이터 전체 삭제
            cur.execute("DELETE FROM favorite_symbols")
            cur.execute("DELETE FROM favorite_groups")
            # 그룹 및 종목 재삽입
            for group_name, symbols in groups.items():
                cur.execute(
                    "INSERT INTO favorite_groups (name) VALUES (?)", (group_name,)
                )
                group_id = cur.lastrowid
                for pos, symbol in enumerate(symbols):
                    cur.execute(
                        "INSERT INTO favorite_symbols (group_id, symbol, position) VALUES (?, ?, ?)",
                        (group_id, symbol, pos),
                    )
            conn.commit()
        return True
    except Exception as e:
        logging.error(f"관심종목 그룹 저장 실패: {e}")
        return False
