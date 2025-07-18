"""
중앙 집중식 설정 관리 모듈

모든 데이터 관련 설정을 통합 관리하여 일관성과 유지보수성 향상
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class DatabaseConfig:
    """데이터베이스 관련 설정"""
    path: str = "data/trading.db"
    trading_calendar_path: str = "data/trading_calendar.db"
    timeout: int = 30
    
    @property
    def full_path(self) -> str:
        return str(PROJECT_ROOT / self.path)
    
    @property
    def full_trading_calendar_path(self) -> str:
        return str(PROJECT_ROOT / self.trading_calendar_path)


@dataclass
class DataCollectionConfig:
    """데이터 수집 관련 설정"""
    api_delay: float = 0.2  # API 호출 간 지연 시간 (초)
    retry_count: int = 3
    timeout: int = 30
    batch_size: int = 100


@dataclass
class CacheConfig:
    """캐시 관련 설정"""
    duration: int = 300  # 5분 (초)
    max_size: int = 1000
    cleanup_interval: int = 3600  # 1시간 (초)


@dataclass
class FilterConfig:
    """필터링 관련 설정"""
    default_market: str = "KOSPI"
    default_top_n: int = 30
    min_market_cap_billion: float = 1.0  # 최소 시가총액 (억원)
    min_volume: int = 10000  # 최소 거래량


@dataclass
class LoggingConfig:
    """로깅 관련 설정"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: str = "logs/data.log"
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    @property
    def full_file_path(self) -> str:
        return str(PROJECT_ROOT / self.file_path)


@dataclass
class DataConfig:
    """통합 데이터 설정 클래스"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    data_collection: DataCollectionConfig = field(default_factory=DataCollectionConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # 환경변수 오버라이드
    def __post_init__(self):
        """환경변수로 설정 오버라이드"""
        # 데이터베이스 경로
        if db_path := os.getenv("DB_PATH"):
            self.database.path = db_path
        
        # API 지연시간
        if api_delay := os.getenv("API_DELAY"):
            try:
                self.data_collection.api_delay = float(api_delay)
            except ValueError:
                logger.warning(f"Invalid API_DELAY value: {api_delay}")
        
        # 로그 레벨
        if log_level := os.getenv("LOG_LEVEL"):
            self.logging.level = log_level.upper()


class DataConfigManager:
    """데이터 설정 관리자 클래스"""
    
    _instance: Optional['DataConfigManager'] = None
    _config: Optional[DataConfig] = None
    
    def __new__(cls) -> 'DataConfigManager':
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """설정 초기화"""
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> DataConfig:
        """설정 파일 로드 및 기본 설정 생성"""
        config = DataConfig()
        
        # config.yaml 파일 로드 시도
        config_path = PROJECT_ROOT / "config.yaml"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)
                
                # YAML 설정을 DataConfig에 적용
                if yaml_config:
                    self._apply_yaml_config(config, yaml_config)
                    logger.info(f"설정 파일 로드 완료: {config_path}")
                
            except Exception as e:
                logger.warning(f"설정 파일 로드 실패, 기본 설정 사용: {e}")
        else:
            logger.info("설정 파일이 없습니다. 기본 설정을 사용합니다.")
        
        return config
    
    def _apply_yaml_config(self, config: DataConfig, yaml_config: Dict[str, Any]):
        """YAML 설정을 DataConfig 객체에 적용"""
        # 데이터베이스 설정
        if db_config := yaml_config.get("database"):
            if "path" in db_config:
                config.database.path = db_config["path"]
            if "timeout" in db_config:
                config.database.timeout = db_config["timeout"]
        
        # 데이터 수집 설정
        if dc_config := yaml_config.get("data_collection"):
            if "api_delay" in dc_config:
                config.data_collection.api_delay = dc_config["api_delay"]
            if "retry_count" in dc_config:
                config.data_collection.retry_count = dc_config["retry_count"]
            if "timeout" in dc_config:
                config.data_collection.timeout = dc_config["timeout"]
        
        # 캐시 설정
        if cache_config := yaml_config.get("cache"):
            if "duration" in cache_config:
                config.cache.duration = cache_config["duration"]
            if "max_size" in cache_config:
                config.cache.max_size = cache_config["max_size"]
        
        # 필터 설정
        if filter_config := yaml_config.get("filter"):
            if "default_market" in filter_config:
                config.filter.default_market = filter_config["default_market"]
            if "default_top_n" in filter_config:
                config.filter.default_top_n = filter_config["default_top_n"]
        
        # 로깅 설정
        if log_config := yaml_config.get("logging"):
            if "level" in log_config:
                config.logging.level = log_config["level"]
            if "file_path" in log_config:
                config.logging.file_path = log_config["file_path"]
    
    @property
    def config(self) -> DataConfig:
        """현재 설정 반환"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def get_database_config(self) -> DatabaseConfig:
        """데이터베이스 설정 반환"""
        return self.config.database
    
    def get_data_collection_config(self) -> DataCollectionConfig:
        """데이터 수집 설정 반환"""
        return self.config.data_collection
    
    def get_cache_config(self) -> CacheConfig:
        """캐시 설정 반환"""
        return self.config.cache
    
    def get_filter_config(self) -> FilterConfig:
        """필터 설정 반환"""
        return self.config.filter
    
    def get_logging_config(self) -> LoggingConfig:
        """로깅 설정 반환"""
        return self.config.logging
    
    def reload_config(self):
        """설정 재로드"""
        self._config = self._load_config()
        logger.info("설정이 재로드되었습니다.")
    
    def save_config_template(self, path: Optional[str] = None):
        """설정 템플릿 파일 저장"""
        if path is None:
            path = str(PROJECT_ROOT / "config.yaml.template")
        
        template_config = {
            "database": {
                "path": "data/trading.db",
                "trading_calendar_path": "data/trading_calendar.db",
                "timeout": 30
            },
            "data_collection": {
                "api_delay": 0.2,
                "retry_count": 3,
                "timeout": 30,
                "batch_size": 100
            },
            "cache": {
                "duration": 300,
                "max_size": 1000,
                "cleanup_interval": 3600
            },
            "filter": {
                "default_market": "KOSPI",
                "default_top_n": 30,
                "min_market_cap_billion": 1.0,
                "min_volume": 10000
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file_path": "logs/data.log",
                "max_bytes": 10485760,
                "backup_count": 5
            }
        }
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(template_config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"설정 템플릿 저장 완료: {path}")
        except Exception as e:
            logger.error(f"설정 템플릿 저장 실패: {e}")


# 전역 설정 관리자 인스턴스
config_manager = DataConfigManager()


# 편의 함수들
def get_config() -> DataConfig:
    """현재 설정 반환"""
    return config_manager.config


def get_database_config() -> DatabaseConfig:
    """데이터베이스 설정 반환"""
    return config_manager.get_database_config()


def get_data_collection_config() -> DataCollectionConfig:
    """데이터 수집 설정 반환"""
    return config_manager.get_data_collection_config()


def get_cache_config() -> CacheConfig:
    """캐시 설정 반환"""
    return config_manager.get_cache_config()


def get_filter_config() -> FilterConfig:
    """필터 설정 반환"""
    return config_manager.get_filter_config()


def get_logging_config() -> LoggingConfig:
    """로깅 설정 반환"""
    return config_manager.get_logging_config()


def setup_logging():
    """로깅 설정 초기화"""
    log_config = get_logging_config()
    
    # 로그 디렉토리 생성
    log_dir = Path(log_config.full_file_path).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 로깅 설정
    logging.basicConfig(
        level=getattr(logging, log_config.level),
        format=log_config.format,
        handlers=[
            logging.FileHandler(log_config.full_file_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


if __name__ == "__main__":
    # 테스트 코드
    print("=== 데이터 설정 관리 테스트 ===")
    
    # 설정 로드
    config = get_config()
    print(f"데이터베이스 경로: {config.database.full_path}")
    print(f"API 지연시간: {config.data_collection.api_delay}초")
    print(f"캐시 지속시간: {config.cache.duration}초")
    print(f"기본 시장: {config.filter.default_market}")
    print(f"로그 레벨: {config.logging.level}")
    
    # 설정 템플릿 생성
    config_manager.save_config_template()
    print("설정 템플릿 생성 완료")
    
    print("설정 관리 시스템 초기화 완료") 