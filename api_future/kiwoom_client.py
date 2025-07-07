import logging
from typing import Optional, Dict, Any
import requests

class KiwoomApiClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_account_info(self, access_token: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        키움 REST API 계좌평가현황요청(kt00004)
        """
        url = "https://api.kiwoom.com/api/dostk/acnt"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {access_token}",
            "api-id": "kt00004",
            "cont-yn": "N",
            "next-key": ""
        }
        data = {
            "qry_tp": "0",  # 0:전체, 1:상장폐지종목제외
            "dmst_stex_tp": "KRX"  # KRX:한국거래소, NXT:넥스트트레이드
        }
        try:
            self.logger.info("계좌평가현황요청(kt00004) API 호출")
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
            response.raise_for_status()
            result = response.json()
            self.logger.info(f"계좌 정보 조회 성공: {result}")
            return result
        except requests.exceptions.RequestException as e:
            self.logger.error(f"계좌 정보 조회 실패: {e}")
            return None

if __name__ == "__main__":
    import os
    import sys
    from src.api.auth import get_access_token, API_KEY, API_SECRET

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/kiwoom_client.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    client = KiwoomApiClient(API_KEY, API_SECRET)
    token = get_access_token(API_KEY, API_SECRET)
    if not token:
        print("[ERROR] 토큰 발급 실패. 환경변수 및 네트워크 상태를 확인하세요.")
        sys.exit(1)
    account_info = client.get_account_info(token)
    if account_info:
        print("[SUCCESS] 계좌 정보:")
        print(account_info)
    else:
        print("[ERROR] 계좌 정보 조회 실패.") 