"""
한국 증권시장 거래일 관리 모듈
주말, 휴일 등을 고려한 견고한 거래일 탐지 및 처리
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from pykrx import stock
import os
import time

logger = logging.getLogger(__name__)

class TradingCalendar:
    """한국 증권시장 거래일 관리 클래스"""
    
    def __init__(self, db_path: str = 'data/trading_calendar.db'):
        self.db_path = db_path
        self.ensure_db_directory()
        self.init_database()
        
        # 2024년 한국 증권시장 휴일 (기본값)
        self.holidays = {
            '20240101': '신정',
            '20240209': '설날 연휴',
            '20240210': '설날 연휴',
            '20240211': '설날 연휴',
            '20240212': '설날 연휴',
            '20240301': '삼일절',
            '20240410': '국회의원 선거',
            '20240415': '어린이날 대체휴일',
            '20240501': '근로자의 날',
            '20240506': '어린이날',
            '20240515': '부처님오신날',
            '20240606': '현충일',
            '20240815': '광복절',
            '20240916': '추석 연휴',
            '20240917': '추석 연휴',
            '20240918': '추석 연휴',
            '20241003': '개천절',
            '20241009': '한글날',
            '20241225': '성탄절',
            '20241231': '연말'
        }
    
    def ensure_db_directory(self):
        """데이터베이스 디렉토리 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def init_database(self):
        """거래일 캐시 데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trading_days (
                    date TEXT PRIMARY KEY,
                    is_trading_day INTEGER,
                    market TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS market_data_cache (
                    date TEXT,
                    market TEXT,
                    data_type TEXT,
                    symbols TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, market, data_type)
                )
            ''')
    
    def is_weekend(self, date: str) -> bool:
        """주말 여부 확인"""
        date_obj = datetime.strptime(date, '%Y%m%d')
        return date_obj.weekday() >= 5  # 5: 토요일, 6: 일요일
    
    def is_holiday(self, date: str) -> bool:
        """휴일 여부 확인"""
        return date in self.holidays
    
    def is_trading_day_simple(self, date: str) -> bool:
        """간단한 거래일 확인 (주말/휴일 제외)"""
        return not (self.is_weekend(date) or self.is_holiday(date))
    
    def get_latest_trading_date(self, max_days_back: int = 30) -> str:
        """
        최근 거래일 조회 (견고한 버전)
        
        Args:
            max_days_back: 최대 검색 일수
            
        Returns:
            최근 거래일 (YYYYMMDD)
        """
        today = datetime.now()
        
        # 1. 캐시된 거래일 확인
        cached_date = self._get_cached_trading_date()
        if cached_date and self._is_recent_date(cached_date):
            logger.info(f"캐시된 거래일 사용: {cached_date}")
            return cached_date
        
        # 2. 간단한 로직으로 후보 날짜 생성
        for i in range(max_days_back):
            candidate_date = (today - timedelta(days=i)).strftime('%Y%m%d')
            
            # 주말/휴일 제외
            if not self.is_trading_day_simple(candidate_date):
                continue
            
            # 3. pykrx API로 실제 거래일 확인
            if self._verify_trading_day(candidate_date):
                logger.info(f"거래일 확인 완료: {candidate_date}")
                self._cache_trading_date(candidate_date)
                return candidate_date
        
        # 4. 폴백: 캐시된 데이터 중 가장 최근 날짜
        fallback_date = self._get_fallback_trading_date()
        if fallback_date:
            logger.warning(f"폴백 거래일 사용: {fallback_date}")
            return fallback_date
        
        # 5. 최종 폴백: 7일 전
        fallback_date = (today - timedelta(days=7)).strftime('%Y%m%d')
        logger.error(f"최종 폴백 거래일 사용: {fallback_date}")
        return fallback_date
    
    def _get_cached_trading_date(self) -> Optional[str]:
        """캐시된 거래일 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT date FROM trading_days 
                    WHERE is_trading_day = 1 
                    AND datetime(last_updated) > datetime('now', '-1 day')
                    ORDER BY date DESC LIMIT 1
                ''')
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"캐시된 거래일 조회 실패: {e}")
            return None
    
    def _is_recent_date(self, date: str) -> bool:
        """최근 날짜인지 확인 (3일 이내)"""
        try:
            date_obj = datetime.strptime(date, '%Y%m%d')
            days_diff = (datetime.now() - date_obj).days
            return days_diff <= 3
        except:
            return False
    
    def _verify_trading_day(self, date: str) -> bool:
        """pykrx API로 실제 거래일 확인"""
        try:
            # 빠른 확인을 위해 시가총액 데이터 조회
            df = stock.get_market_cap_by_ticker(date, market='KOSPI')
            is_trading = not df.empty and len(df) > 0
            
            # 결과 캐시
            self._cache_trading_day_result(date, is_trading)
            return is_trading
            
        except Exception as e:
            logger.debug(f"거래일 확인 실패 ({date}): {e}")
            return False
    
    def _cache_trading_date(self, date: str):
        """거래일 캐시 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO trading_days (date, is_trading_day, market)
                    VALUES (?, 1, 'KOSPI')
                ''', (date,))
        except Exception as e:
            logger.error(f"거래일 캐시 저장 실패: {e}")
    
    def _cache_trading_day_result(self, date: str, is_trading: bool):
        """거래일 확인 결과 캐시"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO trading_days (date, is_trading_day, market)
                    VALUES (?, ?, 'KOSPI')
                ''', (date, 1 if is_trading else 0))
        except Exception as e:
            logger.error(f"거래일 결과 캐시 실패: {e}")
    
    def _get_fallback_trading_date(self) -> Optional[str]:
        """폴백 거래일 조회 (캐시된 데이터 중 가장 최근)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT date FROM trading_days 
                    WHERE is_trading_day = 1 
                    ORDER BY date DESC LIMIT 1
                ''')
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"폴백 거래일 조회 실패: {e}")
            return None
    
    def get_trading_dates_range(self, start_date: str, end_date: str) -> List[str]:
        """기간 내 거래일 목록 조회"""
        trading_dates = []
        
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        current_dt = start_dt
        while current_dt <= end_dt:
            date_str = current_dt.strftime('%Y%m%d')
            if self.is_trading_day_simple(date_str):
                trading_dates.append(date_str)
            current_dt += timedelta(days=1)
        
        return trading_dates
    
    def get_previous_trading_date(self, date: str, days_back: int = 1) -> str:
        """이전 거래일 조회"""
        current_date = datetime.strptime(date, '%Y%m%d')
        
        for _ in range(days_back):
            while True:
                current_date -= timedelta(days=1)
                date_str = current_date.strftime('%Y%m%d')
                if self.is_trading_day_simple(date_str):
                    break
        
        return current_date.strftime('%Y%m%d')
    
    def cache_market_data(self, date: str, market: str, data_type: str, symbols: List[str]):
        """시장 데이터 캐시 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO market_data_cache 
                    (date, market, data_type, symbols)
                    VALUES (?, ?, ?, ?)
                ''', (date, market, data_type, ','.join(symbols)))
        except Exception as e:
            logger.error(f"시장 데이터 캐시 저장 실패: {e}")
    
    def get_cached_market_data(self, date: str, market: str, data_type: str) -> Optional[List[str]]:
        """캐시된 시장 데이터 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT symbols FROM market_data_cache 
                    WHERE date = ? AND market = ? AND data_type = ?
                    AND datetime(last_updated) > datetime('now', '-1 day')
                ''', (date, market, data_type))
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0].split(',')
        except Exception as e:
            logger.error(f"캐시된 시장 데이터 조회 실패: {e}")
        return None
    
    def cleanup_old_cache(self, days_old: int = 30):
        """오래된 캐시 정리"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    DELETE FROM trading_days 
                    WHERE datetime(last_updated) < datetime('now', '-{} days')
                '''.format(days_old))
                
                conn.execute('''
                    DELETE FROM market_data_cache 
                    WHERE datetime(last_updated) < datetime('now', '-{} days')
                '''.format(days_old))
                
                conn.commit()
                logger.info(f"{days_old}일 이상 오래된 캐시 정리 완료")
        except Exception as e:
            logger.error(f"캐시 정리 실패: {e}")


# 전역 인스턴스
trading_calendar = TradingCalendar() 