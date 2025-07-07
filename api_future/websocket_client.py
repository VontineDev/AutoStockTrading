import logging
from typing import Any, Callable, List, Optional, Dict
import asyncio
import json
import websockets
import os
from src.api.auth import get_access_token, API_KEY, API_SECRET
import inspect

class WebSocketClient:
    """
    키움증권 실시간시세 WebSocket 클라이언트
    다양한 TR명(주문체결, 잔고, 주식체결 등) 구독 지원
    """
    def __init__(
        self,
        url: str,
        access_token: str,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.url = url
        self.access_token = access_token
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.keep_running = True
        self.logger = logging.getLogger(self.__class__.__name__)
        self.on_message = on_message

    async def connect(self) -> None:
        """웹소켓 서버에 연결 및 로그인 패킷 전송"""
        try:
            self.websocket = await websockets.connect(self.url)
            self.connected = True
            self.logger.info(f"웹소켓 서버 연결: {self.url}")
            # 로그인 패킷 전송
            login_msg = {"trnm": "LOGIN", "token": self.access_token}
            await self.send_message(login_msg)
        except Exception as e:
            self.logger.error(f"웹소켓 연결 실패: {e}")
            self.connected = False

    async def send_message(self, message: Any) -> None:
        """메시지 전송 (자동 직렬화)"""
        if not self.connected or not self.websocket:
            await self.connect()
        if self.connected and self.websocket:
            if not isinstance(message, str):
                message = json.dumps(message)
            await self.websocket.send(message)
            self.logger.debug(f"메시지 전송: {message}")

    async def receive_messages(self) -> None:
        """서버로부터 메시지 수신 및 처리 루프"""
        while self.keep_running and self.websocket:
            try:
                raw = await self.websocket.recv()
                response = json.loads(raw)
                trnm = response.get("trnm")
                # 로그인 결과 처리
                if trnm == "LOGIN":
                    if response.get("return_code") != 0:
                        self.logger.error(f"웹소켓 로그인 실패: {response.get('return_msg')}")
                        await self.disconnect()
                    else:
                        self.logger.info("웹소켓 로그인 성공")
                # PING 처리
                elif trnm == "PING":
                    await self.send_message(response)
                # 실시간 데이터/응답 처리
                else:
                    self.logger.debug(f"실시간 데이터 수신: {response}")
                    if self.on_message:
                        if inspect.iscoroutinefunction(self.on_message):
                            await self.on_message(response)
                        else:
                            self.on_message(response)
            except websockets.ConnectionClosed:
                self.logger.warning("웹소켓 서버에서 연결 종료")
                self.connected = False
                break
            except Exception as e:
                self.logger.error(f"메시지 수신 오류: {e}")
                break

    async def subscribe(self, tr_types: List[str], items: Optional[List[str]] = None, grp_no: str = "1", refresh: str = "1") -> None:
        """
        실시간 항목 구독 요청 (REG)
        문서 예시와 동일하게 REG 메시지 생성 후 send_message 호출
        """
        data = [{
            'item': items or [""],
            'type': tr_types
        }]
        reg_msg = {
            'trnm': 'REG',
            'grp_no': grp_no,
            'refresh': refresh,
            'data': data
        }
        await self.send_message(reg_msg)
        self.logger.info(f"실시간 구독 요청: {reg_msg}")

    async def unsubscribe(self, tr_types: List[str], items: Optional[List[str]] = None, grp_no: str = "1") -> None:
        """
        실시간 항목 구독 해지 요청 (REMOVE)
        """
        data = [{
            "item": items or [""],
            "type": tr_types
        }]
        remove_msg = {
            "trnm": "REMOVE",
            "grp_no": grp_no,
            "data": data
        }
        await self.send_message(remove_msg)
        self.logger.info(f"실시간 구독 해지 요청: {remove_msg}")

    async def run(self, tr_types: List[str], items: Optional[List[str]] = None) -> None:
        """
        웹소켓 연결 및 실시간 구독, 메시지 수신 루프 실행
        """
        await self.connect()
        await asyncio.sleep(1)  # 연결 후 구독 요청 대기
        await self.subscribe(tr_types, items)
        await self.receive_messages()

    async def disconnect(self) -> None:
        self.keep_running = False
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            self.logger.info("웹소켓 연결 종료")

    def set_on_message(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.on_message = callback

if __name__ == "__main__":
    import os
    import logging
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def print_message(msg):
        # 주식체결(0B) 실시간 데이터 구조 파싱 예시
        if msg.get("trnm") == "REAL" and msg.get("data"):
            for entry in msg["data"]:
                if entry.get("type") == "0B":  # 주식체결
                    values = entry.get("values", {})
                    price = values.get("10", "")  # 현재가
                    volume = values.get("13", "")  # 누적거래량
                    print(f"[주식체결] 현재가: {price} | 누적거래량: {volume}")
        else:
            print("[실시간 데이터]", msg)

    async def main():
        token = os.getenv("KIWOOM_API_ACCESS_TOKEN")
        if not token:
            # 환경변수 없으면 직접 발급
            token = get_access_token(API_KEY, API_SECRET)
            if not token:
                print("[ERROR] 토큰 발급 실패. 환경변수 및 네트워크 상태를 확인하세요.")
                return
            print(f"[INFO] 발급된 토큰: {token}")
        ws_url = "wss://api.kiwoom.com:10000/api/dostk/websocket"
        client = WebSocketClient(ws_url, token, on_message=print_message)
        await client.run(["0B"], ["005930"])  # 삼성전자 주식체결 실시간 구독

    asyncio.run(main()) 