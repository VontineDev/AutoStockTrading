import requests
import logging
from typing import Optional

# 프로젝트 루트를 sys.path에 추가
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config_loader import get_kiwoom_env

logger = logging.getLogger(__name__)


def get_access_token(
    API_KEY: str,
    API_SECRET: str,
    base_url: str = "https://api.kiwoom.com",
    timeout: int = 30,
) -> Optional[str]:
    """
    키움 REST API 접근 토큰 발급
    """
    url = f"{base_url}/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": API_KEY,
        "secretkey": API_SECRET,
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        if result.get("token"):
            logging.info(f"토큰 발급 성공: {result['token']}")
            return result["token"]
        else:
            logging.error(f"토큰 발급 실패: {result}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"토큰 발급 요청 오류: {e}")
        return None


def revoke_access_token(
    API_KEY: str,
    API_SECRET: str,
    access_token: str,
    base_url: str = "https://api.kiwoom.com",
    timeout: int = 30,
) -> bool:
    """
    키움 REST API 접근 토큰 폐기
    """
    url = f"{base_url}/oauth2/revoke"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {"appkey": API_KEY, "secretkey": API_SECRET, "token": access_token}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        if result.get("return_code") == 0:
            logging.info("토큰 폐기 성공")
            return True
        else:
            logging.error(f"토큰 폐기 실패: {result}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"토큰 폐기 요청 오류: {e}")
        return False


if __name__ == "__main__":
    kiwoom_env = get_kiwoom_env()
    token = get_access_token(
        kiwoom_env["api_key"], kiwoom_env["api_secret"], base_url=kiwoom_env["base_url"]
    )
    if token:
        logging.info(f"발급된 토큰: {token}")
        # 테스트용으로 바로 폐기
        revoke_access_token(kiwoom_env["api_key"], kiwoom_env["api_secret"], token)
