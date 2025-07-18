"""
주식 종목 필터링 유틸리티 (DatabaseManager 기반)

SQLite 데이터베이스의 저장된 데이터를 활용하여 시가총액, 거래량, 변동률 등 다양한 조건으로 종목을 필터링
DatabaseManager를 사용하여 표준화된 데이터베이스 접근 방식 적용
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple, Any
import logging
from functools import lru_cache
import time
from pathlib import Path
from .database import DatabaseManager

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "trading.db"

logger = logging.getLogger(__name__)


class StockFilter:
    """주식 종목 필터링 클래스 (DatabaseManager 기반)"""

    def __init__(self, cache_duration: int = 300, db_path: Optional[str] = None):
        """
        초기화

        Args:
            cache_duration: 캐시 유지 시간(초) - 기본 5분
            db_path: 데이터베이스 경로 (None시 기본 경로 사용)
        """
        self.cache_duration = cache_duration
        self.cache: Dict[str, Dict] = {}
        self.db_path = db_path or str(DB_PATH)
        self.db_manager = DatabaseManager(self.db_path)

    def _get_cache_key(self, market: str, date: str, filter_type: str) -> str:
        """캐시 키 생성"""
        return f"{market}_{date}_{filter_type}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache[cache_key].get('timestamp', 0)
        return (time.time() - cache_time) < self.cache_duration

    def _get_latest_trading_date(self) -> str:
        """최근 거래일 조회 (DatabaseManager 기반)"""
        try:
            result = self.db_manager.fetchall("SELECT MAX(date) FROM stock_ohlcv")
            
            if result and result[0] and result[0][0]:
                # YYYY-MM-DD → YYYYMMDD 변환
                return result[0][0].replace('-', '')
            else:
                # DB에 데이터가 없으면 오늘 날짜
                return datetime.now().strftime('%Y%m%d')
                    
        except Exception as e:
            logger.warning(f"최근 거래일 조회 실패: {e}")
            return datetime.now().strftime('%Y%m%d')

    def _date_db_format(self, date_str: str) -> str:
        """YYYYMMDD → YYYY-MM-DD 변환"""
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    def _date_api_format(self, date_str: str) -> str:
        """YYYY-MM-DD → YYYYMMDD 변환"""
        return date_str.replace('-', '')

    def get_market_cap_top(
        self,
        top_n: int = 30,
        market: str = "KOSPI",
        date: Optional[str] = None,
        min_cap: Optional[float] = None,
    ) -> List[str]:
        """
        시가총액 상위 종목 조회 (DatabaseManager 기반)

        Args:
            top_n: 상위 N개 종목
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')
            date: 기준일 (YYYYMMDD, None시 최근 거래일)
            min_cap: 최소 시가총액 (억원)

        Returns:
            종목 코드 리스트
        """
        if date is None:
            date = self._get_latest_trading_date()
            
        cache_key = self._get_cache_key(market, date, f"market_cap_{top_n}_{min_cap}")
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            # 시장 조건 구성
            where_conditions = ["market_cap IS NOT NULL"]
            params: List[Union[str, int]] = []
            
            if market != "ALL":
                where_conditions.append("market = ?")
                params.append(market)
            
            # 최소 시가총액 조건 추가
            if min_cap is not None:
                min_cap_won = int(min_cap * 100_000_000)  # 억원을 원으로 변환
                where_conditions.append("market_cap >= ?")
                params.append(min_cap_won)
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
            SELECT symbol, market_cap 
            FROM stock_info 
            WHERE {where_clause}
            ORDER BY market_cap DESC 
            LIMIT ?
            """
            params.append(top_n)
            
            df = self.db_manager.fetchdf(query, tuple(params))
            result = df['symbol'].tolist() if not df.empty else []
            
            # 캐시 저장
            self.cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            return result
                
        except Exception as e:
            logger.error(f"시가총액 상위 종목 조회 실패: {e}")
            return []

    def get_volume_top(
        self,
        top_n: int = 30,
        market: str = "KOSPI",
        date: Optional[str] = None,
        days_avg: int = 5,
        min_volume: Optional[int] = None,
    ) -> List[str]:
        """
        거래량 상위 종목 조회 (DatabaseManager 기반)

        Args:
            top_n: 상위 N개 종목
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')
            date: 기준일 (YYYYMMDD, None시 최근 거래일)
            days_avg: 평균 거래량 계산 기간 (일)
            min_volume: 최소 거래량 (주)

        Returns:
            종목 코드 리스트
        """
        if date is None:
            date = self._get_latest_trading_date()
            
        cache_key = self._get_cache_key(market, date, f"volume_{top_n}_{days_avg}_{min_volume}")
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            db_date = self._date_db_format(date)
            
            # 평균 거래량 계산 기간 설정
            if days_avg == 1:
                # 단일 날짜 거래량
                volume_query = """
                SELECT so.symbol, so.volume
                FROM stock_ohlcv so
                JOIN stock_info si ON so.symbol = si.symbol
                WHERE so.date = ?
                """
                params = [db_date]
            else:
                # 평균 거래량 계산
                end_date_obj = datetime.strptime(date, '%Y%m%d')
                start_date_obj = end_date_obj - timedelta(days=days_avg-1)
                start_db_date = start_date_obj.strftime('%Y-%m-%d')
                
                volume_query = """
                SELECT so.symbol, AVG(so.volume) as volume
                FROM stock_ohlcv so
                JOIN stock_info si ON so.symbol = si.symbol
                WHERE so.date BETWEEN ? AND ?
                GROUP BY so.symbol
                HAVING COUNT(*) >= ?
                """
                params = [start_db_date, db_date, max(1, days_avg // 2)]
            
            # 시장 조건 추가
            if market != "ALL":
                volume_query += " AND si.market = ?"
                params.append(market)
            
            # 최소 거래량 조건 추가
            if min_volume is not None:
                volume_query += " AND volume >= ?"
                params.append(min_volume)
            
            volume_query += " ORDER BY volume DESC LIMIT ?"
            params.append(top_n)
            
            df = self.db_manager.fetchdf(volume_query, tuple(params))
            result = df['symbol'].tolist() if not df.empty else []
            
            # 캐시 저장
            self.cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            return result
                
        except Exception as e:
            logger.error(f"거래량 상위 종목 조회 실패: {e}")
            return []

    def get_price_change_top(
        self,
        top_n: int = 30,
        market: str = "KOSPI",
        date: Optional[str] = None,
        change_type: str = "rise",
        min_change: Optional[float] = None,
    ) -> List[str]:
        """
        등락률 상위 종목 조회 (DatabaseManager 기반)

        Args:
            top_n: 상위 N개 종목
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')
            date: 기준일 (YYYYMMDD, None시 최근 거래일)
            change_type: 등락 구분 ('rise': 상승, 'fall': 하락, 'abs': 절대값)
            min_change: 최소 등락률 (%)

        Returns:
            종목 코드 리스트
        """
        if date is None:
            date = self._get_latest_trading_date()
            
        cache_key = self._get_cache_key(market, date, f"change_{change_type}_{top_n}_{min_change}")
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        
        try:
            db_date = self._date_db_format(date)
            
            # 전일 날짜 계산
            date_obj = datetime.strptime(date, '%Y%m%d')
            prev_date_obj = date_obj - timedelta(days=1)
            prev_db_date = prev_date_obj.strftime('%Y-%m-%d')
            
            # 등락률 계산 쿼리
            change_query = """
            SELECT 
                today.symbol,
                today.close as current_close,
                prev.close as prev_close,
                ((today.close - prev.close) * 100.0 / prev.close) as change_rate
            FROM stock_ohlcv today
            JOIN stock_ohlcv prev ON today.symbol = prev.symbol
            JOIN stock_info si ON today.symbol = si.symbol
            WHERE today.date = ?
            AND prev.date = ?
            """
            params = [db_date, prev_db_date]
            
            # 시장 조건 추가
            if market != "ALL":
                change_query += " AND si.market = ?"
                params.append(market)
            
            df = self.db_manager.fetchdf(change_query, tuple(params))
            
            if df.empty:
                return []
            
            # 등락 타입별 필터링
            if change_type == "rise":
                filtered = df[df['change_rate'] > 0].copy()
                sort_ascending = False
            elif change_type == "fall":
                filtered = df[df['change_rate'] < 0].copy()
                sort_ascending = True
            else:  # abs
                filtered = df.copy()
                filtered['change_rate'] = np.abs(filtered['change_rate'])
                sort_ascending = False
            
            # 최소 등락률 필터링
            if min_change is not None:
                if change_type == "fall":
                    filtered = filtered[filtered['change_rate'] <= -min_change]
                else:
                    filtered = filtered[np.abs(filtered['change_rate']) >= min_change]
            
            # 등락률 기준 정렬 후 상위 N개 추출
            df_sorted = filtered.sort_values('change_rate', ascending=sort_ascending)
            result = df_sorted.head(top_n)['symbol'].tolist()
            
            # 캐시 저장
            self.cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            return result
                
        except Exception as e:
            logger.error(f"등락률 상위 종목 조회 실패: {e}")
            return []

    def get_stock_info(
        self, symbols: List[str], date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        종목 정보 상세 조회 (DatabaseManager 기반)

        Args:
            symbols: 종목 코드 리스트
            date: 기준일

        Returns:
            종목 정보 DataFrame
        """
        if not symbols:
            return pd.DataFrame()
        
        if date is None:
            date = self._get_latest_trading_date()
        
        try:
            db_date = self._date_db_format(date)
            
            # 심볼 목록을 SQL IN 절로 변환
            placeholders = ','.join(['?' for _ in symbols])
            
            # 종목 정보와 OHLCV 데이터 조인 쿼리
            query = f"""
            SELECT 
                si.symbol,
                si.name,
                si.market,
                si.market_cap,
                so.close,
                so.volume,
                si.market_cap / 100000000.0 as market_cap_billion
            FROM stock_info si
            LEFT JOIN stock_ohlcv so ON si.symbol = so.symbol AND so.date = ?
            WHERE si.symbol IN ({placeholders})
            """
            
            params = [db_date] + symbols
            df = self.db_manager.fetchdf(query, tuple(params))
            
            # 전일 대비 변화율 계산
            if not df.empty:
                prev_date_obj = datetime.strptime(date, '%Y%m%d') - timedelta(days=1)
                prev_db_date = prev_date_obj.strftime('%Y-%m-%d')
                
                prev_query = f"""
                SELECT symbol, close as prev_close
                FROM stock_ohlcv
                WHERE date = ? AND symbol IN ({placeholders})
                """
                
                prev_params = [prev_db_date] + symbols
                prev_df = self.db_manager.fetchdf(prev_query, tuple(prev_params))
                
                # 전일 데이터와 병합하여 변화율 계산
                df = df.merge(prev_df, on='symbol', how='left')
                df['change_rate'] = np.where(
                    (df['close'].notna()) & (df['prev_close'].notna()) & (df['prev_close'] != 0),
                    ((df['close'] - df['prev_close']) / df['prev_close']) * 100,
                    np.nan
                )
                df.drop('prev_close', axis=1, inplace=True)
            
            return df
                
        except Exception as e:
            logger.error(f"종목 정보 조회 실패: {e}")
            return pd.DataFrame()

    def get_available_data_summary(self) -> Dict[str, any]:
        """데이터베이스에 저장된 데이터 현황 요약"""
        try:
            # 종목 정보 요약
            market_data = self.db_manager.fetchall("SELECT market, COUNT(*) FROM stock_info GROUP BY market")
            market_counts = dict(market_data) if market_data else {}
            
            # OHLCV 데이터 요약
            ohlcv_symbols_data = self.db_manager.fetchall("SELECT COUNT(DISTINCT symbol) FROM stock_ohlcv")
            ohlcv_symbols = ohlcv_symbols_data[0][0] if ohlcv_symbols_data else 0
            
            ohlcv_records_data = self.db_manager.fetchall("SELECT COUNT(*) FROM stock_ohlcv")
            ohlcv_records = ohlcv_records_data[0][0] if ohlcv_records_data else 0
            
            date_range_data = self.db_manager.fetchall("SELECT MIN(date), MAX(date) FROM stock_ohlcv")
            date_range = date_range_data[0] if date_range_data else (None, None)
            
            return {
                'total_symbols': sum(market_counts.values()),
                'market_breakdown': market_counts,
                'ohlcv_symbols': ohlcv_symbols,
                'ohlcv_records': ohlcv_records,
                'date_range': date_range,
                'db_path': self.db_path
            }
                
        except Exception as e:
            logger.error(f"데이터 현황 조회 실패: {e}")
            return {}

    def clear_cache(self):
        """캐시 초기화"""
        self.cache = {}

    def validate_database(self) -> bool:
        """데이터베이스 유효성 확인"""
        try:
            # 필수 테이블 확인
            tables_data = self.db_manager.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in tables_data] if tables_data else []
            
            required_tables = ['stock_info', 'stock_ohlcv']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                logger.error(f"필수 테이블이 누락되었습니다: {missing_tables}")
                return False
            
            # 데이터 존재 여부 확인
            info_count_data = self.db_manager.fetchall("SELECT COUNT(*) FROM stock_info")
            info_count = info_count_data[0][0] if info_count_data else 0
            
            ohlcv_count_data = self.db_manager.fetchall("SELECT COUNT(*) FROM stock_ohlcv")
            ohlcv_count = ohlcv_count_data[0][0] if ohlcv_count_data else 0
            
            if info_count == 0:
                logger.warning("stock_info 테이블에 데이터가 없습니다.")
            
            if ohlcv_count == 0:
                logger.warning("stock_ohlcv 테이블에 데이터가 없습니다.")
            
            return True
                
        except Exception as e:
            logger.error(f"데이터베이스 검증 실패: {e}")
            return False


# 전역 인스턴스
stock_filter = StockFilter()


# 편의 함수들
def get_kospi_top(n: int = 30, by: str = "market_cap", **kwargs) -> List[str]:
    """
    코스피 상위 종목 조회 (편의 함수)

    Args:
        n: 상위 N개 종목
        by: 정렬 기준 ('market_cap', 'volume', 'change')
        **kwargs: 추가 매개변수

    Returns:
        종목 코드 리스트
    """
    if by == "market_cap":
        return stock_filter.get_market_cap_top(n, "KOSPI", **kwargs)
    elif by == "volume":
        return stock_filter.get_volume_top(n, "KOSPI", **kwargs)
    elif by == "change":
        return stock_filter.get_price_change_top(n, "KOSPI", **kwargs)
    else:
        return []


def get_kosdaq_top(n: int = 30, by: str = "market_cap", **kwargs) -> List[str]:
    """
    코스닥 상위 종목 조회 (편의 함수)

    Args:
        n: 상위 N개 종목
        by: 정렬 기준 ('market_cap', 'volume', 'change')
        **kwargs: 추가 매개변수

    Returns:
        종목 코드 리스트
    """
    if by == "market_cap":
        return stock_filter.get_market_cap_top(n, "KOSDAQ", **kwargs)
    elif by == "volume":
        return stock_filter.get_volume_top(n, "KOSDAQ", **kwargs)
    elif by == "change":
        return stock_filter.get_price_change_top(n, "KOSDAQ", **kwargs)
    else:
        return []


def get_database_summary() -> None:
    """데이터베이스 현황 출력"""
    summary = stock_filter.get_available_data_summary()
    print("=== 데이터베이스 현황 ===")
    print(f"총 종목 수: {summary.get('total_symbols', 0):,}개")
    
    market_breakdown = summary.get('market_breakdown', {})
    for market, count in market_breakdown.items():
        print(f"  {market}: {count:,}개")
    
    print(f"OHLCV 데이터:")
    print(f"  종목 수: {summary.get('ohlcv_symbols', 0):,}개")
    print(f"  총 레코드: {summary.get('ohlcv_records', 0):,}개")
    
    date_range = summary.get('date_range', (None, None))
    if date_range[0] and date_range[1]:
        print(f"  날짜 범위: {date_range[0]} ~ {date_range[1]}")


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    print("=== DatabaseManager 기반 종목 필터링 테스트 ===")
    
    # 데이터베이스 유효성 검증
    if not stock_filter.validate_database():
        print("⚠️ 데이터베이스 검증 실패")
        exit(1)
    
    # 데이터베이스 현황 출력
    get_database_summary()
    
    # 시가총액 상위 10개 종목
    print("\n1. 시가총액 상위 10개 종목 (코스피)")
    market_cap_stocks = get_kospi_top(10, "market_cap")
    
    if market_cap_stocks:
        info_df = stock_filter.get_stock_info(market_cap_stocks[:5])
        print(info_df[['symbol', 'name', 'market', 'market_cap_billion']].to_string(index=False))
    else:
        print("조회된 종목이 없습니다.")
    
    print("\n테스트 완료 - DatabaseManager 기반 리팩토링 성공")
