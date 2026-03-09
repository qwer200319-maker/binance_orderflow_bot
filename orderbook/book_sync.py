from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List

from orderbook.local_book import LocalBook


class BookSynchronizer:
    def __init__(self, book: LocalBook) -> None:
        self.book = book
        self.buffer: Deque[dict] = deque()
        self.is_ready: bool = False
        self.last_u: int | None = None

    def reset(self) -> None:
        self.buffer.clear()
        self.is_ready = False
        self.last_u = None
        self.book.clear()

    def buffer_event(self, event: dict) -> None:
        self.buffer.append(event)

    def initialize_from_snapshot(self, snapshot: dict) -> None:
        self.book.load_snapshot(snapshot)
        last_update_id = int(snapshot["lastUpdateId"])

        while self.buffer and int(self.buffer[0]["u"]) < last_update_id:
            self.buffer.popleft()

        first_match_found = False
        remaining: List[dict] = []
        for event in list(self.buffer):
            u = int(event["u"])
            U = int(event["U"])
            if not first_match_found:
                if U <= last_update_id <= u:
                    self._apply_event(event)
                    first_match_found = True
                continue
            remaining.append(event)

        if not first_match_found:
            self.is_ready = False
            return

        for event in remaining:
            self._process_ready_event(event)

        self.buffer.clear()
        self.is_ready = True

    def process_event(self, event: dict) -> bool:
        if not self.is_ready:
            self.buffer_event(event)
            return False
        return self._process_ready_event(event)

    def _process_ready_event(self, event: dict) -> bool:
        if self.last_u is not None and int(event.get("pu", -1)) != self.last_u:
            self.reset()
            return False
        self._apply_event(event)
        return True

    def _apply_event(self, event: dict) -> None:
        self.book.apply_update(event.get("b", []), event.get("a", []), int(event["u"]))
        self.last_u = int(event["u"])
