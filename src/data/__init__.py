"""
데이터 처리 모듈
- pykrx 데이터 수집 및 업데이트
- TA-Lib 기반 기술적 지표 계산
- 통합 SQLite 데이터베이스 관리
- 고도화된 주식 필터링 시스템
- 거래일 관리 및 캐싱
- 중앙 집중식 설정 관리
"""

# 핵심 모듈들
from .database import DatabaseManager
from .indicators import TechnicalIndicators, TALibIndicators
from .stock_filter import StockFilter
from .trading_calendar import TradingCalendar
from .stock_data_manager import StockDataManager
from .updater import StockDataUpdater

# 설정 관리 시스템
from .config import (
    DataConfigManager,
    DataConfig,
    DatabaseConfig,
    DataCollectionConfig,
    CacheConfig,
    FilterConfig,
    LoggingConfig,
    get_config,
    get_database_config,
    get_data_collection_config,
    get_cache_config,
    get_filter_config,
    get_logging_config,
    setup_logging,
)

# 편의 함수들
from .stock_filter import (
    get_kospi_top,
    get_kosdaq_top,
    get_database_summary,
)

# 전역 인스턴스들
from .stock_filter import stock_filter
from .trading_calendar import trading_calendar
from .config import config_manager

__all__ = [
    # 핵심 클래스들
    "DatabaseManager",
    "TechnicalIndicators", 
    "TALibIndicators",
    "StockDataManager",
    "StockFilter",
    "TradingCalendar",
    "StockDataUpdater",
    
    # 설정 관리 클래스들
    "DataConfigManager",
    "DataConfig",
    "DatabaseConfig",
    "DataCollectionConfig", 
    "CacheConfig",
    "FilterConfig",
    "LoggingConfig",
    
    # 설정 관련 함수들
    "get_config",
    "get_database_config",
    "get_data_collection_config",
    "get_cache_config",
    "get_filter_config", 
    "get_logging_config",
    "setup_logging",
    
    # 편의 함수들
    "get_kospi_top",
    "get_kosdaq_top", 
    "get_database_summary",
    
    # 전역 인스턴스들
    "stock_filter",
    "trading_calendar",
    "config_manager",
]


def initialize_data_module():
    """
    데이터 모듈 초기화 함수
    
    - 로깅 시스템 설정
    - 데이터베이스 스키마 확인
    - 설정 검증
    """
    # 로깅 시스템 초기화
    setup_logging()
    
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 설정 로드 확인
        config = get_config()
        logger.info("데이터 모듈 설정 로드 완료")
        
        # 데이터베이스 연결 테스트
        db_config = get_database_config()
        db_manager = DatabaseManager(db_config.full_path)
        
        # 스키마 초기화 (필요시)
        schema_path = str(config_manager.config.database.full_path.replace('.db', '').replace('trading', 'schema.sql'))
        try:
            import os
            if os.path.exists('data/schema.sql'):
                db_manager.initialize_schema('data/schema.sql')
                logger.info("데이터베이스 스키마 초기화 완료")
        except Exception as e:
            logger.warning(f"스키마 초기화 중 경고: {e}")
        
        # 필터 시스템 검증
        if stock_filter.validate_database():
            logger.info("주식 필터 시스템 검증 완료")
        else:
            logger.warning("주식 필터 시스템 검증 실패")
        
        logger.info("🚀 데이터 모듈 초기화 완료")
        return True
        
    except Exception as e:
        logger.error(f"데이터 모듈 초기화 실패: {e}")
        return False


def get_data_module_info():
    """데이터 모듈 정보 반환"""
    return {
        "version": "2.0",
        "description": "키움 API 알고리즘 매매 프로그램 데이터 처리 모듈",
        "features": [
            "DatabaseManager 기반 통합 데이터베이스 관리",
            "TA-Lib 기반 기술적 지표 계산 엔진", 
            "고성능 주식 필터링 및 캐싱 시스템",
            "한국 시장 거래일 관리",
            "중앙 집중식 설정 관리",
            "의존성 주입 패턴 적용"
        ],
        "improvements": [
            "순환 의존성 제거",
            "데이터베이스 접근 방식 통일",
            "설정 관리 통합",
            "스키마 중복 제거",
            "캐싱 시스템 강화"
        ]
    }


# 모듈 로드 시 자동 초기화 (선택적)
_auto_initialize = True

if _auto_initialize:
    try:
        initialize_data_module()
    except Exception as e:
        import logging
        logging.warning(f"자동 초기화 실패: {e}")


# 하위 호환성을 위한 별칭들
StockCollector = StockDataUpdater  # 기존 이름 호환성
TechnicalIndicator = TechnicalIndicators  # 단수형 별칭
