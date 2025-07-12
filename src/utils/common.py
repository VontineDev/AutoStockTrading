import os
import pandas as pd
from typing import Dict, Any, Optional
import yaml
import numpy as np
import plotly.graph_objects as go
from src.utils.dataframe_utils import standardize_dataframe
from scripts.data_update import StockDataUpdater
from src.data.stock_data_manager import StockDataManager # StockDataManager 추가 임포트
from datetime import datetime, timedelta

def load_config() -> Dict[str, Any]:
    """
    환경설정 파일(config.yaml) 로드
    """
    config_path = os.path.join(os.path.dirname(__file__), '../../config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def load_stock_data(symbols: list, limit: int = 500) -> Dict[str, pd.DataFrame]:
    """
    종목별 주가 데이터 로드 (StockDataUpdater 사용)
    """
    updater = StockDataUpdater()
    dm = StockDataManager(db_path=updater.db_path)

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=limit + 30)).strftime('%Y%m%d') # 여유 기간 추가

    # StockDataUpdater를 사용하여 데이터 업데이트 (필요시)
    # force_update=False로 설정하여 이미 최신 데이터가 있으면 건너뛰도록 함
    updater.update_multiple_symbols_parallel(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        force_update=False
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
    close = df['종가'] if '종가' in df else df['close']
    df['rsi'] = talib.RSI(close, timeperiod=14)
    df['macd'], df['macdsignal'], df['macdhist'] = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    return df

def create_candlestick_chart(df: pd.DataFrame, symbol: str, indicators: Optional[list] = None) -> Any:
    """
    캔들차트 + 보조지표 시각화 (Plotly)
    """
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name=symbol
    ))
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