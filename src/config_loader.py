"""
설정 및 환경 변수 로딩을 중앙에서 관리하는 모듈
"""
import yaml
from dotenv import load_dotenv
from pathlib import Path
import os
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT = Path(__file__).parent.parent

def get_project_root() -> Path:
    """프로젝트 루트 디렉토리를 반환합니다."""
    return PROJECT_ROOT

def load_config() -> dict:
    """
    config.yaml 파일을 로드하여 설정 딕셔너리를 반환합니다.
    파일이 없거나 오류 발생 시 기본 설정을 반환합니다.
    """
    config_path = PROJECT_ROOT / "config.yaml"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.info(f"✅ 설정 파일 로드 완료: {config_path}")
                return config
        else:
            logger.warning(f"⚠️ 설정 파일({config_path})을 찾을 수 없습니다. 기본 설정을 사용합니다.")
    except Exception as e:
        logger.error(f"❌ 설정 파일 로드 실패: {e}")

    # 기본 설정 반환
    return {
        "project": {"name": "TA-Lib Swing Trading", "version": "1.0.0"},
        "logging": {"level": "INFO", "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
    }

def load_env_vars():
    """
    .env 파일에서 환경 변수를 로드합니다.
    """
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"✅ 환경변수 로드 완료: {env_path}")
    else:
        logger.warning(f"⚠️ 환경변수 파일(.env)이 없습니다. 시스템 환경변수를 사용합니다.")

def get_kiwoom_env() -> dict:
    """
    키움 API 관련 환경 변수를 딕셔너리로 반환합니다.
    """
    load_env_vars()
    
    use_mock = os.getenv("USE_KIWOOM_MOCK", "true").lower() == "true"
    
    if use_mock:
        return {
            "env_type": "모의투자",
            "base_url": "https://openapivts.kiwoom.com:29443",
            "api_key": os.getenv("KIWOOM_MOCK_API_KEY"),
            "api_secret": os.getenv("KIWOOM_MOCK_API_SECRET"),
        }
    else:
        return {
            "env_type": "실전투자",
            "base_url": "https://openapi.kiwoom.com:9443",
            "api_key": os.getenv("KIWOOM_PROD_API_KEY"),
            "api_secret": os.getenv("KIWOOM_PROD_API_SECRET"),
        }

# 초기화: 모듈 로드 시 설정과 환경변수 로드
CONFIG = load_config()
load_env_vars()

# if __name__ == '__main__':
#     # 테스트용 로깅 핸들러 설정
#     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#     
#     print("--- 설정 파일 내용 ---")
#     print(CONFIG)
#     
#     print("\n--- 키움 투자 환경 ---")
#     kiwoom_settings = get_kiwoom_env()
#     print(f"투자 환경: {kiwoom_settings['env_type']}")
#     print(f"Base URL: {kiwoom_settings['base_url']}")
#     print(f"API Key: {'설정됨' if kiwoom_settings['api_key'] else '미설정'}")
#     print(f"API Secret: {'설정됨' if kiwoom_settings['api_secret'] else '미설정'}")