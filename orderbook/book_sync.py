from __future__ import annotations

from collections import deque
import time
from typing import Deque, List

from orderbook.local_book import LocalBook
from utils.logger import get_logger


class BookSynchronizer:
    def __init__(
        self,
        book: LocalBook,
        log_level: str = "INFO",
        buffer_log_interval_sec: float = 5.0,
        no_match_warn_interval_sec: float = 30.0,
    ) -> None:
        self.book = book
        self.buffer: Deque[dict] = deque()
        self.is_ready: bool = False
        self.last_u: int | None = None
        self.snapshot_last_update_id: int | None = None
        self.logger = get_logger(self.__class__.__name__, log_level)
        self._last_buffer_log_ts: float | None = None
        self._buffer_log_interval_sec: float = buffer_log_interval_sec
        self._last_no_match_warn_ts: float | None = None
        self._no_match_warn_interval_sec: float = no_match_warn_interval_sec

    def reset(self) -> None:
        self.logger.warning(
            "Resetting book sync. buffer=%s last_u=%s",
            len(self.buffer),
            self.last_u,
        )
        self.buffer.clear()
        self.is_ready = False
        self.last_u = None
        self.snapshot_last_update_id = None
        self.book.clear()

    def buffer_event(self, event: dict) -> None:
        self.buffer.append(event)
        self._maybe_log_buffer(event)

    def buffer_age_seconds(self) -> float:
        if not self.buffer:
            return 0.0
        first = self.buffer[0]
        last = self.buffer[-1]
        try:
            return max((float(last.get("event_time", 0)) - float(first.get("event_time", 0))) / 1000.0, 0.0)
        except Exception:  # noqa: BLE001
            return 0.0

    def buffer_summary(self) -> str:
        if not self.buffer:
            return "buffer=0"
        first = self.buffer[0]
        last = self.buffer[-1]
        return (
            f"buffer={len(self.buffer)} "
            f"U0={first.get('U')} u0={first.get('u')} "
            f"U1={last.get('U')} u1={last.get('u')} "
            f"age={self.buffer_age_seconds():.3f}s"
        )

    def buffer_len(self) -> int:
        return len(self.buffer)

    def _maybe_log_buffer(self, event: dict) -> None:
        if not self.logger.isEnabledFor(10):
            return
        if self._buffer_log_interval_sec <= 0:
            self.logger.debug(
                "Buffered depth event U=%s u=%s pu=%s %s",
                event.get("U"),
                event.get("u"),
                event.get("pu"),
                self.buffer_summary(),
            )
            return
        now = time.time()
        if self._last_buffer_log_ts is not None and now - self._last_buffer_log_ts < self._buffer_log_interval_sec:
            return
        self._last_buffer_log_ts = now
        self.logger.debug(
            "Buffered depth event U=%s u=%s pu=%s %s",
            event.get("U"),
            event.get("u"),
            event.get("pu"),
            self.buffer_summary(),
        )
    def initialize_from_snapshot(self, snapshot: dict) -> None:
        self.book.load_snapshot(snapshot)
        self.snapshot_last_update_id = int(snapshot["lastUpdateId"])
        self._finalize_from_buffer(snapshot_init=True)

    def try_finalize(self) -> bool:
        if self.snapshot_last_update_id is None:
            return False
        return self._finalize_from_buffer(snapshot_init=False)

    def needs_snapshot_refresh(self) -> bool:
        if self.snapshot_last_update_id is None or not self.buffer:
            return False
        first_u = int(self.buffer[0].get("U", 0))
        return first_u > (self.snapshot_last_update_id + 1)

    def process_event(self, event: dict) -> bool:
        if not self.is_ready:
            self.buffer_event(event)
            if self.try_finalize():
                return True
            return False
        return self._process_ready_event(event)

    def _finalize_from_buffer(self, snapshot_init: bool) -> bool:
        last_update_id = self.snapshot_last_update_id
        if last_update_id is None:
            return False

        buffer_before = len(self.buffer)
        trimmed = 0
        while self.buffer and int(self.buffer[0]["u"]) <= last_update_id:
            self.buffer.popleft()
            trimmed += 1

        if snapshot_init or trimmed or buffer_before:
            self.logger.debug(
                "Snapshot init lastUpdateId=%s buffer_before=%s trimmed=%s buffer_after=%s %s",
                last_update_id,
                buffer_before,
                trimmed,
                len(self.buffer),
                self.buffer_summary(),
            )

        first_match_found = False
        remaining: List[dict] = []
        for event in list(self.buffer):
            u = int(event["u"])
            U = int(event["U"])
            if not first_match_found:
                if U <= last_update_id + 1 <= u:
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
            if not self.buffer:
                self.logger.debug(
                    "No buffered events yet for snapshot lastUpdateId=%s",
                    last_update_id,
                )
            else:
                now = time.time()
                if self._no_match_warn_interval_sec <= 0:
                    first = self.buffer[0]
                    self.logger.warning(
                        "No matching buffered event found for snapshot lastUpdateId=%s buffer_after=%s U0=%s u0=%s",
                        last_update_id,
                        len(self.buffer),
                        first.get("U"),
                        first.get("u"),
                    )
                    self.is_ready = False
                    return False
                if (
                    self._last_no_match_warn_ts is None
                    or now - self._last_no_match_warn_ts >= self._no_match_warn_interval_sec
                ):
                    self._last_no_match_warn_ts = now
                    first = self.buffer[0]
                    self.logger.warning(
                        "No matching buffered event found for snapshot lastUpdateId=%s buffer_after=%s U0=%s u0=%s",
                        last_update_id,
                        len(self.buffer),
                        first.get("U"),
                        first.get("u"),
                    )
                else:
                    self.logger.debug(
                        "No matching buffered event (throttled) lastUpdateId=%s %s",
                        last_update_id,
                        self.buffer_summary(),
                    )
            self.is_ready = False
            return False

        for event in remaining:
            if not self._process_ready_event(event):
                self.logger.warning(
                    "Sequence mismatch while draining buffer. last_u=%s event_u=%s event_pu=%s",
                    self.last_u,
                    event.get("u"),
                    event.get("pu"),
                )
                return False

        self.buffer.clear()
        self.is_ready = True
        self.logger.info(
            "Book sync ready. last_u=%s buffer_drained=%s",
            self.last_u,
            len(remaining),
        )
        return True

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
