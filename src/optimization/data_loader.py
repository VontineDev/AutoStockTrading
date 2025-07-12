"""
데이터 로딩/샘플 생성 모듈
- load_sample_data 등
"""
from typing import List, Dict
import pandas as pd

def load_sample_data(symbols: List[str], start_date, end_date) -> Dict[str, pd.DataFrame]:
    """
    샘플 데이터 로드 (더미)
    실제 구현에서는 DB 또는 API에서 데이터 로드
    """
    return {} 