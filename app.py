from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict

import aiohttp
from dotenv import load_dotenv

from config import RAW_EVENTS_DIR, STORAGE_DIR, settings
from feeds.depth_stream import parse_depth_message
from feeds.liquidation_stream import parse_force_order_message
from feeds.oi_funding_loader import fetch_funding_rate, fetch_open_interest
from feeds.snapshot_loader import fetch_depth_snapshot
from feeds.trade_stream import parse_agg_trade_message
from feeds.ws_manager import WebSocketManager
from flow.absorption import detect_absorption
from flow.cvd import CVDTracker
from flow.divergence import detect_bullish_divergence, detect_bearish_divergence
from flow.liquidation_map import LiquidationMap
from flow.spoofing import summarize_spoofing
from flow.trades_buffer import TradesBuffer
from notifier.telegram import TelegramNotifier
from orderbook.book_features import build_book_snapshot
from orderbook.book_sync import BookSynchronizer
from orderbook.local_book import LocalBook
from orderbook.wall_tracker import WallTracker
from risk.filters import signal_allowed
from risk.sltp import build_trade_plan
from strategy.signal_formatter import format_signal
from strategy.signal_rules import decide_signal
from utils.json_store import JsonLineStore, JsonStore
from utils.logger import get_logger
from utils.math_utils import mean
from utils.time_utils import iso_utc, now_ts


class BotApp:
    def __init__(self) -> None:
        self.logger = get_logger("BotApp", settings.log_level)
        self.book = LocalBook()
        self.book_sync = BookSynchronizer(self.book, settings.log_level)
        self.wall_tracker = WallTracker()
        self.trades_buffer = TradesBuffer(max_age_seconds=900)
        self.cvd = CVDTracker()
        self.liquidations = LiquidationMap(max_age_seconds=900)
        self.ws_manager = WebSocketManager(
            settings.ws_base_url,
            settings.streams,
            settings.log_level,
            settings.reconnect_delay_seconds,
        )
        self.telegram = TelegramNotifier(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            settings.telegram_enabled,
        )

        self.feature_store = JsonLineStore(STORAGE_DIR / "features.jsonl")
        self.signal_store = JsonLineStore(STORAGE_DIR / "signals.jsonl")
        self.state_store = JsonStore(STORAGE_DIR / "state.json")

        self.current_open_interest: float = 0.0
        self.previous_open_interest: float = 0.0
        self.current_funding_rate: float = 0.0
        self.last_snapshot_ts: float = 0.0
        self.last_signal_ts: float | None = None
        self.last_feature_payload: Dict[str, Any] = {}
        self.running = True

    async def initialize(self, session: aiohttp.ClientSession) -> None:
        while self.running:
            ok = await self.refresh_snapshot(session)
            if ok:
                break
            await asyncio.sleep(settings.reconnect_delay_seconds)
        await self.refresh_oi(session)
        await self.refresh_funding(session)
        self.persist_state()

    async def refresh_snapshot(self, session: aiohttp.ClientSession) -> bool:
        try:
            snapshot = await fetch_depth_snapshot(
                session, settings.rest_base_url, settings.market_symbol, settings.depth_limit
            )
        except aiohttp.ClientResponseError as exc:
            if exc.status == 451:
                self.logger.error(
                    "Snapshot blocked (HTTP 451). This usually means the Binance API is blocked from your hosting "
                    "region. Change Render region or use a proxy via BINANCE_REST_BASE_URL."
                )
                return False
            raise
        self.book_sync.initialize_from_snapshot(snapshot)
        self.last_snapshot_ts = now_ts()
        self.logger.info(
            "Loaded snapshot lastUpdateId=%s ready=%s %s",
            snapshot.get("lastUpdateId"),
            self.book_sync.is_ready,
            self.book_sync.buffer_summary(),
        )
        return True

    async def refresh_oi(self, session: aiohttp.ClientSession) -> bool:
        try:
            oi = await fetch_open_interest(session, settings.rest_base_url, settings.market_symbol)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 451:
                self.logger.error(
                    "Open interest blocked (HTTP 451). Change Render region or use a proxy."
                )
                return False
            raise
        self.previous_open_interest = self.current_open_interest or oi
        self.current_open_interest = oi
        return True

    async def refresh_funding(self, session: aiohttp.ClientSession) -> bool:
        try:
            self.current_funding_rate = await fetch_funding_rate(
                session, settings.rest_base_url, settings.market_symbol
            )
        except aiohttp.ClientResponseError as exc:
            if exc.status == 451:
                self.logger.error(
                    "Funding rate blocked (HTTP 451). Change Render region or use a proxy."
                )
                return False
            raise
        return True

    async def periodic_rest_tasks(self, session: aiohttp.ClientSession) -> None:
        last_oi_refresh = 0.0
        last_funding_refresh = 0.0
        while self.running:
            now = now_ts()
            try:
                if now - last_oi_refresh >= settings.oi_poll_seconds:
                    if await self.refresh_oi(session):
                        last_oi_refresh = now
                if now - last_funding_refresh >= settings.funding_poll_seconds:
                    if await self.refresh_funding(session):
                        last_funding_refresh = now
                if now - self.last_snapshot_ts >= settings.snapshot_refresh_seconds:
                    await self.refresh_snapshot(session)
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("REST task error: %s", exc)
            await asyncio.sleep(1)

    async def consume_ws(self, session: aiohttp.ClientSession) -> None:
        async for envelope in self.ws_manager.connect(session):
            data = envelope.get("data", envelope)
            stream = envelope.get("stream", "")
            if settings.persist_raw_events:
                self.persist_raw_event(stream or data.get("e", "unknown"), envelope)

            event_type = data.get("e")
            if event_type == "depthUpdate":
                await self.handle_depth_event(parse_depth_message(data), session)
            elif event_type == "aggTrade":
                self.handle_trade_event(parse_agg_trade_message(data))
            elif event_type == "forceOrder":
                self.handle_liquidation_event(parse_force_order_message(data))

    async def handle_depth_event(self, event: dict, session: aiohttp.ClientSession) -> None:
        if not self.book_sync.is_ready:
            self.book_sync.buffer_event(event)
            if self.book.last_update_id is None:
                try:
                    await self.refresh_snapshot(session)
                except Exception as exc:  # noqa: BLE001
                    self.logger.exception("Snapshot refresh failed during bootstrap: %s", exc)
            return

        ok = self.book_sync.process_event(event)
        if not ok:
            if self.book_sync.needs_snapshot_refresh():
                now = now_ts()
                if now - self.last_snapshot_ts >= 5:
                    self.logger.warning(
                        "Order book snapshot is behind buffered events. Refreshing snapshot... %s",
                        self.book_sync.buffer_summary(),
                    )
                    await self.refresh_snapshot(session)
            return

        book_snapshot = build_book_snapshot(self.book)
        bid_walls = book_snapshot.get("bid_walls", [])
        ask_walls = book_snapshot.get("ask_walls", [])
        self.wall_tracker.observe(
            "bid",
            bid_walls,
            now_ts(),
            self.book.best_bid(),
            self.book.best_ask(),
        )
        self.wall_tracker.observe(
            "ask",
            ask_walls,
            now_ts(),
            self.book.best_bid(),
            self.book.best_ask(),
        )

    def handle_trade_event(self, trade: dict) -> None:
        self.trades_buffer.add_trade(trade)
        self.cvd.update_from_trade(trade)

    def handle_liquidation_event(self, liq: dict) -> None:
        self.liquidations.add(liq)

    def compute_price_change(self, window_sec: int) -> float:
        now = now_ts()
        prices = [p for p in self.trades_buffer.prices if now - p["ts"] <= window_sec]
        if len(prices) < 2:
            return 0.0
        return prices[-1]["price"] - prices[0]["price"]

    def compute_micro_atr(self, max_points: int = 100) -> float:
        prices = [p["price"] for p in list(self.trades_buffer.prices)[-max_points:]]
        if len(prices) < 2:
            return settings.default_tick_size * 10
        diffs = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
        return max(mean(diffs), settings.default_tick_size * 5)

    def compute_bid_ask_avg_qty(self) -> tuple[float, float]:
        top_bids = self.book.top_bids(settings.top_levels)
        top_asks = self.book.top_asks(settings.top_levels)
        bid_avg = mean(qty for _, qty in top_bids)
        ask_avg = mean(qty for _, qty in top_asks)
        return bid_avg, ask_avg

    def build_feature_snapshot(self) -> Dict[str, Any]:
        now = now_ts()
        self.trades_buffer.trim(now)
        self.cvd.trim(now, max_age=900)
        self.liquidations.trim(now)

        book_snapshot = build_book_snapshot(self.book)
        price_change = self.compute_price_change(settings.price_change_window_seconds)
        delta_15s = self.cvd.window_delta(now, settings.delta_window_seconds)
        cvd_change = self.cvd.window_delta(now, settings.cvd_window_seconds)
        oi_change = self.current_open_interest - self.previous_open_interest
        tick_size = settings.default_tick_size
        price_move_ticks = price_change / tick_size if tick_size > 0 else 0.0

        bid_persistence_count = len(book_snapshot.get("bid_walls", []))
        ask_persistence_count = len(book_snapshot.get("ask_walls", []))
        bullish_absorption, bearish_absorption = detect_absorption(
            delta_15s=delta_15s,
            price_move_ticks=price_move_ticks,
            bid_persistence_count=bid_persistence_count,
            ask_persistence_count=ask_persistence_count,
            delta_threshold=settings.absorption_delta_threshold,
            max_price_move_ticks=settings.absorption_max_price_move_ticks,
            min_persistence=settings.absorption_persistence_levels,
        )

        bid_avg_qty, ask_avg_qty = self.compute_bid_ask_avg_qty()
        spoof_summary = summarize_spoofing(
            self.wall_tracker.get_recent(),
            bid_avg_qty,
            ask_avg_qty,
            settings.spoof_min_size_multiplier,
            settings.spoof_lifetime_ms,
            settings.spoof_max_execution_ratio,
        )

        liq_summary = self.liquidations.summarize(
            now,
            settings.liq_cluster_window_sec,
            settings.liq_price_bin,
            settings.liq_min_cluster_count,
        )

        features: Dict[str, Any] = {
            "ts": iso_utc(now),
            "mid_price": book_snapshot["mid_price"],
            "spread": book_snapshot["spread"],
            "imbalance": book_snapshot["imbalance"],
            "cvd": self.cvd.value,
            "delta_15s": delta_15s,
            "price_change": price_change,
            "price_move_ticks": price_move_ticks,
            "funding_rate": self.current_funding_rate,
            "open_interest": self.current_open_interest,
            "oi_change": oi_change,
            "bullish_absorption": bullish_absorption,
            "bearish_absorption": bearish_absorption,
            "bullish_divergence": detect_bullish_divergence(
                price_change, cvd_change, oi_change, self.current_funding_rate
            ),
            "bearish_divergence": detect_bearish_divergence(
                price_change, cvd_change, oi_change, self.current_funding_rate
            ),
            **spoof_summary,
            **liq_summary,
        }
        self.last_feature_payload = features
        return features

    async def feature_loop(self, session: aiohttp.ClientSession) -> None:
        while self.running:
            try:
                features = self.build_feature_snapshot()
                self.feature_store.append(features)
                signal, long_score, short_score = decide_signal(features)
                current_price = features.get("mid_price", 0.0)
                now = now_ts()
                if signal and current_price > 0 and signal_allowed(
                    self.last_signal_ts, now, settings.min_signal_cooldown_seconds
                ):
                    plan = build_trade_plan(signal, current_price, self.compute_micro_atr())
                    message = format_signal(
                        settings.market_symbol,
                        signal,
                        features,
                        plan,
                        long_score,
                        short_score,
                    )
                    await self.telegram.send_message(session, message)
                    signal_payload = {
                        "ts": iso_utc(now),
                        "symbol": settings.market_symbol,
                        "side": signal,
                        "entry": plan["entry"],
                        "sl": plan["sl"],
                        "tp1": plan["tp1"],
                        "tp2": plan["tp2"],
                        "long_score": long_score,
                        "short_score": short_score,
                    }
                    self.signal_store.append(signal_payload)
                    self.last_signal_ts = now
                    self.logger.info("Signal emitted: %s", signal_payload)
                self.persist_state()
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Feature loop error: %s", exc)
            await asyncio.sleep(settings.feature_interval_seconds)

    def persist_raw_event(self, stream_name: str, payload: dict) -> None:
        safe_name = (stream_name or "unknown").replace("/", "_").replace("@", "_")
        path = RAW_EVENTS_DIR / f"{safe_name}.jsonl"
        JsonLineStore(path).append(payload)

    def persist_state(self) -> None:
        payload = {
            "ts": iso_utc(),
            "symbol": settings.market_symbol,
            "book_ready": self.book_sync.is_ready,
            "last_update_id": self.book.last_update_id,
            "open_interest": self.current_open_interest,
            "funding_rate": self.current_funding_rate,
            "last_signal_ts": self.last_signal_ts,
            "last_features": self.last_feature_payload,
        }
        self.state_store.save(payload)


async def main() -> None:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    app = BotApp()
    timeout = aiohttp.ClientTimeout(total=20)
    connector = aiohttp.TCPConnector(limit=50, ssl=False)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        await app.initialize(session)
        await asyncio.gather(
            app.consume_ws(session),
            app.periodic_rest_tasks(session),
            app.feature_loop(session),
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
