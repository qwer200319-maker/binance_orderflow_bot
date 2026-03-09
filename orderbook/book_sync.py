from __future__ import annotations

from collections import deque
from typing import Deque, List

from orderbook.local_book import LocalBook
from utils.logger import get_logger


class BookSynchronizer:
    def __init__(self, book: LocalBook, log_level: str = "INFO") -> None:
        self.book = book
        self.buffer: Deque[dict] = deque()
        self.is_ready: bool = False
        self.last_u: int | None = None
        self.logger = get_logger(self.__class__.__name__, log_level)

    def reset(self) -> None:
        self.logger.warning(
            "Resetting book sync. buffer=%s last_u=%s",
            len(self.buffer),
            self.last_u,
        )
        self.buffer.clear()
        self.is_ready = False
        self.last_u = None
        self.book.clear()

    def buffer_event(self, event: dict) -> None:
        self.buffer.append(event)
        self.logger.debug(
            "Buffered depth event U=%s u=%s pu=%s buffer=%s",
            event.get("U"),
            event.get("u"),
            event.get("pu"),
            len(self.buffer),
        )

    def initialize_from_snapshot(self, snapshot: dict) -> None:
        self.book.load_snapshot(snapshot)
        last_update_id = int(snapshot["lastUpdateId"])
        buffer_before = len(self.buffer)

        trimmed = 0
        while self.buffer and int(self.buffer[0]["u"]) < last_update_id:
            self.buffer.popleft()
            trimmed += 1
        self.logger.debug(
            "Snapshot init lastUpdateId=%s buffer_before=%s trimmed=%s buffer_after=%s",
            last_update_id,
            buffer_before,
            trimmed,
            len(self.buffer),
        )

        first_match_found = False
        remaining: List[dict] = []
        for event in list(self.buffer):
            u = int(event["u"])
            U = int(event["U"])
            if not first_match_found:
                if U <= last_update_id <= u:
                    self._apply_event(event)
                    first_match_found = True
                else:
                    self.logger.debug(
                        "Skipping buffered event for initial match U=%s u=%s lastUpdateId=%s",
                        U,
                        u,
                        last_update_id,
                    )
                continue
            remaining.append(event)

        if not first_match_found:
            self.logger.warning(
                "No matching buffered event found for snapshot lastUpdateId=%s buffer_after=%s",
                last_update_id,
                len(self.buffer),
            )
            self.is_ready = False
            return

        for event in remaining:
            if not self._process_ready_event(event):
                self.logger.warning(
                    "Sequence mismatch while draining buffer. last_u=%s event_u=%s event_pu=%s",
                    self.last_u,
                    event.get("u"),
                    event.get("pu"),
                )
                return

        self.buffer.clear()
        self.is_ready = True
        self.logger.info(
            "Book sync ready. last_u=%s buffer_drained=%s",
            self.last_u,
            len(remaining),
        )

    def process_event(self, event: dict) -> bool:
        if not self.is_ready:
            self.buffer_event(event)
            return False
        return self._process_ready_event(event)

    def _process_ready_event(self, event: dict) -> bool:
        if self.last_u is not None and int(event.get("pu", -1)) != self.last_u:
            self.logger.warning(
                "Sequence mismatch pu=%s expected=%s u=%s",
                event.get("pu"),
                self.last_u,
                event.get("u"),
            )
            self.reset()
            return False
        self._apply_event(event)
        return True

    def _apply_event(self, event: dict) -> None:
        self.book.apply_update(event.get("b", []), event.get("a", []), int(event["u"]))
        self.last_u = int(event["u"])
