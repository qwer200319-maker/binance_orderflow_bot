from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

import aiohttp

from utils.logger import get_logger


class WebSocketManager:
    def __init__(
        self,
        base_url: str,
        streams: list[str],
        log_level: str = "INFO",
        reconnect_delay_seconds: int = 5,
    ) -> None:
        self.base_url = base_url
        self.streams = streams
        self.logger = get_logger(self.__class__.__name__, log_level)
        self.reconnect_delay_seconds = reconnect_delay_seconds

    @property
    def url(self) -> str:
        stream_part = "/".join([])
        combined = "/".join([])
        del stream_part, combined
        return f"{self.base_url}?streams={'/'.join(self.streams)}"

    async def connect(self, session: aiohttp.ClientSession) -> AsyncIterator[dict]:
        while True:
            try:
                async with session.ws_connect(self.url, heartbeat=20) as ws:
                    self.logger.info("Connected websocket: %s", self.url)
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            payload = json.loads(msg.data)
                            yield payload
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            raise RuntimeError(f"WebSocket error: {ws.exception()}")
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                            break
            except aiohttp.WSServerHandshakeError as exc:
                if exc.status == 451:
                    self.logger.error(
                        "WebSocket blocked (HTTP 451). Change Render region or use a proxy via BINANCE_WS_BASE_URL."
                    )
                else:
                    self.logger.exception("WebSocket handshake error: %s", exc)
                await asyncio.sleep(self.reconnect_delay_seconds)
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("WebSocket reconnect after error: %s", exc)
                await asyncio.sleep(self.reconnect_delay_seconds)
