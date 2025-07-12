import os
import sys
import requests
import logging
from dotenv import load_dotenv
from typing import Optional

try:
    import streamlit as st

    STREAMLIT_MODE = True
except ImportError:
    STREAMLIT_MODE = False

load_dotenv()


def get_kiwoom_env():
    """
    실전/모의투자 환경에 따라 API 키, 시크릿, 계좌번호, API URL을 반환
    - Streamlit 환경이면 st.session_state['USE_KIWOOM_MOCK'] 우선 적용
    - 환경변수 USE_KIWOOM_MOCK이 '1' 또는 'true'면 모의투자, 아니면 실전투자
    - 각각의 url은 KIWOOM_API_BASE_URL, KIWOOM_MOCK_API_BASE_URL에서 읽음(없으면 기본값)
    """
    use_mock = False
    if (
        STREAMLIT_MODE
        and hasattr(st, "session_state")
        and "USE_KIWOOM_MOCK" in st.session_state
    ):
        use_mock = st.session_state["USE_KIWOOM_MOCK"]
    else:
        use_mock = os.getenv("USE_KIWOOM_MOCK", "0").lower() in ("1", "true", "yes")
    if use_mock:
        api_key = os.getenv("KIWOOM_MOCK_API_KEY")
        api_secret = os.getenv("KIWOOM_MOCK_API_SECRET")
        account = os.getenv("KIWOOM_MOCK_ACCOUNT")
        base_url = os.getenv("KIWOOM_MOCK_API_BASE_URL", "https://mockapi.kiwoom.com")
        env_type = "모의투자"
    else:
        api_key = os.getenv("KIWOOM_API_KEY")
        api_secret = os.getenv("KIWOOM_API_SECRET")
        account = os.getenv("KIWOOM_ACCOUNT")
        base_url = os.getenv("KIWOOM_API_BASE_URL", "https://api.kiwoom.com")
        env_type = "실전투자"
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "account": account,
        "base_url": base_url,
        "env_type": env_type,
    }


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/auth.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


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
