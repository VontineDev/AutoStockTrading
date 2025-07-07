import os
import sys
import requests
import logging
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

API_KEY = os.getenv("KIWOOM_API_KEY")
API_SECRET = os.getenv("KIWOOM_API_SECRET")

if not API_KEY or not API_SECRET:
    logging.basicConfig(level=logging.INFO)
    logging.error("환경변수 KIWOOM_API_KEY, KIWOOM_API_SECRET이 설정되어 있지 않습니다.\n"
                  "1) 프로젝트 루트에 .env 파일을 생성하세요.\n"
                  "2) .env.example 파일을 참고해 실제 값을 입력하세요.\n"
                  "3) 예시: KIWOOM_API_KEY=your_API_KEY_here\n")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/auth.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_access_token(API_KEY: str, API_SECRET: str, timeout: int = 30) -> Optional[str]:
    """
    키움 REST API 접근 토큰 발급
    """
    url = "https://api.kiwoom.com/oauth2/token"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "grant_type": "client_credentials",
        "appkey": API_KEY,
        "secretkey": API_SECRET
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

def revoke_access_token(API_KEY: str, API_SECRET: str, access_token: str, timeout: int = 30) -> bool:
    """
    키움 REST API 접근 토큰 폐기
    """
    url = "https://api.kiwoom.com/oauth2/revoke"
    headers = {"Content-Type": "application/json;charset=UTF-8"}
    data = {
        "appkey": API_KEY,
        "secretkey": API_SECRET,
        "token": access_token
    }
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
    token = get_access_token(API_KEY, API_SECRET)
    if token:
        logging.info(f"발급된 토큰: {token}")
        # 테스트용으로 바로 폐기
        revoke_access_token(API_KEY, API_SECRET, token)
