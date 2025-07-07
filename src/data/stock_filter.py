"""
주식 종목 필터링 유틸리티

시가총액, 거래량, 변동률 등 다양한 조건으로 종목을 필터링하는 최적화된 함수들
"""

import pandas as pd
import pykrx.stock as stock
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple
import logging
from functools import lru_cache
import time
from .trading_calendar import trading_calendar

logger = logging.getLogger(__name__)

class StockFilter:
    """주식 종목 필터링 클래스"""
    
    def __init__(self, cache_duration: int = 300):
        """
        초기화
        
        Args:
            cache_duration: 캐시 유지 시간(초) - 기본 5분
        """
        self.cache_duration = cache_duration
        self._cache = {}
        self._cache_time = {}
    
    def _get_cache_key(self, market: str, date: str, filter_type: str) -> str:
        """캐시 키 생성"""
        return f"{market}_{date}_{filter_type}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """캐시 유효성 확인"""
        if cache_key not in self._cache_time:
            return False
        
        elapsed = time.time() - self._cache_time[cache_key]
        return elapsed < self.cache_duration
    
    def _get_latest_trading_date(self, days_back: int = 30) -> str:
        """최근 거래일 조회 (견고한 버전)"""
        return trading_calendar.get_latest_trading_date(max_days_back=days_back)
    
    def get_market_cap_top(self, 
                          top_n: int = 30,
                          market: str = 'KOSPI',
                          date: Optional[str] = None,
                          min_cap: Optional[float] = None) -> List[str]:
        """
        시가총액 상위 종목 조회
        
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
        
        cache_key = self._get_cache_key(market, date, f'market_cap_top_{top_n}')
        
        # 캐시 확인
        if self._is_cache_valid(cache_key):
            logger.info(f"시가총액 상위 종목 캐시 사용: {cache_key}")
            return self._cache[cache_key]
        
        # 캐시된 데이터 확인
        cached_data = trading_calendar.get_cached_market_data(date, market, 'market_cap')
        if cached_data:
            logger.info(f"데이터베이스 캐시 사용: {market} ({date})")
            return cached_data[:top_n]
        
        # 여러 날짜 시도
        dates_to_try = [date]
        
        # 원본 날짜가 실패할 경우 이전 거래일들 시도
        for i in range(1, 6):
            try:
                prev_date = trading_calendar.get_previous_trading_date(date, i)
                dates_to_try.append(prev_date)
            except:
                break
        
        for attempt_date in dates_to_try:
            try:
                logger.info(f"시가총액 상위 {top_n}개 종목 조회: {market} ({attempt_date})")
                
                # 시가총액 데이터 조회
                if market == 'ALL':
                    # KOSPI + KOSDAQ 통합
                    kospi_df = stock.get_market_cap_by_ticker(attempt_date, market='KOSPI')
                    kosdaq_df = stock.get_market_cap_by_ticker(attempt_date, market='KOSDAQ')
                    df = pd.concat([kospi_df, kosdaq_df])
                else:
                    df = stock.get_market_cap_by_ticker(attempt_date, market=market)
                
                if df.empty:
                    logger.warning(f"시가총액 데이터 없음: {market} ({attempt_date})")
                    continue
                
                # 시가총액 기준 정렬
                df = df.sort_values('시가총액', ascending=False)
                
                # 최소 시가총액 필터링
                if min_cap:
                    df = df[df['시가총액'] >= min_cap * 100000000]  # 억원 -> 원 변환
                
                # 상위 N개 선택
                top_stocks = df.head(top_n).index.tolist()
                
                # 캐시 저장
                self._cache[cache_key] = top_stocks
                self._cache_time[cache_key] = time.time()
                
                # 데이터베이스 캐시 저장
                trading_calendar.cache_market_data(attempt_date, market, 'market_cap', top_stocks)
                
                logger.info(f"시가총액 상위 {len(top_stocks)}개 종목 조회 완료 ({attempt_date})")
                return top_stocks
                
            except Exception as e:
                logger.warning(f"시가총액 조회 실패 ({attempt_date}): {e}")
                continue
        
        logger.error(f"모든 날짜에서 시가총액 조회 실패: {market}")
        return []
    
    def get_volume_top(self, 
                      top_n: int = 30,
                      market: str = 'KOSPI',
                      date: Optional[str] = None,
                      days_avg: int = 5,
                      min_volume: Optional[int] = None) -> List[str]:
        """
        거래량 상위 종목 조회
        
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
        
        cache_key = self._get_cache_key(market, date, f'volume_top_{top_n}_{days_avg}')
        
        # 캐시 확인
        if self._is_cache_valid(cache_key):
            logger.info(f"거래량 상위 종목 캐시 사용: {cache_key}")
            return self._cache[cache_key]
        
        # 캐시된 데이터 확인
        cached_data = trading_calendar.get_cached_market_data(date, market, 'volume')
        if cached_data:
            logger.info(f"데이터베이스 캐시 사용: {market} ({date})")
            return cached_data[:top_n]
        
        # 여러 날짜 시도
        dates_to_try = [date]
        
        # 원본 날짜가 실패할 경우 이전 거래일들 시도
        for i in range(1, 6):
            try:
                prev_date = trading_calendar.get_previous_trading_date(date, i)
                dates_to_try.append(prev_date)
            except:
                break
        
        for attempt_date in dates_to_try:
            try:
                logger.info(f"거래량 상위 {top_n}개 종목 조회: {market} ({attempt_date})")
                
                # 기간 계산 - 거래일 기준으로 계산
                trading_dates = trading_calendar.get_trading_dates_range(
                    trading_calendar.get_previous_trading_date(attempt_date, days_avg),
                    attempt_date
                )
                
                if not trading_dates:
                    logger.warning(f"거래일 기간 계산 실패: {attempt_date}")
                    continue
                
                start_date = trading_dates[0]
                end_date = trading_dates[-1]
                
                # 거래량 데이터 조회
                if market == 'ALL':
                    # KOSPI + KOSDAQ 통합
                    kospi_df = stock.get_market_ohlcv_by_ticker(start_date, end_date, 'KOSPI')
                    kosdaq_df = stock.get_market_ohlcv_by_ticker(start_date, end_date, 'KOSDAQ')
                    df = pd.concat([kospi_df, kosdaq_df])
                else:
                    df = stock.get_market_ohlcv_by_ticker(start_date, end_date, market)
                
                if df.empty:
                    logger.warning(f"거래량 데이터 없음: {market} ({attempt_date})")
                    continue
                
                # 평균 거래량 계산
                if days_avg > 1:
                    # 여러 날짜 평균
                    volume_avg = df.groupby(df.index)['거래량'].mean()
                else:
                    # 단일 날짜
                    volume_avg = df['거래량']
                
                # 거래량 기준 정렬
                volume_avg = volume_avg.sort_values(ascending=False)
                
                # 최소 거래량 필터링
                if min_volume:
                    volume_avg = volume_avg[volume_avg >= min_volume]
                
                # 상위 N개 선택
                top_stocks = volume_avg.head(top_n).index.tolist()
                
                # 캐시 저장
                self._cache[cache_key] = top_stocks
                self._cache_time[cache_key] = time.time()
                
                # 데이터베이스 캐시 저장
                trading_calendar.cache_market_data(attempt_date, market, 'volume', top_stocks)
                
                logger.info(f"거래량 상위 {len(top_stocks)}개 종목 조회 완료 ({attempt_date})")
                return top_stocks
                
            except Exception as e:
                logger.warning(f"거래량 조회 실패 ({attempt_date}): {e}")
                continue
        
        logger.error(f"모든 날짜에서 거래량 조회 실패: {market}")
        return []
    
    def get_price_change_top(self, 
                           top_n: int = 30,
                           market: str = 'KOSPI',
                           date: Optional[str] = None,
                           change_type: str = 'rise',
                           min_change: Optional[float] = None) -> List[str]:
        """
        등락률 상위 종목 조회
        
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
        
        cache_key = self._get_cache_key(market, date, f'price_change_{change_type}_{top_n}')
        
        # 캐시 확인
        if self._is_cache_valid(cache_key):
            logger.info(f"등락률 상위 종목 캐시 사용: {cache_key}")
            return self._cache[cache_key]
        
        # 캐시된 데이터 확인
        cached_data = trading_calendar.get_cached_market_data(date, market, f'price_change_{change_type}')
        if cached_data:
            logger.info(f"데이터베이스 캐시 사용: {market} ({date})")
            return cached_data[:top_n]
        
        # 여러 날짜 시도
        dates_to_try = [date]
        
        # 원본 날짜가 실패할 경우 이전 거래일들 시도
        for i in range(1, 6):
            try:
                prev_date = trading_calendar.get_previous_trading_date(date, i)
                dates_to_try.append(prev_date)
            except:
                break
        
        for attempt_date in dates_to_try:
            try:
                logger.info(f"등락률 상위 {top_n}개 종목 조회: {market} ({attempt_date})")
                
                # 등락률 데이터 조회
                if market == 'ALL':
                    # KOSPI + KOSDAQ 통합
                    kospi_df = stock.get_market_ohlcv_by_ticker(attempt_date, attempt_date, 'KOSPI')
                    kosdaq_df = stock.get_market_ohlcv_by_ticker(attempt_date, attempt_date, 'KOSDAQ')
                    df = pd.concat([kospi_df, kosdaq_df])
                else:
                    df = stock.get_market_ohlcv_by_ticker(attempt_date, attempt_date, market)
                
                if df.empty:
                    logger.warning(f"등락률 데이터 없음: {market} ({attempt_date})")
                    continue
                
                # 등락률 계산 (당일 종가 기준)
                df['등락률'] = ((df['종가'] - df['시가']) / df['시가'] * 100)
                
                # 등락 타입별 정렬
                if change_type == 'rise':
                    df = df.sort_values('등락률', ascending=False)
                elif change_type == 'fall':
                    df = df.sort_values('등락률', ascending=True)
                elif change_type == 'abs':
                    df['등락률_절대값'] = df['등락률'].abs()
                    df = df.sort_values('등락률_절대값', ascending=False)
                
                # 최소 등락률 필터링
                if min_change:
                    if change_type == 'rise':
                        df = df[df['등락률'] >= min_change]
                    elif change_type == 'fall':
                        df = df[df['등락률'] <= -min_change]
                    elif change_type == 'abs':
                        df = df[df['등락률_절대값'] >= min_change]
                
                # 상위 N개 선택
                top_stocks = df.head(top_n).index.tolist()
                
                # 캐시 저장
                self._cache[cache_key] = top_stocks
                self._cache_time[cache_key] = time.time()
                
                # 데이터베이스 캐시 저장
                trading_calendar.cache_market_data(attempt_date, market, f'price_change_{change_type}', top_stocks)
                
                logger.info(f"등락률 상위 {len(top_stocks)}개 종목 조회 완료 ({attempt_date})")
                return top_stocks
                
            except Exception as e:
                logger.warning(f"등락률 조회 실패 ({attempt_date}): {e}")
                continue
        
        logger.error(f"모든 날짜에서 등락률 조회 실패: {market}")
        return []
    
    def get_combined_filter(self, 
                          market_cap_top: Optional[int] = None,
                          volume_top: Optional[int] = None,
                          price_change_top: Optional[int] = None,
                          market: str = 'KOSPI',
                          date: Optional[str] = None,
                          intersection: bool = True,
                          max_symbols: int = 50) -> List[str]:
        """
        복합 필터링 - 여러 조건 조합
        
        Args:
            market_cap_top: 시가총액 상위 N개 (None시 제외)
            volume_top: 거래량 상위 N개 (None시 제외)
            price_change_top: 등락률 상위 N개 (None시 제외)
            market: 시장 구분
            date: 기준일
            intersection: True=교집합, False=합집합
            max_symbols: 최대 종목 수
            
        Returns:
            필터링된 종목 코드 리스트
        """
        if date is None:
            date = self._get_latest_trading_date()
        
        results = []
        
        # 각 조건별 종목 리스트 수집
        if market_cap_top:
            cap_stocks = self.get_market_cap_top(market_cap_top, market, date)
            results.append(set(cap_stocks))
            logger.info(f"시가총액 상위 {len(cap_stocks)}개 종목")
        
        if volume_top:
            vol_stocks = self.get_volume_top(volume_top, market, date)
            results.append(set(vol_stocks))
            logger.info(f"거래량 상위 {len(vol_stocks)}개 종목")
        
        if price_change_top:
            change_stocks = self.get_price_change_top(price_change_top, market, date)
            results.append(set(change_stocks))
            logger.info(f"등락률 상위 {len(change_stocks)}개 종목")
        
        if not results:
            logger.warning("필터링 조건이 없습니다.")
            return []
        
        # 교집합 또는 합집합 계산
        if intersection:
            # 교집합
            combined = results[0]
            for result_set in results[1:]:
                combined = combined.intersection(result_set)
            final_stocks = list(combined)
            logger.info(f"교집합 결과: {len(final_stocks)}개 종목")
        else:
            # 합집합
            combined = set()
            for result_set in results:
                combined = combined.union(result_set)
            final_stocks = list(combined)
            logger.info(f"합집합 결과: {len(final_stocks)}개 종목")
        
        # 최대 종목 수 제한
        if len(final_stocks) > max_symbols:
            final_stocks = final_stocks[:max_symbols]
            logger.info(f"최대 종목 수 제한: {max_symbols}개")
        
        return final_stocks
    
    def get_stock_info(self, symbols: List[str], date: Optional[str] = None) -> pd.DataFrame:
        """
        종목 정보 상세 조회
        
        Args:
            symbols: 종목 코드 리스트
            date: 기준일
            
        Returns:
            종목 정보 DataFrame
        """
        if date is None:
            date = self._get_latest_trading_date()
        
        # 여러 날짜 시도
        dates_to_try = [date]
        
        # 원본 날짜가 실패할 경우 이전 거래일들 시도
        for i in range(1, 6):
            try:
                prev_date = trading_calendar.get_previous_trading_date(date, i)
                dates_to_try.append(prev_date)
            except:
                break
        
        for attempt_date in dates_to_try:
            try:
                info_list = []
                
                for symbol in symbols:
                    try:
                        # 종목명 조회
                        name = stock.get_market_ticker_name(symbol)
                        
                        # 기본 정보 조회
                        ohlcv = stock.get_market_ohlcv_by_ticker(attempt_date, attempt_date, 'ALL')
                        if symbol in ohlcv.index:
                            row = ohlcv.loc[symbol]
                            
                            # 시가총액 정보
                            try:
                                cap_df = stock.get_market_cap_by_ticker(attempt_date, market='ALL')
                                market_cap = cap_df.loc[symbol, '시가총액'] if symbol in cap_df.index else 0
                            except:
                                market_cap = 0
                            
                            info = {
                                'symbol': symbol,
                                'name': name,
                                'close': row['종가'],
                                'volume': row['거래량'],
                                'market_cap': market_cap,
                                'market_cap_billion': market_cap / 100000000,  # 억원 단위
                                'change_rate': ((row['종가'] - row['시가']) / row['시가'] * 100) if row['시가'] > 0 else 0
                            }
                            info_list.append(info)
                            
                    except Exception as e:
                        logger.warning(f"종목 정보 조회 실패 ({symbol}): {e}")
                        continue
                
                df = pd.DataFrame(info_list)
                logger.info(f"종목 정보 조회 완료: {len(df)}개 종목 ({attempt_date})")
                return df
                
            except Exception as e:
                logger.warning(f"종목 정보 조회 실패 ({attempt_date}): {e}")
                continue
        
        logger.error(f"모든 날짜에서 종목 정보 조회 실패")
        return pd.DataFrame()
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()
        self._cache_time.clear()
        logger.info("캐시 초기화 완료")


# 전역 인스턴스
stock_filter = StockFilter()

# 편의 함수들
def get_kospi_top(n: int = 30, by: str = 'market_cap', **kwargs) -> List[str]:
    """
    코스피 상위 종목 조회 (편의 함수)
    
    Args:
        n: 상위 N개 종목
        by: 정렬 기준 ('market_cap', 'volume', 'change')
        **kwargs: 추가 매개변수
    
    Returns:
        종목 코드 리스트
    """
    if by == 'market_cap':
        return stock_filter.get_market_cap_top(n, 'KOSPI', **kwargs)
    elif by == 'volume':
        return stock_filter.get_volume_top(n, 'KOSPI', **kwargs)
    elif by == 'change':
        return stock_filter.get_price_change_top(n, 'KOSPI', **kwargs)
    else:
        raise ValueError(f"Unknown filter type: {by}")

def get_kosdaq_top(n: int = 30, by: str = 'market_cap', **kwargs) -> List[str]:
    """
    코스닥 상위 종목 조회 (편의 함수)
    
    Args:
        n: 상위 N개 종목
        by: 정렬 기준 ('market_cap', 'volume', 'change')
        **kwargs: 추가 매개변수
    
    Returns:
        종목 코드 리스트
    """
    if by == 'market_cap':
        return stock_filter.get_market_cap_top(n, 'KOSDAQ', **kwargs)
    elif by == 'volume':
        return stock_filter.get_volume_top(n, 'KOSDAQ', **kwargs)
    elif by == 'change':
        return stock_filter.get_price_change_top(n, 'KOSDAQ', **kwargs)
    else:
        raise ValueError(f"Unknown filter type: {by}")

def get_all_market_top(n: int = 30, by: str = 'market_cap', **kwargs) -> List[str]:
    """
    전체 시장 상위 종목 조회 (편의 함수)
    
    Args:
        n: 상위 N개 종목
        by: 정렬 기준 ('market_cap', 'volume', 'change')
        **kwargs: 추가 매개변수
    
    Returns:
        종목 코드 리스트
    """
    if by == 'market_cap':
        return stock_filter.get_market_cap_top(n, 'ALL', **kwargs)
    elif by == 'volume':
        return stock_filter.get_volume_top(n, 'ALL', **kwargs)
    elif by == 'change':
        return stock_filter.get_price_change_top(n, 'ALL', **kwargs)
    else:
        raise ValueError(f"Unknown filter type: {by}")

def get_balanced_portfolio(n: int = 10, market: str = 'KOSPI', **kwargs) -> List[str]:
    """
    균형 잡힌 포트폴리오 종목 조회 (시가총액 + 거래량 교집합)
    
    Args:
        n: 상위 N개 종목
        market: 시장 구분
        **kwargs: 추가 매개변수
    
    Returns:
        종목 코드 리스트
    """
    return stock_filter.get_combined_filter(
        market_cap_top=n*3,  # 시가총액 상위 3배수
        volume_top=n*3,      # 거래량 상위 3배수
        market=market,
        intersection=True,   # 교집합
        max_symbols=n,
        **kwargs
    )


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)
    
    print("=== 종목 필터링 테스트 ===")
    
    # 시가총액 상위 10개 종목
    print("\n1. 시가총액 상위 10개 종목 (코스피)")
    market_cap_stocks = get_kospi_top(10, 'market_cap')
    for i, symbol in enumerate(market_cap_stocks, 1):
        try:
            name = stock.get_market_ticker_name(symbol)
            print(f"{i:2d}. {symbol} ({name})")
        except:
            print(f"{i:2d}. {symbol} (이름 조회 실패)")
    
    # 거래량 상위 10개 종목
    print("\n2. 거래량 상위 10개 종목 (코스피)")
    volume_stocks = get_kospi_top(10, 'volume')
    for i, symbol in enumerate(volume_stocks, 1):
        try:
            name = stock.get_market_ticker_name(symbol)
            print(f"{i:2d}. {symbol} ({name})")
        except:
            print(f"{i:2d}. {symbol} (이름 조회 실패)")
    
    # 등락률 상위 10개 종목
    print("\n3. 등락률 상위 10개 종목 (코스피)")
    change_stocks = get_kospi_top(10, 'change')
    for i, symbol in enumerate(change_stocks, 1):
        try:
            name = stock.get_market_ticker_name(symbol)
            print(f"{i:2d}. {symbol} ({name})")
        except:
            print(f"{i:2d}. {symbol} (이름 조회 실패)")
    
    # 복합 필터링 (시가총액 + 거래량 교집합)
    print("\n4. 복합 필터링 (시가총액 & 거래량 교집합)")
    combined_stocks = get_balanced_portfolio(10, 'KOSPI')
    for i, symbol in enumerate(combined_stocks, 1):
        try:
            name = stock.get_market_ticker_name(symbol)
            print(f"{i:2d}. {symbol} ({name})")
        except:
            print(f"{i:2d}. {symbol} (이름 조회 실패)")
    
    # 종목 정보 상세 조회
    if market_cap_stocks:
        print("\n5. 종목 정보 상세 조회 (시가총액 상위 5개)")
        info_df = stock_filter.get_stock_info(market_cap_stocks[:5])
        if not info_df.empty:
            print(info_df[['symbol', 'name', 'close', 'market_cap_billion', 'change_rate']].to_string(index=False))
        else:
            print("종목 정보 조회 실패") 