import pandas as pd
from typing import Any

def check_date_column_or_index(df: pd.DataFrame, verbose: bool = True) -> bool:
    """
    데이터프레임에 날짜 정보가 컬럼 또는 인덱스로 존재하는지 확인
    Args:
        df: 입력 데이터프레임
        verbose: True면 진단 정보 출력
    Returns:
        날짜 정보가 있으면 True, 없으면 False
    """
    date_candidates = ['date', '일자', '날짜', 'datetime', 'dt']
    has_date_col = any(col.lower() in date_candidates for col in df.columns)
    is_index_date = pd.api.types.is_datetime64_any_dtype(df.index)
    is_index_named_date = df.index.name and df.index.name.lower() in date_candidates

    if verbose:
        print("컬럼명:", df.columns.tolist())
        print("인덱스:", df.index)
        print("인덱스 타입:", type(df.index))
        print("인덱스 이름:", df.index.name)
        print("날짜 컬럼 있음:", has_date_col)
        print("인덱스가 날짜 타입:", is_index_date)
        print("인덱스 이름이 날짜 후보:", is_index_named_date)
        if not (has_date_col or is_index_date or is_index_named_date):
            print("⚠️ 날짜 정보가 없습니다! 데이터 소스를 확인하세요.")

    return has_date_col or is_index_date or is_index_named_date

def standardize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    컬럼명 표준화 및 날짜 컬럼 보장
    - 컬럼명 소문자화/공백제거
    - 한글/영문/약어 등 다양한 변형을 표준명으로 통일
    - 날짜 컬럼이 없고 인덱스가 날짜라면 'date' 컬럼으로 복사
    Returns:
        표준화된 데이터프레임
    """
    df = df.copy()
    df.columns = [col.strip().lower() for col in df.columns]
    rename_map = {}
    for col in df.columns:
        if col in ['종가', 'close', 'close_price', 'c'] and col != 'close':
            rename_map[col] = 'close'
        if col in ['거래량', 'volume', 'vol', 'v'] and col != 'volume':
            rename_map[col] = 'volume'
        if col in ['시가', 'open', 'o'] and col != 'open':
            rename_map[col] = 'open'
        if col in ['고가', 'high', 'h'] and col != 'high':
            rename_map[col] = 'high'
        if col in ['저가', 'low', 'l'] and col != 'low':
            rename_map[col] = 'low'
        if col in ['일자', '날짜', 'datetime', 'dt'] and col != 'date':
            rename_map[col] = 'date'
    df = df.rename(columns=rename_map)
    # 날짜 컬럼이 없고, 인덱스가 날짜라면 컬럼으로 추가
    if 'date' not in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df.index) or (df.index.name and df.index.name.lower() in ['date', '일자', '날짜', 'datetime', 'dt']):
            df['date'] = df.index
    return df 