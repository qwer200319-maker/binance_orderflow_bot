from __future__ import annotations

import aiohttp


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str, enabled: bool = False) -> None:
        self.token = token
        self.chat_id = chat_id
        self.enabled = enabled and bool(token) and bool(chat_id)

    async def send_message(self, session: aiohttp.ClientSession, text: str) -> None:
        if not self.enabled:
            return
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
