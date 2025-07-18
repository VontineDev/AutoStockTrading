"""
데이터 서비스
UI와 데이터 계층 간의 중간 계층
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import os

from src.data.stock_data_manager import StockDataManager
from src.utils.constants import PROJECT_ROOT


class DataService:
    """데이터 관련 서비스"""
    
    def __init__(self):
        self.db_path = str(PROJECT_ROOT / "data" / "trading.db")
        self._data_manager = None
    
    @property
    def data_manager(self) -> StockDataManager:
        """지연 초기화된 데이터 매니저"""
        if self._data_manager is None:
            try:
                # 데이터베이스 파일 존재 확인
                if not os.path.exists(self.db_path):
                    logging.warning(f"데이터베이스 파일이 없습니다: {self.db_path}")
                    # 빈 데이터베이스 생성 시도
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                
                self._data_manager = StockDataManager(db_path=self.db_path)
                logging.info(f"데이터 매니저 초기화 완료: {self.db_path}")
            except Exception as e:
                logging.error(f"데이터 매니저 초기화 실패: {e}")
                raise
        return self._data_manager
    
    @st.cache_data
    def get_available_symbols(_self, min_data_days: int = 30) -> pd.DataFrame:
        """백테스팅 가능한 종목 목록 조회"""
        try:
            return _self.data_manager.get_available_symbols_for_backtest(min_data_days)
        except Exception as e:
            logging.error(f"종목 목록 조회 실패: {e}")
            return pd.DataFrame()
    
    @st.cache_data
    def get_stock_data(_self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """종목 데이터 조회"""
        try:
            return _self.data_manager.get_stock_data(symbol, start_date, end_date)
        except Exception as e:
            logging.error(f"종목 데이터 조회 실패 {symbol}: {e}")
            return pd.DataFrame()
    
    @st.cache_data
    def get_stock_data_with_indicators(_self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """기술적 지표가 포함된 종목 데이터 조회"""
        try:
            from src.data.indicators import TALibIndicators
            
            df = _self.get_stock_data(symbol, start_date, end_date)
            if df.empty:
                logging.warning(f"{symbol} 데이터가 비어있습니다.")
                return df

            # 컬럼명 강제 일치 (DB에서 불러온 데이터가 다를 수 있음)
            rename_map = {
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
                'OPEN': 'open', 'HIGH': 'high', 'LOW': 'low', 'CLOSE': 'close', 'VOLUME': 'volume',
                'open_price': 'open', 'high_price': 'high', 'low_price': 'low', 'close_price': 'close',
                'volume_amount': 'volume', 'amount': 'volume'
            }
            
            # 실제 존재하는 컬럼만 리네임
            existing_columns = df.columns.tolist()
            actual_rename = {k: v for k, v in rename_map.items() if k in existing_columns}
            if actual_rename:
                df.rename(columns=actual_rename, inplace=True)
            
            # 필수 컬럼 체크
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logging.error(f"{symbol} 필수 컬럼 누락: {missing_cols}. 실제 컬럼: {list(df.columns)}")
                return pd.DataFrame()

            # 최소 row 체크
            if len(df) < 50:
                logging.warning(f"{symbol} 데이터 row 부족: {len(df)}개 (최소 50개 필요)")

            # 기술적 지표 계산
            try:
                indicators = TALibIndicators(df)
                df_ind = indicators.calculate_all_indicators()
                
                # 지표 계산 후 DataFrame이 비어있으면 원본 반환
                if df_ind.empty:
                    logging.error(f"{symbol} 지표 계산 결과 DataFrame이 비어 있음. 원본 반환")
                    return df
                    
                return df_ind
            except Exception as indicator_error:
                logging.error(f"{symbol} 지표 계산 실패: {indicator_error}")
                return df  # 원본 데이터 반환
                
        except Exception as e:
            logging.error(f"지표 포함 데이터 조회 실패 {symbol}: {e}")
            return pd.DataFrame()
    
    @st.cache_data
    def get_market_cap_symbols(_self, top_n: int = 50, market: str = 'KOSPI') -> List[str]:
        """시가총액 상위 종목 조회"""
        try:
            return _self.data_manager.get_top_market_cap_symbols(top_n, market)
        except Exception as e:
            logging.error(f"시가총액 상위 종목 조회 실패: {e}")
            return []
    
    def update_stock_data(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, bool]:
        """종목 데이터 업데이트"""
        try:
            return self.data_manager.update_and_calculate_indicators(symbols, start_date, end_date)
        except Exception as e:
            logging.error(f"데이터 업데이트 실패: {e}")
            return {symbol: False for symbol in symbols}
    
    @st.cache_data
    def get_data_summary(_self) -> pd.DataFrame:
        """데이터 현황 요약"""
        try:
            return _self.data_manager.get_data_summary()
        except Exception as e:
            logging.error(f"데이터 현황 조회 실패: {e}")
            return pd.DataFrame()
    
    def get_latest_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """최근 N일 데이터 조회"""
        try:
            return self.data_manager.get_latest_data(symbol, days)
        except Exception as e:
            logging.error(f"최근 데이터 조회 실패 {symbol}: {e}")
            return pd.DataFrame()
    
    def add_stock_by_code(self, stock_code: str) -> Tuple[bool, str]:
        """종목코드로 종목 추가"""
        try:
            return self.data_manager.add_stock_by_code(stock_code)
        except Exception as e:
            logging.error(f"종목 추가 실패 {stock_code}: {e}")
            return False, f"종목 추가 실패: {e}"


# 싱글톤 인스턴스
_data_service_instance = None

def get_data_service() -> DataService:
    """데이터 서비스 싱글톤 인스턴스 반환"""
    global _data_service_instance
    if _data_service_instance is None:
        _data_service_instance = DataService()
    return _data_service_instance 