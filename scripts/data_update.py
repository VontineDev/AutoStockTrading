#!/usr/bin/env python3
"""
pykrx 기반 주식 데이터 자동 업데이트 스크립트

한국 주식 시장의 OHLCV 데이터를 pykrx를 통해 수집하고
SQLite 데이터베이스에 저장하는 스크립트입니다.
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
import logging
import time
import argparse
from pathlib import Path
import yaml

# 병렬 처리를 위한 imports
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import threading

# pykrx 관련 import
try:
    from pykrx import stock
    # bond와 etf 모듈은 pykrx 버전에 따라 없을 수 있음
    try:
        from pykrx import bond
    except ImportError:
        bond = None
    try:
        from pykrx import etf
    except ImportError:
        etf = None
except ImportError:
    print("pykrx가 설치되지 않았습니다. 'pip install pykrx'로 설치해주세요.")
    sys.exit(1)

# 병렬 처리를 위한 imports 추가
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import threading

# 프로젝트 루트 디렉토리를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'logs' / 'data_update.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 기존 imports 아래에 추가
try:
    from scripts.utils.optimized_data_updater import (
        create_optimized_data_updater, 
        progress_callback_with_eta,
        OptimizedDataUpdateConfig
    )
    OPTIMIZED_ENGINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"최적화 엔진을 불러올 수 없습니다: {e}")
    OPTIMIZED_ENGINE_AVAILABLE = False

class StockDataUpdater:
    """주식 데이터 업데이트 클래스"""
    
    def __init__(self, db_path: str = None, config_path: str = None):
        """
        Args:
            db_path: SQLite 데이터베이스 경로
            config_path: 설정 파일 경로
        """
        self.db_path = db_path or str(PROJECT_ROOT / 'data' / 'trading.db')
        self.config_path = config_path or str(PROJECT_ROOT / 'config.yaml')
        
        # 설정 로드
        self.config = self._load_config()
        
        # 데이터베이스 초기화
        self._init_database()
        
        # API 호출 간격 (초)
        self.api_delay = self.config.get('data_collection', {}).get('api_delay', 0.5)
        
        # API 사용량 추적
        self.api_call_count = 0
        self.session_start_time = datetime.now()
        
        # 병렬 처리를 위한 Lock
        self.db_lock = Lock()
        self.progress_lock = Lock()
        
        logger.info(f"데이터 업데이터 초기화 완료: DB={self.db_path}")
    
    def _load_config(self) -> Dict:
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"설정 파일 로드 실패: {e}")
        
        # 기본 설정 반환
        return {
            'data_collection': {
                'api_delay': 0.5,
                'max_retries': 3,
                'default_symbols': ['005930', '000660', '035420'],
                'market_indices': ['KOSPI', 'KOSDAQ'],
                'update_schedule': 'daily'
            }
        }
    
    def _init_database(self):
        """데이터베이스 및 테이블 초기화"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # 주식 데이터 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS stock_data (
                    symbol TEXT,
                    date DATE,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    amount BIGINT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, date)
                )
            ''')
            
            # 종목 정보 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS stock_info (
                    symbol TEXT PRIMARY KEY,
                    name TEXT,
                    market TEXT,
                    sector TEXT,
                    industry TEXT,
                    listing_date DATE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 시장 지수 테이블
            conn.execute('''
                CREATE TABLE IF NOT EXISTS market_indices (
                    index_name TEXT,
                    date DATE,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume BIGINT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (index_name, date)
                )
            ''')
            
            # 인덱스 생성
            conn.execute('CREATE INDEX IF NOT EXISTS idx_stock_data_date ON stock_data(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_stock_data_symbol ON stock_data(symbol)')
            
            conn.commit()
            logger.info("데이터베이스 테이블 초기화 완료")
    
    def get_kospi_symbols(self, limit: int = None) -> List[str]:
        """KOSPI 종목 코드 조회"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            symbols = stock.get_market_ticker_list(today, market="KOSPI")
            
            if limit:
                symbols = symbols[:limit]
            
            logger.info(f"KOSPI 종목 {len(symbols)}개 조회 완료")
            return symbols
            
        except Exception as e:
            logger.error(f"KOSPI 종목 조회 실패: {e}")
            return []
    
    def get_latest_trading_date_from_db(self) -> Optional[str]:
        """데이터베이스에서 최신 거래일 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT date FROM stock_data 
                    WHERE date <= date('now', 'localtime')
                    ORDER BY date DESC 
                    LIMIT 1
                ''')
                result = cursor.fetchone()
                if result:
                    return result[0]
            return None
        except Exception as e:
            logger.error(f"데이터베이스에서 최신 거래일 조회 실패: {e}")
            return None
    
    def get_kospi_top_symbols_from_db(self, target_date: str, limit: int = 30) -> Optional[List[str]]:
        """데이터베이스 데이터 기반 KOSPI 상위 종목 선별"""
        try:
            # 해당 날짜에 KOSPI 데이터가 충분히 있는지 확인
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT symbol, close, volume 
                    FROM stock_data 
                    WHERE date = ? AND volume > 0
                    ORDER BY volume DESC
                    LIMIT 200
                ''', (target_date,))
                
                db_data = cursor.fetchall()
                
                if len(db_data) < 50:  # 최소한의 데이터가 없으면 API 사용
                    logger.info(f"데이터베이스 내 {target_date} 데이터 부족 ({len(db_data)}개), API 호출 필요")
                    return None
                
                logger.info(f"데이터베이스에서 {target_date} 기준 {len(db_data)}개 종목 데이터 발견")
                
                # 해당 날짜의 시가총액 API 1회 호출로 순위 확인
                try:
                    market_cap_df = stock.get_market_cap_by_ticker(target_date, market="KOSPI")
                    
                    if not market_cap_df.empty and '시가총액' in market_cap_df.columns:
                        # DB에 있는 종목들 중에서 시가총액 상위 종목 선별
                        db_symbols = [row[0] for row in db_data]
                        available_caps = market_cap_df[market_cap_df.index.isin(db_symbols)]
                        
                        if len(available_caps) >= limit:
                            # 시가총액 기준 정렬
                            top_symbols = available_caps.sort_values('시가총액', ascending=False).head(limit).index.tolist()
                            
                            logger.info(f"데이터베이스 기반 KOSPI 상위 {len(top_symbols)}개 종목 선별 완료")
                            
                            # 상위 10개 종목 로그 출력
                            for i, symbol in enumerate(top_symbols[:10], 1):
                                try:
                                    name = stock.get_market_ticker_name(symbol)
                                    market_cap = available_caps.loc[symbol, '시가총액']
                                    logger.info(f"  {i:2d}. {symbol} - {name} (시총: {market_cap:,.0f}억원)")
                                except Exception:
                                    logger.info(f"  {i:2d}. {symbol}")
                            
                            if len(top_symbols) > 10:
                                logger.info(f"  ... 외 {len(top_symbols) - 10}개 종목")
                            
                            return top_symbols
                        
                except Exception as e:
                    logger.warning(f"시가총액 API 호출 실패: {e}")
                
                return None
                
        except Exception as e:
            logger.error(f"데이터베이스 기반 종목 선별 실패: {e}")
            return None
    
    def get_kospi_top_symbols_with_retry(self, limit: int = 30, max_retries: int = 3) -> Optional[List[str]]:
        """재시도 로직을 포함한 Ultra-Fast API 호출"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Ultra-Fast API 호출 시도 {attempt + 1}/{max_retries}")
                result = self.get_kospi_top_symbols_ultra_fast(limit)
                if result:
                    logger.info(f"Ultra-Fast API 호출 성공 (시도 {attempt + 1}회)")
                    return result
            except Exception as e:
                logger.warning(f"Ultra-Fast API 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 2초, 4초, 6초 대기
                    logger.info(f"{wait_time}초 대기 후 재시도...")
                    time.sleep(wait_time)
        
        logger.error(f"Ultra-Fast API 호출 {max_retries}회 모두 실패")
        return None
    
    def get_kospi_top_symbols_fallback(self, limit: int = 30) -> List[str]:
        """폴백: 전날 또는 최근 데이터 기반 종목 선별"""
        try:
            # 1. 데이터베이스에서 최근 거래일 찾기
            latest_date = self.get_latest_trading_date_from_db()
            
            if latest_date:
                logger.info(f"폴백: 데이터베이스 최신 거래일({latest_date}) 기반 종목 선별 시도")
                
                # 해당 날짜의 시가총액 조회 시도
                try:
                    market_cap_df = stock.get_market_cap_by_ticker(latest_date.replace('-', ''), market="KOSPI")
                    
                    if not market_cap_df.empty and '시가총액' in market_cap_df.columns:
                        # DB에 있는 종목들 확인
                        with sqlite3.connect(self.db_path) as conn:
                            cursor = conn.execute('''
                                SELECT DISTINCT symbol FROM stock_data 
                                WHERE date = ? AND volume > 0
                            ''', (latest_date,))
                            db_symbols = [row[0] for row in cursor.fetchall()]
                        
                        if db_symbols:
                            # DB에 있는 종목 중 상위 종목 선별
                            available_caps = market_cap_df[market_cap_df.index.isin(db_symbols)]
                            
                            if len(available_caps) >= limit:
                                top_symbols = available_caps.sort_values('시가총액', ascending=False).head(limit).index.tolist()
                                logger.info(f"폴백 성공: {latest_date} 기준 상위 {len(top_symbols)}개 종목")
                                return top_symbols
                except Exception as e:
                    logger.warning(f"폴백 시가총액 조회 실패: {e}")
            
            # 2. 최후의 수단: 기본 KOSPI 종목 리스트
            logger.warning("폴백: 기본 KOSPI 종목 리스트 사용")
            today = datetime.now().strftime('%Y%m%d')
            kospi_symbols = stock.get_market_ticker_list(today, market="KOSPI")
            
            if kospi_symbols:
                selected = kospi_symbols[:limit]
                logger.info(f"기본 KOSPI 상위 {len(selected)}개 종목 반환")
                return selected
            
            # 3. 하드코딩된 안전한 대형주들
            logger.error("모든 방법 실패, 하드코딩된 대형주 사용")
            safe_symbols = [
                '005930',  # 삼성전자
                '000660',  # SK하이닉스
                '207940',  # 삼성바이오로직스
                '373220',  # LG에너지솔루션
                '005380',  # 현대차
                '006400',  # 삼성SDI
                '051910',  # LG화학
                '035420',  # NAVER
                '005490',  # POSCO홀딩스
                '035720',  # 카카오
                '000270',  # 기아
                '105560',  # KB금융
                '055550',  # 신한지주
                '028260',  # 삼성물산
                '096770',  # SK이노베이션
            ]
            return safe_symbols[:limit]
            
        except Exception as e:
            logger.error(f"폴백 로직 실패: {e}")
            # 최종 안전망
            return ['005930', '000660', '207940', '373220', '005380'][:limit]
    
    def get_kospi_top_symbols(self, limit: int = 30) -> List[str]:
        """스마트 KOSPI 상위 종목 조회: DB 우선 → API 재시도 → 폴백"""
        logger.info(f"=== KOSPI 상위 {limit}개 종목 조회 시작 ===")
        
        try:
            today = datetime.now()
            today_str = today.strftime('%Y-%m-%d')
            today_api = today.strftime('%Y%m%d')
            
            # 1단계: 데이터베이스에서 최신 데이터 확인
            logger.info("1단계: 데이터베이스 최신 데이터 확인")
            latest_db_date = self.get_latest_trading_date_from_db()
            
            if latest_db_date:
                logger.info(f"데이터베이스 최신 거래일: {latest_db_date}")
                
                # 오늘 또는 최근 거래일 데이터가 있는지 확인
                if latest_db_date >= today_str or latest_db_date >= (today - timedelta(days=3)).strftime('%Y-%m-%d'):
                    logger.info("데이터베이스에 최신 데이터 존재, DB 기반 종목 선별 시도")
                    
                    db_result = self.get_kospi_top_symbols_from_db(latest_db_date, limit)
                    if db_result:
                        logger.info("✅ 데이터베이스 기반 종목 선별 성공")
                        return db_result
                    else:
                        logger.info("데이터베이스 데이터 부족, API 호출로 전환")
                else:
                    logger.info(f"데이터베이스 데이터가 오래됨 ({latest_db_date}), API 호출 필요")
            else:
                logger.info("데이터베이스에 데이터 없음, API 호출 필요")
            
            # 2단계: Ultra-Fast API 호출 (재시도 포함)
            logger.info("2단계: Ultra-Fast API 호출 (최대 3회 재시도)")
            api_result = self.get_kospi_top_symbols_with_retry(limit, max_retries=3)
            
            if api_result:
                logger.info("✅ Ultra-Fast API 호출 성공")
                return api_result
            
            # 3단계: 폴백 - 이전 데이터 사용
            logger.info("3단계: 폴백 - 이전 데이터 기반 종목 선별")
            fallback_result = self.get_kospi_top_symbols_fallback(limit)
            
            logger.info("⚠️ 폴백 모드로 종목 선별 완료")
            return fallback_result
            
        except Exception as e:
            logger.error(f"KOSPI 상위 종목 조회 전체 실패: {e}")
            
            # 최종 안전망: 하드코딩된 대형주
            logger.error("최종 안전망: 하드코딩된 대형주 사용")
            safe_symbols = ['005930', '000660', '207940', '373220', '005380']
            return safe_symbols[:limit]
    
    def get_kospi_top_symbols_ultra_fast(self, limit: int = 30) -> List[str]:
        """Ultra-Fast: 한번의 API 호출로 KOSPI 상위 종목 조회"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            
            # Ultra-Fast: 한번에 모든 KOSPI 종목의 OHLCV + 시가총액 조회
            logger.info("Ultra-Fast 모드: KOSPI 전체 종목 일괄 조회 시작")
            
            # API 호출 추적
            self._track_api_call()
            
            # 한번에 모든 데이터 조회 (OHLCV + 시가총액 포함)
            all_data = stock.get_market_ohlcv_by_ticker(today, market="KOSPI")
            
            if all_data.empty:
                logger.error("KOSPI 데이터 조회 실패")
                return []
            
            # 거래량이 있는 활성 종목만 필터링
            active_stocks = all_data[all_data['거래량'] > 0].copy()
            
            if active_stocks.empty:
                logger.warning("거래 활성 종목이 없음")
                return all_data.index.tolist()[:limit]
            
            # 시가총액 기준 정렬
            top_stocks = active_stocks.sort_values('시가총액', ascending=False)
            
            # 상위 종목 선택
            top_symbols = top_stocks.head(limit).index.tolist()
            
            logger.info(f"Ultra-Fast 조회 완료: 전체 {len(all_data)}개, 활성 {len(active_stocks)}개, 선별 {len(top_symbols)}개")
            
            # 상위 10개 종목 로그 출력
            display_count = min(10, len(top_stocks))
            logger.info(f"시가총액 상위 {display_count}개 종목:")
            
            for i, (symbol, row) in enumerate(top_stocks.head(display_count).iterrows(), 1):
                try:
                    name = stock.get_market_ticker_name(symbol)
                    market_cap = row['시가총액']
                    close_price = row['종가']
                    logger.info(f"  {i:2d}. {symbol} - {name} (시총: {market_cap:,.0f}억원, 종가: {close_price:,.0f}원)")
                except Exception as e:
                    logger.debug(f"종목명 조회 실패: {symbol} - {e}")
                    logger.info(f"  {i:2d}. {symbol} (시총: {market_cap:,.0f}억원)")
            
            if len(top_symbols) > display_count:
                logger.info(f"  ... 외 {len(top_symbols) - display_count}개 종목")
            
            return top_symbols
            
        except Exception as e:
            logger.error(f"Ultra-Fast 조회 실패: {e}")
            # 기존 방식으로 폴백
            logger.info("기존 방식으로 폴백")
            return self.get_kospi_top_symbols(limit)

    def get_kosdaq_symbols(self, limit: int = None) -> List[str]:
        """KOSDAQ 종목 코드 조회"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            symbols = stock.get_market_ticker_list(today, market="KOSDAQ")
            
            if limit:
                symbols = symbols[:limit]
            
            logger.info(f"KOSDAQ 종목 {len(symbols)}개 조회 완료")
            return symbols
            
        except Exception as e:
            logger.error(f"KOSDAQ 종목 조회 실패: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """종목 기본 정보 조회"""
        try:
            today = datetime.now().strftime('%Y%m%d')
            
            # 종목명 조회
            market_caps = stock.get_market_cap(today, today, symbol)
            if market_caps.empty:
                return None
            
            # KOSPI/KOSDAQ 구분
            kospi_symbols = set(stock.get_market_ticker_list(today, market="KOSPI"))
            market = "KOSPI" if symbol in kospi_symbols else "KOSDAQ"
            
            # 종목명
            name = stock.get_market_ticker_name(symbol)
            
            return {
                'symbol': symbol,
                'name': name,
                'market': market,
                'sector': '',  # pykrx에서는 직접 제공하지 않음
                'industry': '',
                'listing_date': None
            }
            
        except Exception as e:
            logger.warning(f"종목 정보 조회 실패 ({symbol}): {e}")
            return None
    
    def fetch_stock_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """개별 종목 데이터 조회"""
        max_retries = self.config['data_collection']['max_retries']
        
        for attempt in range(max_retries):
            try:
                # API 호출 추적
                self._track_api_call()
                
                # pykrx로 OHLCV 데이터 조회
                df = stock.get_market_ohlcv(start_date, end_date, symbol)
                
                if df.empty:
                    logger.warning(f"데이터 없음: {symbol} ({start_date}~{end_date})")
                    return None
                
                # 데이터 정리
                df = df.reset_index()
                
                # 실제 컬럼 확인 및 표준화
                logger.debug(f"원본 컬럼: {list(df.columns)} ({symbol})")
                
                if len(df.columns) == 7:  # ['날짜', '시가', '고가', '저가', '종가', '거래량', '등락률']
                    # 등락률 컬럼 제거하고 기본 OHLCV만 사용
                    df = df.iloc[:, :6]  # 처음 6개 컬럼만 선택
                    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                    df['amount'] = df['close'] * df['volume']
                elif len(df.columns) == 6:  # ['date', 'open', 'high', 'low', 'close', 'volume'] 
                    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                    df['amount'] = df['close'] * df['volume']
                else:
                    logger.warning(f"예상하지 못한 컬럼 구조: {list(df.columns)} ({symbol})")
                    continue
                
                df['symbol'] = symbol
                df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
                
                logger.debug(f"데이터 조회 성공: {symbol} ({len(df)}건)")
                return df
                
            except Exception as e:
                logger.warning(f"데이터 조회 실패 (시도 {attempt+1}/{max_retries}): {symbol} - {e}")
                if attempt < max_retries - 1:
                    time.sleep(self.api_delay * (attempt + 1))  # 점진적 대기
                
        return None
    
    def save_stock_data(self, df: pd.DataFrame):
        """주식 데이터를 데이터베이스에 저장 (Thread-safe, 개선된 중복 처리)"""
        try:
            # 병렬 처리 시 DB 접근을 동기화
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    # DataFrame을 리스트로 변환 (배치 처리용)
                    data_list = []
                    for _, row in df.iterrows():
                        # date를 문자열로 변환하여 SQLite 호환성 확보
                        date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                        
                        data_list.append((
                            str(row['symbol']), 
                            date_str, 
                            float(row['open']), 
                            float(row['high']), 
                            float(row['low']), 
                            float(row['close']),
                            int(row['volume']), 
                            int(row['amount'])
                        ))
                    
                    # 배치 처리로 안전하게 삽입 (중복 시 자동 교체)
                    conn.executemany('''
                        INSERT OR REPLACE INTO stock_data 
                        (symbol, date, open, high, low, close, volume, amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', data_list)
                    
                    conn.commit()
                    logger.debug(f"✅ 데이터 저장 완료: {len(df)}건 (배치 처리, Thread-safe)")
                
        except Exception as e:
            logger.error(f"❌ 데이터 저장 실패: {e}")
            raise
    
    def save_symbol_info(self, symbol_info: Dict):
        """종목 정보 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO stock_info 
                    (symbol, name, market, sector, industry, listing_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol_info['symbol'],
                    symbol_info['name'],
                    symbol_info['market'],
                    symbol_info['sector'],
                    symbol_info['industry'],
                    symbol_info['listing_date'],
                    datetime.now()
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"종목 정보 저장 실패: {e}")
    
    def get_last_update_date(self, symbol: str) -> Optional[date]:
        """종목의 마지막 업데이트 날짜 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT MAX(date) FROM stock_data WHERE symbol = ?',
                    (symbol,)
                )
                result = cursor.fetchone()[0]
                
                if result:
                    # 시간 정보가 포함된 경우와 날짜만 있는 경우를 모두 처리
                    if ' ' in result:
                        # '2025-07-07 00:00:00' 형태
                        return datetime.strptime(result.split(' ')[0], '%Y-%m-%d').date()
                    else:
                        # '2025-07-07' 형태
                        return datetime.strptime(result, '%Y-%m-%d').date()
                
        except Exception as e:
            logger.warning(f"마지막 업데이트 날짜 조회 실패 ({symbol}): {e}")
        
        return None
    
    def update_symbol(self, symbol: str, start_date: str = None, end_date: str = None, 
                     force_update: bool = False, show_date_progress: bool = False) -> bool:
        """개별 종목 데이터 업데이트 (개선된 날짜 진행상황 표시)"""
        try:
            # 종목 정보 업데이트
            symbol_info = self.get_symbol_info(symbol)
            if symbol_info:
                self.save_symbol_info(symbol_info)
            
            # 업데이트 날짜 범위 결정
            original_start_date = start_date
            if not start_date:
                if force_update:
                    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
                else:
                    last_date = self.get_last_update_date(symbol)
                    if last_date:
                        start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
                    else:
                        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            
            # 날짜 범위 표시 (진행상황 표시가 활성화된 경우)
            if show_date_progress:
                start_display = datetime.strptime(start_date, '%Y%m%d').strftime('%Y-%m-%d')
                end_display = datetime.strptime(end_date, '%Y%m%d').strftime('%Y-%m-%d')
                
                # 일수 계산
                start_dt = datetime.strptime(start_date, '%Y%m%d')
                end_dt = datetime.strptime(end_date, '%Y%m%d')
                total_days = (end_dt - start_dt).days + 1
                
                if total_days > 1:
                    logger.debug(f"📅 {symbol}: {start_display} ~ {end_display} ({total_days}일간)")
                else:
                    logger.debug(f"📅 {symbol}: {start_display} (1일)")
            
            # 이미 최신 상태인지 확인
            if not force_update:
                last_date = self.get_last_update_date(symbol)
                if last_date and last_date >= datetime.now().date():
                    if show_date_progress:
                        logger.debug(f"✨ {symbol}: 이미 최신 상태")
                    else:
                        logger.debug(f"이미 최신 상태: {symbol}")
                    return True
            
            # 데이터 조회 시작 시간
            fetch_start = datetime.now()
            
            # 데이터 조회
            df = self.fetch_stock_data(symbol, start_date, end_date)
            
            if df is not None and not df.empty:
                # 데이터 저장
                save_start = datetime.now()
                self.save_stock_data(df)
                
                # 처리 시간 계산
                fetch_time = (save_start - fetch_start).total_seconds()
                save_time = (datetime.now() - save_start).total_seconds()
                
                if show_date_progress:
                    # 데이터 범위 정보
                    data_start = df['date'].min().strftime('%Y-%m-%d')
                    data_end = df['date'].max().strftime('%Y-%m-%d')
                    
                    logger.info(f"💾 {symbol}: {len(df)}건 저장 완료 "
                              f"({data_start}~{data_end}) "
                              f"[조회:{fetch_time:.1f}s, 저장:{save_time:.1f}s]")
                else:
                    logger.info(f"업데이트 완료: {symbol} ({len(df)}건)")
                
                # API 호출 간격 대기
                time.sleep(self.api_delay)
                return True
            else:
                if show_date_progress:
                    logger.warning(f"📭 {symbol}: 업데이트할 데이터 없음 ({start_date}~{end_date})")
                else:
                    logger.warning(f"업데이트할 데이터 없음: {symbol}")
                return False
                
        except Exception as e:
            if show_date_progress:
                logger.error(f"💥 {symbol}: 업데이트 실패 - {e}")
            else:
                logger.error(f"종목 업데이트 실패: {symbol} - {e}")
            return False
    
    def update_multiple_symbols(self, symbols: List[str], start_date: str = None, 
                              end_date: str = None, force_update: bool = False) -> Dict[str, bool]:
        """여러 종목 일괄 업데이트 (개선된 진행상황 표시)"""
        results = {}
        total = len(symbols)
        start_time = datetime.now()
        
        # 날짜 범위 표시용
        date_range_str = ""
        if start_date and end_date:
            start_formatted = datetime.strptime(start_date, '%Y%m%d').strftime('%Y-%m-%d')
            end_formatted = datetime.strptime(end_date, '%Y%m%d').strftime('%Y-%m-%d') 
            date_range_str = f" ({start_formatted} ~ {end_formatted})"
        elif start_date:
            start_formatted = datetime.strptime(start_date, '%Y%m%d').strftime('%Y-%m-%d')
            date_range_str = f" (from {start_formatted})"
        
        logger.info(f"📊 일괄 업데이트 시작: {total}개 종목{date_range_str}")
        logger.info("="*60)
        logger.info("🚀 KOSPI 종목 일괄 업데이트 시작")
        logger.info(f"📈 대상 종목: {total}개")
        logger.info(f"📅 업데이트 기간{date_range_str}")
        logger.info("="*60)
        
        for i, symbol in enumerate(symbols, 1):
            # 경과 시간 계산
            elapsed = datetime.now() - start_time
            
            # 예상 완료 시간 계산
            if i > 1:
                avg_time_per_symbol = elapsed.total_seconds() / (i - 1)
                remaining_symbols = total - i + 1
                eta_seconds = avg_time_per_symbol * remaining_symbols
                eta_str = str(timedelta(seconds=int(eta_seconds)))
            else:
                eta_str = "계산 중..."
            
            # 백분율 계산
            progress_percent = (i / total) * 100
            
            # 진행 바 생성 (20자리)
            progress_bar_length = 20
            filled_length = int(progress_bar_length * i // total)
            bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
            
            # 종목명 조회 (캐시 사용)
            try:
                from pykrx import stock
                symbol_name = stock.get_market_ticker_name(symbol)
                if not symbol_name:
                    symbol_name = symbol
            except:
                symbol_name = symbol
            
            # 진행상황 출력
            print(f"\r🔄 [{bar}] {progress_percent:5.1f}% | {i:3d}/{total} | "
                  f"{symbol}({symbol_name[:8]}) | ETA: {eta_str}", end='', flush=True)
            
            logger.info(f"진행상황 [{progress_percent:5.1f}%]: {i}/{total} - {symbol}({symbol_name})")
            
            try:
                success = self.update_symbol(symbol, start_date, end_date, force_update, 
                                           show_date_progress=True)  # 날짜 진행상황 표시 활성화
                results[symbol] = success
                
                if success:
                    print(f" ✅", end='', flush=True)
                else:
                    print(f" ⚠️", end='', flush=True)
                
            except KeyboardInterrupt:
                print(f"\n\n❌ 사용자에 의해 중단됨 (진행률: {progress_percent:.1f}%)")
                logger.info("사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"예외 발생: {symbol} - {e}")
                results[symbol] = False
                print(f" ❌", end='', flush=True)
        
        # 최종 결과 요약
        print(f"\n\n{'='*60}")
        total_elapsed = datetime.now() - start_time
        success_count = sum(results.values())
        failed_count = total - success_count
        
        print(f"✅ 일괄 업데이트 완료!")
        print(f"📊 성공: {success_count}개 | 실패: {failed_count}개 | 전체: {total}개")
        print(f"⏱️  총 소요시간: {str(total_elapsed).split('.')[0]}")
        print(f"⚡ 평균 처리속도: {total / max(total_elapsed.total_seconds() / 60, 1):.1f} 종목/분")
        print(f"{'='*60}\n")
        
        logger.info(f"일괄 업데이트 완료: {success_count}/{total} 성공 (소요시간: {total_elapsed})")
        
        return results
    
    def _update_single_symbol_parallel(self, args_tuple) -> tuple:
        """병렬 처리용 단일 종목 업데이트 함수"""
        symbol, start_date, end_date, force_update = args_tuple
        
        try:
            success = self.update_symbol(symbol, start_date, end_date, force_update, show_date_progress=False)
            return symbol, success, None
        except Exception as e:
            return symbol, False, str(e)
    
    def update_multiple_symbols_parallel(self, symbols: List[str], start_date: str = None, 
                                       end_date: str = None, force_update: bool = False,
                                       max_workers: int = 5) -> Dict[str, bool]:
        """병렬 처리로 여러 종목 일괄 업데이트"""
        results = {}
        total = len(symbols)
        start_time = datetime.now()
        completed = 0
        
        # 날짜 범위 표시용
        date_range_str = ""
        if start_date and end_date:
            start_formatted = datetime.strptime(start_date, '%Y%m%d').strftime('%Y-%m-%d')
            end_formatted = datetime.strptime(end_date, '%Y%m%d').strftime('%Y-%m-%d') 
            date_range_str = f" ({start_formatted} ~ {end_formatted})"
        elif start_date:
            start_formatted = datetime.strptime(start_date, '%Y%m%d').strftime('%Y-%m-%d')
            date_range_str = f" (from {start_formatted})"
        
        logger.info(f"🚀 병렬 업데이트 시작: {total}개 종목{date_range_str} (워커: {max_workers}개)")
        print(f"\n{'='*70}")
        print(f"🚀 KOSPI 종목 병렬 업데이트 시작")
        print(f"📈 대상 종목: {total}개")
        print(f"⚡ 병렬 워커: {max_workers}개")
        print(f"📅 업데이트 기간{date_range_str}")
        print(f"{'='*70}")
        
        # 작업 인수 준비
        task_args = [(symbol, start_date, end_date, force_update) for symbol in symbols]
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 모든 작업 제출
                future_to_symbol = {
                    executor.submit(self._update_single_symbol_parallel, args): args[0] 
                    for args in task_args
                }
                
                # 완료된 작업 처리
                for future in as_completed(future_to_symbol):
                    symbol, success, error = future.result()
                    results[symbol] = success
                    completed += 1
                    
                    # 진행상황 업데이트 (thread-safe)
                    with self.progress_lock:
                        # 경과 시간 계산
                        elapsed = datetime.now() - start_time
                        
                        # 예상 완료 시간 계산
                        if completed > 1:
                            avg_time_per_symbol = elapsed.total_seconds() / completed
                            remaining_symbols = total - completed
                            eta_seconds = avg_time_per_symbol * remaining_symbols
                            eta_str = str(timedelta(seconds=int(eta_seconds)))
                        else:
                            eta_str = "계산 중..."
                        
                        # 백분율 계산
                        progress_percent = (completed / total) * 100
                        
                        # 진행 바 생성 (25자리)
                        progress_bar_length = 25
                        filled_length = int(progress_bar_length * completed // total)
                        bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
                        
                        # 종목명 조회 (간단히)
                        try:
                            from pykrx import stock
                            symbol_name = stock.get_market_ticker_name(symbol)
                            if not symbol_name:
                                symbol_name = symbol[:8]
                        except:
                            symbol_name = symbol[:8]
                        
                        # 성공/실패 표시
                        status_icon = "✅" if success else ("❌" if error else "⚠️")
                        
                        # 진행상황 출력
                        print(f"\r🔄 [{bar}] {progress_percent:5.1f}% | {completed:3d}/{total} | "
                              f"{symbol}({symbol_name}) {status_icon} | ETA: {eta_str}", end='', flush=True)
                        
                        if error:
                            logger.warning(f"종목 {symbol} 업데이트 실패: {error}")
                        
        except KeyboardInterrupt:
            print(f"\n\n❌ 사용자에 의해 중단됨 (진행률: {(completed/total)*100:.1f}%)")
            logger.info("병렬 업데이트가 사용자에 의해 중단됨")
            
        except Exception as e:
            print(f"\n\n❌ 병렬 처리 중 오류 발생: {e}")
            logger.error(f"병렬 처리 중 오류: {e}")
        
        # 최종 결과 요약
        print(f"\n\n{'='*70}")
        total_elapsed = datetime.now() - start_time
        success_count = sum(results.values())
        failed_count = completed - success_count
        
        print(f"✅ 병렬 업데이트 완료!")
        print(f"📊 성공: {success_count}개 | 실패: {failed_count}개 | 완료: {completed}개 | 전체: {total}개")
        print(f"⏱️  총 소요시간: {str(total_elapsed).split('.')[0]}")
        
        if completed > 0:
            print(f"⚡ 평균 처리속도: {completed / max(total_elapsed.total_seconds() / 60, 1):.1f} 종목/분")
            print(f"🚀 병렬 효율성: ~{max_workers}x 속도 향상 (예상)")
        
        print(f"{'='*70}\n")
        
        logger.info(f"병렬 업데이트 완료: {success_count}/{completed} 성공 (소요시간: {total_elapsed})")
        
        return results
    
    def update_market_indices(self, start_date: str = None, end_date: str = None):
        """시장 지수 업데이트"""
        indices = self.config['data_collection']['market_indices']
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        
        for index_name in indices:
            try:
                if index_name == 'KOSPI':
                    df = stock.get_index_ohlcv(start_date, end_date, "1001")  # KOSPI 지수
                elif index_name == 'KOSDAQ':
                    df = stock.get_index_ohlcv(start_date, end_date, "2001")  # KOSDAQ 지수
                else:
                    continue
                
                if not df.empty:
                    df = df.reset_index()
                    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                    df['index_name'] = index_name
                    df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
                    
                    with sqlite3.connect(self.db_path) as conn:
                        df.to_sql('market_indices', conn, if_exists='append', index=False)
                        
                        # 중복 제거
                        conn.execute('''
                            DELETE FROM market_indices 
                            WHERE rowid NOT IN (
                                SELECT MIN(rowid) 
                                FROM market_indices 
                                GROUP BY index_name, date
                            )
                        ''')
                        conn.commit()
                    
                    logger.info(f"시장 지수 업데이트 완료: {index_name}")
                
                time.sleep(self.api_delay)
                
            except Exception as e:
                logger.error(f"시장 지수 업데이트 실패: {index_name} - {e}")
    
    def get_data_summary(self) -> Dict:
        """데이터베이스 현황 요약"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 종목 수
                symbols_count = conn.execute('SELECT COUNT(DISTINCT symbol) FROM stock_data').fetchone()[0]
                
                # 데이터 기간
                date_range = conn.execute(
                    'SELECT MIN(date), MAX(date) FROM stock_data'
                ).fetchone()
                
                # 총 데이터 건수
                total_records = conn.execute('SELECT COUNT(*) FROM stock_data').fetchone()[0]
                
                # 최근 업데이트 종목
                recent_updates = conn.execute('''
                    SELECT symbol, MAX(date) as last_date 
                    FROM stock_data 
                    GROUP BY symbol 
                    ORDER BY last_date DESC 
                    LIMIT 5
                ''').fetchall()
                
                return {
                    'symbols_count': symbols_count,
                    'date_range': date_range,
                    'total_records': total_records,
                    'recent_updates': recent_updates,
                    'db_path': self.db_path
                }
                
        except Exception as e:
            logger.error(f"데이터 요약 조회 실패: {e}")
            return {}
    
    def _track_api_call(self):
        """API 호출 추적"""
        self.api_call_count += 1
        if self.api_call_count % 50 == 0:  # 50회마다 로그 출력
            elapsed = datetime.now() - self.session_start_time
            logger.info(f"API 호출 현황: {self.api_call_count}회 (경과시간: {elapsed})")
    
    def get_api_usage_status(self) -> Dict:
        """API 사용량 현황 조회"""
        elapsed = datetime.now() - self.session_start_time
        
        return {
            'api_calls': self.api_call_count,
            'session_duration': str(elapsed).split('.')[0],  # 초 단위 제거
            'calls_per_minute': round(self.api_call_count / max(elapsed.total_seconds() / 60, 1), 2),
            'estimated_daily_limit': 'pykrx는 무제한 (공개 데이터 기반)',
            'notes': 'pykrx는 한국거래소 공개 데이터를 사용하므로 API 제한이 거의 없습니다.'
        }
    
    def update_yesterday_data(self, symbols: List[str] = None, use_kospi_top: bool = False, top_limit: int = 30) -> Dict:
        """전날 데이터만 업데이트 (효율적인 일일 업데이트용)"""
        
        # 전날 거래일 계산
        yesterday = self._get_last_trading_day()
        
        # 대상 종목 결정
        if use_kospi_top:
            symbols = self.get_kospi_top_symbols(top_limit)
            logger.info(f"코스피 상위 {top_limit}개 종목의 전날 데이터 업데이트")
        elif not symbols:
            # 기본적으로 DB에 있는 모든 종목
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT DISTINCT symbol FROM stock_data")
                symbols = [row[0] for row in cursor.fetchall()]
            logger.info(f"기존 등록된 {len(symbols)}개 종목의 전날 데이터 업데이트")
        
        logger.info(f"전날 거래일: {yesterday}")
        
        # 결과 저장용
        results = {
            'date': yesterday,
            'total_symbols': len(symbols),
            'success_count': 0,
            'failed_count': 0,
            'new_data_count': 0,
            'duplicate_count': 0,
            'failed_symbols': []
        }
        
        for i, symbol in enumerate(symbols):
            try:
                # API 호출 추적
                self._track_api_call()
                
                # 전날 하루만 조회 (효율적)
                df = stock.get_market_ohlcv(yesterday, yesterday, symbol)
                
                if df.empty:
                    logger.warning(f"데이터 없음: {symbol} ({yesterday})")
                    results['failed_count'] += 1
                    results['failed_symbols'].append(symbol)
                    continue
                
                # 데이터 정리
                df = df.reset_index()
                
                # 실제 컬럼 확인 및 표준화
                logger.debug(f"원본 컬럼: {list(df.columns)} ({symbol})")
                
                if len(df.columns) == 7:  # ['날짜', '시가', '고가', '저가', '종가', '거래량', '등락률']
                    # 등락률 컬럼 제거하고 기본 OHLCV만 사용
                    df = df.iloc[:, :6]  # 처음 6개 컬럼만 선택
                    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                    df['amount'] = df['close'] * df['volume']
                elif len(df.columns) == 6:  # ['date', 'open', 'high', 'low', 'close', 'volume'] 
                    df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                    df['amount'] = df['close'] * df['volume']
                else:
                    logger.warning(f"예상하지 못한 컬럼 구조: {list(df.columns)} ({symbol})")
                    continue
                
                df['symbol'] = symbol
                df['date'] = pd.to_datetime(df['date'], format='mixed', errors='coerce')
                
                # 중복 체크
                with sqlite3.connect(self.db_path) as conn:
                    existing = pd.read_sql_query(
                        "SELECT COUNT(*) as count FROM stock_data WHERE symbol = ? AND DATE(date) = ?",
                        conn, params=(symbol, df.iloc[0]['date'].strftime('%Y-%m-%d'))
                    )
                    
                    if existing.iloc[0]['count'] > 0:
                        logger.debug(f"중복 데이터 건너뜀: {symbol} ({yesterday})")
                        results['duplicate_count'] += 1
                        results['success_count'] += 1  # 중복도 처리 성공으로 간주
                        continue
                    else:
                        # 새 데이터 저장
                        df.to_sql('stock_data', conn, if_exists='append', index=False)
                        results['new_data_count'] += 1
                        logger.debug(f"새 데이터 저장: {symbol} - 종가 {df.iloc[0]['close']:,}")
                
                results['success_count'] += 1
                
                # 진행률 표시
                if (i + 1) % 20 == 0 or (i + 1) == len(symbols):
                    logger.info(f"진행률: {i+1}/{len(symbols)} ({(i+1)/len(symbols)*100:.1f}%)")
                
                # API 호출 제한
                time.sleep(self.api_delay)
                
            except Exception as e:
                logger.error(f"전날 데이터 수집 실패: {symbol} - {e}")
                results['failed_count'] += 1
                results['failed_symbols'].append(symbol)
        
        # 결과 요약
        logger.info("=== 전날 데이터 업데이트 완료 ===")
        logger.info(f"날짜: {yesterday}")
        logger.info(f"처리 종목: {results['success_count']}/{results['total_symbols']}")
        logger.info(f"신규 데이터: {results['new_data_count']}건")
        logger.info(f"중복 건너뜀: {results['duplicate_count']}건")
        
        if results['failed_symbols']:
            logger.warning(f"실패 종목: {results['failed_symbols']}")
        
        return results
    
    def _get_last_trading_day(self) -> str:
        """마지막 거래일 조회 (주말/공휴일 고려)"""
        today = datetime.now()
        
        # 주말인 경우 금요일로 설정
        if today.weekday() == 0:  # 월요일
            last_trading_day = today - timedelta(days=3)  # 금요일
        elif today.weekday() == 6:  # 일요일  
            last_trading_day = today - timedelta(days=2)  # 금요일
        else:
            last_trading_day = today - timedelta(days=1)  # 전날
            
        return last_trading_day.strftime('%Y%m%d')

    def get_all_kospi_data_ultra_fast(self, date: str = None) -> Optional[pd.DataFrame]:
        """Ultra-Fast: 한번의 API 호출로 KOSPI 전체 종목 OHLCV + 시가총액 조회"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y%m%d')
            
            logger.info(f"Ultra-Fast 전체 KOSPI 데이터 조회: {date}")
            
            # API 호출 추적
            self._track_api_call()
            
            # 한번에 모든 데이터 조회
            all_data = stock.get_market_ohlcv_by_ticker(date, market="KOSPI")
            
            if all_data.empty:
                logger.error(f"KOSPI 데이터 조회 실패: {date}")
                return None
            
            # 데이터 정리 및 표준화
            df = all_data.reset_index()
            df.rename(columns={'티커': 'symbol'}, inplace=True)
            
            # 컬럼명 영문 변환
            column_mapping = {
                '시가': 'open',
                '고가': 'high', 
                '저가': 'low',
                '종가': 'close',
                '거래량': 'volume',
                '거래대금': 'amount',
                '등락률': 'change_rate',
                '시가총액': 'market_cap'
            }
            
            for kor_col, eng_col in column_mapping.items():
                if kor_col in df.columns:
                    df.rename(columns={kor_col: eng_col}, inplace=True)
            
            # 날짜 컬럼 추가
            df['date'] = pd.to_datetime(date, format='mixed', errors='coerce')
            
            # 거래량이 있는 활성 종목만 필터링
            active_df = df[df['volume'] > 0].copy()
            
            logger.info(f"Ultra-Fast 조회 완료: 전체 {len(df)}개, 활성 {len(active_df)}개 종목")
            
            return active_df
            
        except Exception as e:
            logger.error(f"Ultra-Fast 전체 데이터 조회 실패: {e}")
            return None

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='주식 데이터 업데이트 스크립트')
    parser.add_argument('--symbols', nargs='+', help='업데이트할 종목 코드들')
    parser.add_argument('--kospi', action='store_true', help='KOSPI 전체 종목 업데이트')
    parser.add_argument('--kosdaq', action='store_true', help='KOSDAQ 전체 종목 업데이트')
    parser.add_argument('--all-kospi', action='store_true', help='KOSPI 전체 종목 업데이트 (Ultra-Fast 방식)')
    parser.add_argument('--all-kosdaq', action='store_true', help='KOSDAQ 전체 종목 업데이트')
    parser.add_argument('--top-kospi', type=int, default=30, help='KOSPI 상위 N개 종목 업데이트 (기본: 30)')
    parser.add_argument('--limit', type=int, help='업데이트할 종목 수 제한')
    parser.add_argument('--start-date', help='시작 날짜 (YYYYMMDD)')
    parser.add_argument('--end-date', help='종료 날짜 (YYYYMMDD)')
    parser.add_argument('--force', action='store_true', help='강제 업데이트')
    parser.add_argument('--indices', action='store_true', help='시장 지수 업데이트')
    parser.add_argument('--summary', action='store_true', help='데이터베이스 현황 보기')
    parser.add_argument('--api-status', action='store_true', help='API 사용량 현황 보기')
    parser.add_argument('--yesterday-only', '-y', action='store_true', help='어제 데이터만 업데이트 (Ultra-Fast)')
    
    # 🤖 엔진 선택 및 성능 설정 (백테스팅과 동일한 구조)
    engine_group = parser.add_argument_group('🤖 처리 엔진 선택 및 성능 설정')
    engine_group.add_argument('--parallel', '-p', action='store_true', help='병렬 처리 엔진 강제 사용 (중규모 최적)')
    engine_group.add_argument('--optimized', '-o', action='store_true', help='최적화 엔진 강제 사용 (대규모 최적, 캐싱)')
    engine_group.add_argument('--workers', type=int, default=5, help='병렬 처리 워커 수 (기본: 5)')
    
    # 자동 엔진 선택 안내
    auto_group = parser.add_argument_group('자동 엔진 선택 (옵션 미지정 시)')
    auto_group.add_argument('--auto-help', action='store_true', help='자동 엔진 선택 로직 확인')
    
    args = parser.parse_args()
    
    # 자동 엔진 선택 도움말
    if args.auto_help:
        logger.info("\n🤖 종목 수에 따른 자동 엔진 선택:")
        logger.info("• 1-9개 종목: 순차 처리 (Sequential Engine) - 디버깅 최적")
        logger.info("• 10-99개 종목: 병렬 처리 (Parallel Engine) - 성능/안정성 균형") 
        logger.info("• 100개+ 종목: 최적화 엔진 (Optimized Engine) - 캐싱+배치+병렬")
        logger.info("\n강제 선택:")
        logger.info("  --parallel: 병렬 처리 강제 사용")
        logger.info("  --optimized: 최적화 엔진 강제 사용 (캐싱+배치+병렬)")
        return
    
    # 데이터 업데이터 초기화
    updater = StockDataUpdater()
    
        # API 사용량 현황 보기
    if args.api_status:
        status = updater.get_api_usage_status()
        logger.info("=== API 사용량 현황 ===")
        logger.info(f"API 호출 횟수: {status['api_calls']}회")
        logger.info(f"세션 지속 시간: {status['session_duration']}")
        logger.info(f"분당 호출 수: {status['calls_per_minute']}회/분")
        logger.info(f"일일 한도: {status['estimated_daily_limit']}")
        logger.info(f"참고사항: {status['notes']}")
        return

    # 데이터베이스 현황 보기
    if args.summary:
        summary = updater.get_data_summary()
        logger.info("=== 데이터베이스 현황 ===")
        logger.info(f"종목 수: {summary.get('symbols_count', 0):,}개")
        logger.info(f"데이터 기간: {summary.get('date_range', ('N/A', 'N/A'))[0]} ~ {summary.get('date_range', ('N/A', 'N/A'))[1]}")
        logger.info(f"총 데이터: {summary.get('total_records', 0):,}건")
        logger.info(f"DB 경로: {summary.get('db_path', 'N/A')}")
        
        if summary.get('recent_updates'):
            logger.info("최근 업데이트 종목:")
            for symbol, last_date in summary['recent_updates']:
                logger.info(f"  {symbol}: {last_date}")
        
        return
    
    # 시장 지수 업데이트
    if args.indices:
        logger.info("시장 지수 업데이트 시작")
        updater.update_market_indices(args.start_date, args.end_date)
        return
    
    # 어제 데이터만 업데이트 (Ultra-Fast)
    if args.yesterday_only:
        logger.info("=== 어제 데이터 Ultra-Fast 업데이트 시작 ===")
        
        # 상위 종목 또는 전체 종목 결정
        if hasattr(args, 'top_kospi') and args.top_kospi:
            results = updater.update_yesterday_data(use_kospi_top=True, top_limit=args.top_kospi)
            logger.info(f"코스피 상위 {args.top_kospi}개 종목의 어제 데이터 업데이트 완료")
        elif args.all_kospi:
            # 전체 KOSPI 종목 어제 데이터 업데이트
            all_symbols = updater.get_kospi_symbols()
            results = updater.update_yesterday_data(symbols=all_symbols)
            logger.info("전체 KOSPI 종목 어제 데이터 업데이트 완료")
        else:
            # 기본: 상위 30개 종목
            results = updater.update_yesterday_data(use_kospi_top=True, top_limit=30)
            logger.info("코스피 상위 30개 종목 어제 데이터 업데이트 완료")
        
        # 결과 출력
        logger.info("=== 어제 데이터 업데이트 결과 ===")
        logger.info(f"처리 종목: {results['success_count']}/{results['total_symbols']}")
        logger.info(f"신규 데이터: {results['new_data_count']}건")
        logger.info(f"중복 건너뜀: {results['duplicate_count']}건")
        
        if results['failed_symbols']:
            logger.warning(f"실패 종목: {results['failed_symbols']}")
        
        return

    # 전체 KOSPI 종목 업데이트 (Ultra-Fast 방식)
    if args.all_kospi:
        logger.info("=== 전체 KOSPI 종목 업데이트 시작 ===")
        
        # 기간이 지정된 경우 기존 방식 사용
        if args.start_date or args.end_date:
            logger.info("기간이 지정되어 기존 방식으로 전체 KOSPI 업데이트")
            symbols_to_update = updater.get_kospi_symbols(args.limit)
            logger.info(f"전체 KOSPI {len(symbols_to_update)}개 종목 선택됨")
        else:
            # Ultra-Fast 방식으로 당일 전체 KOSPI 데이터 조회
            logger.info("Ultra-Fast 방식으로 당일 전체 KOSPI 데이터 업데이트")
            ultra_fast_data = updater.get_all_kospi_data_ultra_fast()
            
            if ultra_fast_data is not None:
                logger.info(f"Ultra-Fast 조회 성공: {len(ultra_fast_data)}개 종목")
                
                # Ultra-Fast 데이터를 DB에 저장
                try:
                    updater.save_stock_data(ultra_fast_data)
                    logger.info("✅ Ultra-Fast 데이터 저장 완료")
                    
                    logger.info("=== Ultra-Fast 전체 KOSPI 업데이트 결과 ===")
                    logger.info(f"업데이트 종목: {len(ultra_fast_data)}개")
                    logger.info(f"업데이트 날짜: {ultra_fast_data['date'].iloc[0].strftime('%Y-%m-%d')}")
                    logger.info("✅ 전체 KOSPI 종목 Ultra-Fast 업데이트 완료")
                    
                    # API 사용량 출력
                    final_status = updater.get_api_usage_status()
                    logger.info("=== API 사용량 요약 ===")
                    logger.info(f"총 API 호출: {final_status['api_calls']}회")
                    logger.info(f"소요 시간: {final_status['session_duration']}")
                    
                    return
                    
                except Exception as e:
                    logger.error(f"Ultra-Fast 데이터 저장 실패: {e}")
                    logger.warning("❌ Ultra-Fast 데이터 저장 실패, 기존 방식으로 전환")
            else:
                logger.error("Ultra-Fast 조회 실패, 기존 방식으로 전환")
            
            # Ultra-Fast 실패시 기존 방식으로 폴백
            symbols_to_update = updater.get_kospi_symbols(args.limit)
            logger.info(f"기존 방식으로 전체 KOSPI {len(symbols_to_update)}개 종목 업데이트")
    
    # 전체 KOSDAQ 종목 업데이트  
    elif args.all_kosdaq:
        logger.info("=== 전체 KOSDAQ 종목 업데이트 시작 ===")
        symbols_to_update = updater.get_kosdaq_symbols()
        logger.info(f"전체 KOSDAQ {len(symbols_to_update)}개 종목 선택됨")
    
    # 업데이트할 종목 결정
    else:
        symbols_to_update = []
        
        if args.symbols:
            symbols_to_update = args.symbols
        elif hasattr(args, 'top_kospi') and args.top_kospi:
            # 코스피 상위 종목 (명령줄에서 --top-kospi가 사용된 경우)
            symbols_to_update = updater.get_kospi_top_symbols(args.top_kospi)
            logger.info(f"코스피 상위 {args.top_kospi}개 종목 선택됨")
        elif args.kospi:
            symbols_to_update = updater.get_kospi_symbols(args.limit)
        elif args.kosdaq:
            symbols_to_update = updater.get_kosdaq_symbols(args.limit)
        else:
            # 기본 종목들
            default_symbols = updater.config['data_collection']['default_symbols']
            symbols_to_update = default_symbols
            logger.info(f"기본 종목 업데이트: {default_symbols}")
    
    if not symbols_to_update:
        logger.error("업데이트할 종목이 없습니다.")
        return
    
    # 2년 기간 설정 (기본값)
    if not args.start_date:
        # 2년 전부터 현재까지
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y%m%d')
        logger.info(f"기본 시작 날짜 설정: {start_date} (2년 전)")
    else:
        start_date = args.start_date
    
    end_date = args.end_date or datetime.now().strftime('%Y%m%d')
    
    # 종목 데이터 업데이트
    logger.info(f"업데이트 시작: {len(symbols_to_update)}개 종목 ({start_date}~{end_date})")
    
    # 🤖 종목 수에 따른 최적 엔진 자동 선택
    num_symbols = len(symbols_to_update)
    force_parallel = getattr(args, 'parallel', False)
    force_optimized = getattr(args, 'optimized', False)
    
    # 엔진 선택 로직
    if force_optimized:
        engine_type = 'optimized'
        if OPTIMIZED_ENGINE_AVAILABLE:
            logger.info("🎯 사용자 지정: 최적화 엔진 (캐싱 + 병렬 + 배치)")
        else:
            logger.info("🎯 사용자 지정: 최적화 엔진 요청됨 - 병렬 엔진으로 대체")
            engine_type = 'parallel'
    elif force_parallel:
        engine_type = 'parallel'
        logger.info("🎯 사용자 지정: 병렬 엔진 (ThreadPool 병렬 처리)")
    elif num_symbols >= 100:
        engine_type = 'optimized'
        if OPTIMIZED_ENGINE_AVAILABLE:
            logger.info(f"🚀 자동 선택: 최적화 엔진 (대규모 {num_symbols}개 종목)")
            logger.info("   └─ 이유: 캐싱 + 메모리 최적화 + 병렬 처리로 최고 성능")
        else:
            logger.info("🚀 자동 선택: 최적화 엔진 권장 - 병렬 엔진으로 대체")
            engine_type = 'parallel'
    elif num_symbols >= 10:
        engine_type = 'parallel'
        logger.info(f"⚡ 자동 선택: 병렬 엔진 (중규모 {num_symbols}개 종목)")
        logger.info("   └─ 이유: 병렬 처리로 최적 성능/안정성 균형")
    else:
        engine_type = 'sequential'
        logger.info(f"🐌 자동 선택: 순차 엔진 (소규모 {num_symbols}개 종목)")
        logger.info("   └─ 이유: 순차 처리로 디버깅 및 안정성 최적화")
    
    # 선택된 엔진으로 실행
    if engine_type == 'optimized':
        logger.info("🚀 최적화 엔진 실행 (캐싱 + 배치 + 병렬)")
        logger.info("   ├─ 중복 업데이트 방지: 캐싱으로 이미 최신인 종목 건너뛰기")
        logger.info("   ├─ 증분 업데이트: 누락된 날짜만 업데이트") 
        logger.info("   ├─ 배치 최적화: API 호출 효율성 극대화")
        logger.info("   ├─ 메모리 관리: 대용량 처리 시 메모리 최적화")
        logger.info("   └─ 예상 성능 향상: 3-5배 빠른 처리 속도")
        
        # 최적화 엔진 생성 및 실행
        optimized_updater = create_optimized_data_updater(
            db_path=updater.db_path,
            max_workers=args.workers,
            enable_cache=True,
            batch_size=30,
            progress_callback=progress_callback_with_eta
        )
        
        # 최적화된 업데이트 실행
        optimization_results = optimized_updater.update_symbols_optimized(
            symbols=symbols_to_update,
            start_date=start_date,
            end_date=end_date,
            force_update=args.force
        )
        
        # 결과 변환 (기존 형식과 호환)
        results = optimization_results['results']
        
        # 최적화 통계 출력
        performance = optimization_results['performance_analysis']
        cache_stats = optimization_results['cache_stats']
        
        logger.info("📊 최적화 성능 분석:")
        logger.info(f"   ├─ 총 처리 시간: {performance['total_time']:.2f}초")
        logger.info(f"   ├─ 처리 속도: {performance['symbols_per_second']:.1f} 종목/초")
        logger.info(f"   ├─ 성공률: {performance['success_rate']:.1%}")
        logger.info(f"   ├─ 캐시 효율성: {performance['cache_efficiency']:.1%}")
        logger.info(f"   ├─ 건너뛴 종목: {cache_stats['skipped_updates']}개")
        logger.info(f"   ├─ 증분 업데이트: {cache_stats['incremental_updates']}개")
        logger.info(f"   ├─ 전체 업데이트: {cache_stats['full_updates']}개")
        logger.info(f"   └─ 전체 최적화 효율성: {performance['overall_efficiency']:.1%}")
        
        logger.info(f"최적화된 업데이트 완료: {performance['successful_updates']}/{performance['total_symbols']} 성공")
        
    elif engine_type == 'parallel':
        logger.info(f"🚀 병렬 처리 엔진 실행 (워커: {args.workers}개)")
        results = updater.update_multiple_symbols_parallel(
            symbols_to_update,
            start_date,
            end_date,
            args.force,
            max_workers=args.workers
        )
    else:  # sequential
        logger.info("🐌 순차 처리 엔진 실행")
        results = updater.update_multiple_symbols(
            symbols_to_update,
            start_date,
            end_date,
            args.force
        )
    
    # 결과 출력
    success_count = sum(results.values())
    total_count = len(results)
    
    logger.info("=== 업데이트 결과 ===")
    logger.info(f"성공: {success_count}/{total_count}")
    logger.info(f"실패: {total_count - success_count}")
    
    if total_count - success_count > 0:
        failed_symbols = [symbol for symbol, success in results.items() if not success]
        logger.warning(f"실패 종목: {failed_symbols}")
    
    # 최종 API 사용량 출력
    final_status = updater.get_api_usage_status()
    logger.info("=== API 사용량 요약 ===")
    logger.info(f"총 API 호출: {final_status['api_calls']}회")
    logger.info(f"소요 시간: {final_status['session_duration']}")

if __name__ == "__main__":
    main() 