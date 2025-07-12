import logging
from typing import Any, Callable, List, Optional, Dict
import asyncio
import json
import websockets
import os
from src.utils.logging_utils import log_function_trace


class WebSocketClient:
    """
    키움증권 실시간시세 WebSocket 클라이언트
    다양한 TR명(주문체결, 잔고, 주식체결 등) 구독 지원
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.ws = None
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None

    @log_function_trace
    async def connect(self) -> None:
        kiwoom_env = get_kiwoom_env()
        token = get_access_token(
            kiwoom_env["api_key"],
            kiwoom_env["api_secret"],
            base_url=kiwoom_env["base_url"],
        )
        if not token:
            self.logger.error("토큰 발급 실패. 환경변수 및 네트워크 상태를 확인하세요.")
            return
        url = f"wss://openapi.kiwoom.com/ws"  # 실제 URL은 키움 가이드에 맞게 수정 필요
        self.ws = await websockets.connect(
            url, extra_headers={"authorization": f"Bearer {token}"}
        )
        self.logger.info("WebSocket 연결 성공")

    @log_function_trace
    async def send_message(self, message: Any) -> None:
        if self.ws:
            await self.ws.send(json.dumps(message))
            self.logger.info(f"메시지 전송: {message}")

    async def receive_messages(self) -> None:
        if self.ws:
            async for msg in self.ws:
                data = json.loads(msg)
                self.logger.info(f"수신 메시지: {data}")
                if self.on_message:
                    self.on_message(data)

    @log_function_trace
    async def subscribe(
        self,
        tr_types: List[str],
        items: Optional[List[str]] = None,
        grp_no: str = "1",
        refresh: str = "1",
    ) -> None:
        # 구독 메시지 포맷은 키움 가이드 참고
        message = {
            "tr_type": tr_types,
            "items": items or [],
            "grp_no": grp_no,
            "refresh": refresh,
        }
        await self.send_message(message)

    @log_function_trace
    async def unsubscribe(
        self, tr_types: List[str], items: Optional[List[str]] = None, grp_no: str = "1"
    ) -> None:
        # 해제 메시지 포맷은 키움 가이드 참고
        message = {
            "tr_type": tr_types,
            "items": items or [],
            "grp_no": grp_no,
            "unsubscribe": True,
        }
        await self.send_message(message)

    @log_function_trace
    async def run(self, tr_types: List[str], items: Optional[List[str]] = None) -> None:
        await self.connect()
        await self.subscribe(tr_types, items)
        await self.receive_messages()

    async def disconnect(self) -> None:
        if self.ws:
            await self.ws.close()
            self.logger.info("WebSocket 연결 종료")

    def set_on_message(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.on_message = callback


if __name__ == "__main__":
    import os
    import logging
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/websocket_client.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    async def print_message(msg):
        print("[RECV]", msg)

    async def main():
        client = WebSocketClient()
        client.set_on_message(print_message)
        await client.connect()
        # 예시: 실시간 시세 구독 (tr_types, items는 실제 사용에 맞게 수정)
        await client.subscribe(["stock_price"], ["005930"])  # 삼성전자 예시
        await client.receive_messages()

    asyncio.run(main())
