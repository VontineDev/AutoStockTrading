"""
데이터 로딩/샘플 생성 모듈
- load_sample_data 등
"""

from typing import List, Dict
import pandas as pd
from src.utils.common import load_stock_data
from datetime import datetime


def load_sample_data(
    symbols: List[str], start_date, end_date
) -> Dict[str, pd.DataFrame]:
    """
    DB에서 실제 주가 데이터를 불러온다 (load_stock_data 활용)
    """
    # 날짜 차이로 limit 계산
    if isinstance(start_date, str):
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_dt = start_date
    if isinstance(end_date, str):
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end_dt = end_date
    days = (end_dt - start_dt).days
    return load_stock_data(symbols, limit=days)
