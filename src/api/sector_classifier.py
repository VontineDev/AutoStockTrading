"""
업종/섹터 분류 API 모듈

키움 API의 업종 정보와 정적 매핑을 활용하여 종목의 업종 분류를 제공합니다.
매개변수 최적화 시 업종별 종목 선택에 활용됩니다.
"""

import logging
from typing import Dict, List, Optional, Tuple
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import json

from src.utils.common import load_config

logger = logging.getLogger(__name__)

@dataclass
class SectorInfo:
    """업종 정보 데이터 클래스"""
    code: str
    name: str
    market: str  # KOSPI, KOSDAQ
    group: str   # 대분류 (예: 제조업, 서비스업 등)
    description: Optional[str] = None

@dataclass
class StockSectorInfo:
    """종목-업종 매핑 정보"""
    symbol: str
    name: str
    sector_code: str
    sector_name: str
    market: str
    market_cap: Optional[float] = None
    
class SectorClassifier:
    """
    업종 분류 서비스 클래스
    
    주요 기능:
    1. 업종 코드별 종목 리스트 제공
    2. 종목별 업종 정보 제공  
    3. 업종별 대표 종목 추천
    4. 최적화용 업종별 종목 그룹핑
    """
    
def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: 데이터베이스 경로 (기본: 프로젝트 루트/data/trading.db)
        """
        if db_path is None:
            config = load_config()
            project_root = Path(config.get('paths', {}).get('project_root', '.'))
            db_path = project_root / 'data' / 'trading.db'
        
        self.db_path = Path(db_path)
        self.sector_mapping = self._load_sector_mapping()
        self._ensure_sector_tables()
    
def _load_sector_mapping(self) -> Dict[str, SectorInfo]:
        """
        한국거래소 업종 분류 매핑 테이블 로드
        
        Returns:
            업종 코드별 SectorInfo 딕셔너리
        """
        # 한국거래소 표준 업종 분류 (KOSPI)
        kospi_sectors = {
            "001": SectorInfo("001", "종합(KOSPI)", "KOSPI", "지수"),
            "002": SectorInfo("002", "대형주", "KOSPI", "규모별"),
            "003": SectorInfo("003", "중형주", "KOSPI", "규모별"),  
            "004": SectorInfo("004", "소형주", "KOSPI", "규모별"),
            "005": SectorInfo("005", "음식료업", "KOSPI", "제조업"),
            "006": SectorInfo("006", "섬유의복", "KOSPI", "제조업"),
            "007": SectorInfo("007", "종이목재", "KOSPI", "제조업"), 
            "008": SectorInfo("008", "화학", "KOSPI", "제조업"),
            "009": SectorInfo("009", "의약품", "KOSPI", "제조업"),
            "010": SectorInfo("010", "비금속광물", "KOSPI", "제조업"),
            "011": SectorInfo("011", "철강금속", "KOSPI", "제조업"),
            "012": SectorInfo("012", "기계", "KOSPI", "제조업"),
            "013": SectorInfo("013", "전기전자", "KOSPI", "제조업"),
            "014": SectorInfo("014", "의료정밀", "KOSPI", "제조업"),
            "015": SectorInfo("015", "운수장비", "KOSPI", "제조업"),
            "016": SectorInfo("016", "유통업", "KOSPI", "서비스업"),
            "017": SectorInfo("017", "전기가스업", "KOSPI", "에너지"),
            "018": SectorInfo("018", "건설업", "KOSPI", "건설"),
            "019": SectorInfo("019", "운수창고업", "KOSPI", "서비스업"),
            "020": SectorInfo("020", "통신업", "KOSPI", "통신서비스"),
            "021": SectorInfo("021", "금융업", "KOSPI", "금융"),
            "022": SectorInfo("022", "은행", "KOSPI", "금융"),
            "023": SectorInfo("023", "증권", "KOSPI", "금융"),
            "024": SectorInfo("024", "보험", "KOSPI", "금융"),
            "025": SectorInfo("025", "서비스업", "KOSPI", "서비스업"),
            "026": SectorInfo("026", "제조업", "KOSPI", "제조업"),
        }
        
        # KOSDAQ 업종 분류
        kosdaq_sectors = {
            "101": SectorInfo("101", "종합(KOSDAQ)", "KOSDAQ", "지수"),
            "102": SectorInfo("102", "중견기업", "KOSDAQ", "규모별"),
            "103": SectorInfo("103", "기술성장", "KOSDAQ", "특성별"),
            "104": SectorInfo("104", "일반기업", "KOSDAQ", "특성별"),
            "105": SectorInfo("105", "소재", "KOSDAQ", "제조업"),
            "106": SectorInfo("106", "부품장비", "KOSDAQ", "제조업"),
            "107": SectorInfo("107", "IT", "KOSDAQ", "기술"),
            "108": SectorInfo("108", "생명과학", "KOSDAQ", "바이오"),
            "109": SectorInfo("109", "에너지화학", "KOSDAQ", "에너지"),
            "110": SectorInfo("110", "콘텐츠", "KOSDAQ", "서비스업"),
        }
        
        # 통합 매핑
        all_sectors = {**kospi_sectors, **kosdaq_sectors}
        
        return all_sectors
    
def _ensure_sector_tables(self):
        """업종 관련 테이블이 없으면 생성"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 업종 마스터 테이블
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sectors (
                        code TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        market TEXT NOT NULL,
                        group_name TEXT NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 종목-업종 매핑 테이블
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stock_sectors (
                        symbol TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        sector_code TEXT NOT NULL,
                        market TEXT NOT NULL,
                        market_cap REAL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sector_code) REFERENCES sectors (code)
                    )
                """)
                
                # 기본 업종 데이터 삽입
                self._insert_default_sectors(conn)
                
        except Exception as e:
            logger.error(f"업종 테이블 생성 실패: {e}")
    
def _insert_default_sectors(self, conn):
        """기본 업종 정보를 데이터베이스에 삽입"""
        try:
            for sector in self.sector_mapping.values():
                conn.execute("""
                    INSERT OR REPLACE INTO sectors (code, name, market, group_name, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (sector.code, sector.name, sector.market, sector.group, sector.description))
            
            conn.commit()
            logger.info(f"기본 업종 정보 {len(self.sector_mapping)}개 삽입 완료")
            
        except Exception as e:
            logger.error(f"기본 업종 데이터 삽입 실패: {e}")
    
def get_all_sectors(self, market: Optional[str] = None) -> List[SectorInfo]:
        """
        전체 업종 리스트 조회
        
        Args:
            market: 시장 필터 (KOSPI, KOSDAQ, None=전체)
            
        Returns:
            업종 정보 리스트
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                if market:
                    query = "SELECT code, name, market, group_name, description FROM sectors WHERE market = ? ORDER BY code"
                    rows = conn.execute(query, (market,)).fetchall()
                else:
                    query = "SELECT code, name, market, group_name, description FROM sectors ORDER BY market, code"
                    rows = conn.execute(query).fetchall()
                
                return [
                    SectorInfo(
                        code=row[0],
                        name=row[1], 
                        market=row[2],
                        group=row[3],
                        description=row[4]
                    ) for row in rows
                ]
                
        except Exception as e:
            logger.error(f"업종 리스트 조회 실패: {e}")
            return []
    
def get_stocks_by_sector(self, sector_code: str, limit: Optional[int] = None) -> List[StockSectorInfo]:
        """
        특정 업종의 종목들 조회
        
        Args:
            sector_code: 업종 코드
            limit: 최대 종목 수 (None=전체)
            
        Returns:
            종목-업종 정보 리스트
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 해당 업종에 속한 종목들 조회
                query = """
                    SELECT ss.symbol, ss.name, ss.sector_code, s.name as sector_name, 
                           ss.market, ss.market_cap
                    FROM stock_sectors ss
                    JOIN sectors s ON ss.sector_code = s.code
                    WHERE ss.sector_code = ?
                    ORDER BY ss.market_cap DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                rows = conn.execute(query, (sector_code,)).fetchall()
                
                return [
                    StockSectorInfo(
                        symbol=row[0],
                        name=row[1],
                        sector_code=row[2], 
                        sector_name=row[3],
                        market=row[4],
                        market_cap=row[5]
                    ) for row in rows
                ]
                
        except Exception as e:
            logger.error(f"업종별 종목 조회 실패 ({sector_code}): {e}")
            return []
    
def get_stock_sector(self, symbol: str) -> Optional[StockSectorInfo]:
        """
        특정 종목의 업종 정보 조회
        
        Args:
            symbol: 종목 코드
            
        Returns:
            종목-업종 정보 또는 None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT ss.symbol, ss.name, ss.sector_code, s.name as sector_name,
                           ss.market, ss.market_cap
                    FROM stock_sectors ss
                    JOIN sectors s ON ss.sector_code = s.code
                    WHERE ss.symbol = ?
                """
                
                row = conn.execute(query, (symbol,)).fetchone()
                
                if row:
                    return StockSectorInfo(
                        symbol=row[0],
                        name=row[1],
                        sector_code=row[2],
                        sector_name=row[3], 
                        market=row[4],
                        market_cap=row[5]
                    )
                return None
                
        except Exception as e:
            logger.error(f"종목 업종 조회 실패 ({symbol}): {e}")
            return None
    
def add_stock_sector_mapping(self, symbol: str, name: str, sector_code: str, 
                                market: str, market_cap: Optional[float] = None):
        """
        종목-업종 매핑 정보 추가/업데이트
        
        Args:
            symbol: 종목 코드
            name: 종목명
            sector_code: 업종 코드
            market: 시장 구분
            market_cap: 시가총액
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_sectors 
                    (symbol, name, sector_code, market, market_cap, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (symbol, name, sector_code, market, market_cap, datetime.now()))
                
                conn.commit()
                logger.debug(f"종목-업종 매핑 추가: {symbol} -> {sector_code}")
                
        except Exception as e:
            logger.error(f"종목-업종 매핑 추가 실패 ({symbol}): {e}")
    
def get_representative_stocks_by_sector(self, market: str = "KOSPI", 
                                          stocks_per_sector: int = 3) -> Dict[str, List[StockSectorInfo]]:
        """
        업종별 대표 종목들 조회 (시가총액 순)
        
        Args:
            market: 시장 구분
            stocks_per_sector: 업종당 종목 수
            
        Returns:
            업종별 대표 종목 딕셔너리
        """
        try:
            result = {}
            sectors = self.get_all_sectors(market)
            
            for sector in sectors:
                # 규모별, 지수는 제외
                if sector.group in ["규모별", "지수"]:
                    continue
                
                stocks = self.get_stocks_by_sector(sector.code, stocks_per_sector)
                if stocks:
                    result[sector.code] = stocks
            
            return result
            
        except Exception as e:
            logger.error(f"업종별 대표종목 조회 실패: {e}")
            return {}
    
def get_sector_groups_for_optimization(self, market: str = "KOSPI") -> Dict[str, Dict[str, List[str]]]:
        """
        매개변수 최적화용 업종별 종목 그룹 생성
        
        Args:
            market: 시장 구분
            
        Returns:
            그룹별 -> 업종별 -> 종목 리스트 딕셔너리
        """
        try:
            result = {}
            representative_stocks = self.get_representative_stocks_by_sector(market, 5)
            
            # 업종 그룹별로 정리
            for sector_code, stocks in representative_stocks.items():
                sector_info = self.sector_mapping.get(sector_code)
                if not sector_info:
                    continue
                    
                group_name = sector_info.group
                if group_name not in result:
                    result[group_name] = {}
                
                result[group_name][sector_info.name] = [stock.symbol for stock in stocks]
            
            return result
            
        except Exception as e:
            logger.error(f"최적화용 업종 그룹 생성 실패: {e}")
            return {}
    
def classify_symbol_by_name(self, symbol: str, name: str) -> str:
        """
        종목명 기반 간단한 업종 추정 (fallback 용도)
        
        Args:
            symbol: 종목 코드
            name: 종목명
            
        Returns:
            추정 업종 코드
        """
        # 간단한 키워드 기반 분류 (실제로는 더 정교한 로직 필요)
        name_lower = name.lower()
        
        # 대표적인 업종 키워드 매핑
        sector_keywords = {
            "013": ["전자", "반도체", "디스플레이", "LG", "삼성전자"],  # 전기전자
            "008": ["화학", "케미칼", "LG화학", "롯데케미칼"],           # 화학
            "022": ["은행", "금융", "신한", "KB", "하나"],               # 은행
            "020": ["통신", "텔레콤", "KT", "LG유플러스"],              # 통신업
            "015": ["자동차", "현대차", "기아"],                        # 운수장비
            "018": ["건설", "건설업", "GS건설", "대우건설"],            # 건설업
            "025": ["서비스", "카카오", "네이버", "엔터"],              # 서비스업
        }
        
        for sector_code, keywords in sector_keywords.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return sector_code
        
        # 기본값: 제조업
        return "026" if symbol.startswith(('0', '1', '2')) else "101"

# API 엔드포인트 함수들
def get_all_sectors_api(market: Optional[str] = None) -> Dict:
    """전체 업종 리스트 조회 API"""
    classifier = SectorClassifier()
    sectors = classifier.get_all_sectors(market)
    
    return {
        "status": "success",
        "data": [
            {
                "code": sector.code,
                "name": sector.name,
                "market": sector.market,
                "group": sector.group,
                "description": sector.description
            } for sector in sectors
        ],
        "total": len(sectors)
    }

def get_stocks_by_sector_api(sector_code: str, limit: int = 10) -> Dict:
    """특정 업종의 종목들 조회 API"""
    classifier = SectorClassifier()
    stocks = classifier.get_stocks_by_sector(sector_code, limit)
    
    return {
        "status": "success",
        "sector_code": sector_code,
        "data": [
            {
                "symbol": stock.symbol,
                "name": stock.name,
                "sector_name": stock.sector_name,
                "market": stock.market,
                "market_cap": stock.market_cap
            } for stock in stocks
        ],
        "total": len(stocks)
    }

def get_optimization_groups_api(market: str = "KOSPI") -> Dict:
    """매개변수 최적화용 업종별 종목 그룹 조회 API"""
    classifier = SectorClassifier()
    groups = classifier.get_sector_groups_for_optimization(market)
    
    return {
        "status": "success",
        "market": market,
        "data": groups,
        "total_groups": len(groups)
    }

def get_stock_sector_api(symbol: str) -> Dict:
    """특정 종목의 업종 정보 조회 API"""
    classifier = SectorClassifier()
    stock_info = classifier.get_stock_sector(symbol)
    
    if stock_info:
        return {
            "status": "success",
            "data": {
                "symbol": stock_info.symbol,
                "name": stock_info.name,
                "sector_code": stock_info.sector_code,
                "sector_name": stock_info.sector_name,
                "market": stock_info.market,
                "market_cap": stock_info.market_cap
            }
        }
    else:
        return {
            "status": "error",
            "message": f"종목 {symbol}의 업종 정보를 찾을 수 없습니다."
        } 