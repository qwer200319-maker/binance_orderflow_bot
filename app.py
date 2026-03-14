from __future__ import annotations

import asyncio
import logging
from collections import deque
from pathlib import Path
from typing import Any, Dict

import aiohttp
from dotenv import load_dotenv

from config import RAW_EVENTS_DIR, STORAGE_DIR, settings
from feeds.candle_loader import fetch_klines
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
from strategy.htf_bias import classify_bias
from strategy.liquidity_sweep import detect_liquidity_sweep
from strategy.regime_detector import detect_regime
from strategy.setup_15m import detect_setup
from strategy.volatility_filter import classify_volatility
from strategy.vwap_context import vwap_context
from utils.json_store import JsonLineStore, JsonStore
from utils.logger import get_logger
from utils.math_utils import mean
from utils.time_utils import iso_utc, now_ts


class LogBuffer(logging.Handler):
    def __init__(self, maxlen: int = 200) -> None:
        super().__init__()
        self.records: deque[dict[str, Any]] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.records.append(
                {
                    "ts": iso_utc(record.created),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
            )
        except Exception:
            return


class BotApp:
    def __init__(self) -> None:
        self.logger = get_logger("BotApp", settings.log_level)
        self.log_buffer = LogBuffer(maxlen=250)
        self.log_buffer.setLevel(logging.DEBUG)
        self.logger.addHandler(self.log_buffer)
        self.book = LocalBook()
        self.book_sync = BookSynchronizer(
            self.book,
            settings.log_level,
            settings.buffer_log_interval_seconds,
            settings.no_match_warn_throttle_seconds,
        )
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
        self.last_signal_side: str | None = None
        self.last_signal_price: float | None = None
        self.last_signal_long_score: int | None = None
        self.last_signal_short_score: int | None = None
        self.htf_bias: str = "NEUTRAL"
        self.htf_context: Dict[str, Any] = {}
        self.setup_signal: str = "NONE"
        self.setup_context: Dict[str, Any] = {}
        self.sweep_context: Dict[str, Any] = {}
        self.vwap_context: Dict[str, Any] = {}
        self.vwap_value: float = 0.0
        self.vwap_state: str = "NEUTRAL"
        self.vwap_reclaim: bool = False
        self.vwap_reject: bool = False
        self.market_regime: str = "UNKNOWN"
        self.regime_context: Dict[str, Any] = {}
        self.volatility_state: str = "UNKNOWN"
        self.volatility_value: float = 0.0
        self.last_htf_refresh: float = 0.0
        self.last_setup_refresh: float = 0.0
        self.last_book_resync_ts: float = 0.0
        self.last_decision_log_ts: float = 0.0
        self.last_feature_payload: Dict[str, Any] = {}
        self.last_decision_signal: str = "NONE"
        self.last_quality_score: int = 0
        self.last_quality_grade: str = ""
        self.last_signal_payload: Dict[str, Any] | None = None
        self.last_trade_plan: Dict[str, Any] | None = None
        self.recent_signals: deque[dict[str, Any]] = deque(maxlen=25)
        self.price_history: deque[dict[str, float]] = deque(maxlen=600)
        self.running = True
        self.oi_backoff_until: float = 0.0
        self.funding_backoff_until: float = 0.0
        self.snapshot_backoff_until: float = 0.0
        self.htf_backoff_until: float = 0.0
        self.setup_backoff_until: float = 0.0
        self.oi_backoff_seconds: int = settings.rest_backoff_seconds
        self.funding_backoff_seconds: int = settings.rest_backoff_seconds
        self.snapshot_backoff_seconds: int = settings.rest_backoff_seconds
        self.htf_backoff_seconds: int = settings.rest_backoff_seconds
        self.setup_backoff_seconds: int = settings.rest_backoff_seconds
        self.last_snapshot_warn_ts: float = 0.0

    async def initialize(self, session: aiohttp.ClientSession) -> None:
        while self.running:
            ok = await self.refresh_snapshot(session)
            if ok:
                break
            await asyncio.sleep(settings.reconnect_delay_seconds)
        await self.refresh_oi(session)
        await self.refresh_funding(session)
        await self.refresh_htf_bias(session)
        await self.refresh_setup(session)
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
                self.snapshot_backoff_until = now_ts() + self.snapshot_backoff_seconds
                self.snapshot_backoff_seconds = min(
                    self.snapshot_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            if exc.status == 418:
                retry_after = self._retry_after_seconds(exc, self.snapshot_backoff_seconds)
                self.logger.warning(
                    "Snapshot rate limited/banned (HTTP 418). Backing off for %ss.",
                    retry_after,
                )
                self.snapshot_backoff_until = now_ts() + retry_after
                self.snapshot_backoff_seconds = min(
                    self.snapshot_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            if exc.status == 429:
                retry_after = self._retry_after_seconds(exc, self.snapshot_backoff_seconds)
                self.logger.warning(
                    "Snapshot rate limited (HTTP 429). Backing off for %ss.",
                    retry_after,
                )
                self.snapshot_backoff_until = now_ts() + retry_after
                self.snapshot_backoff_seconds = min(
                    self.snapshot_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            raise
        except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
            self.logger.warning(
                "Snapshot request failed (%s). Backing off for %ss.",
                exc.__class__.__name__,
                self.snapshot_backoff_seconds,
            )
            self.snapshot_backoff_until = now_ts() + self.snapshot_backoff_seconds
            self.snapshot_backoff_seconds = min(
                self.snapshot_backoff_seconds * 2, settings.rest_backoff_max_seconds
            )
            return False
        self.book_sync.initialize_from_snapshot(snapshot)
        self.last_snapshot_ts = now_ts()
        self.snapshot_backoff_seconds = settings.rest_backoff_seconds
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
                self.oi_backoff_until = now_ts() + self.oi_backoff_seconds
                self.oi_backoff_seconds = min(
                    self.oi_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            if exc.status == 418:
                retry_after = self._retry_after_seconds(exc, self.oi_backoff_seconds)
                self.logger.warning(
                    "Open interest rate limited/banned (HTTP 418). Backing off for %ss.",
                    retry_after,
                )
                self.oi_backoff_until = now_ts() + retry_after
                self.oi_backoff_seconds = min(
                    self.oi_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            if exc.status == 429:
                retry_after = self._retry_after_seconds(exc, self.oi_backoff_seconds)
                self.logger.warning(
                    "Open interest rate limited (HTTP 429). Backing off for %ss.",
                    retry_after,
                )
                self.oi_backoff_until = now_ts() + retry_after
                self.oi_backoff_seconds = min(
                    self.oi_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            raise
        except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
            self.logger.warning(
                "Open interest request failed (%s). Backing off for %ss.",
                exc.__class__.__name__,
                self.oi_backoff_seconds,
            )
            self.oi_backoff_until = now_ts() + self.oi_backoff_seconds
            self.oi_backoff_seconds = min(
                self.oi_backoff_seconds * 2, settings.rest_backoff_max_seconds
            )
            return False
        self.previous_open_interest = self.current_open_interest or oi
        self.current_open_interest = oi
        self.oi_backoff_seconds = settings.rest_backoff_seconds
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
                self.funding_backoff_until = now_ts() + self.funding_backoff_seconds
                self.funding_backoff_seconds = min(
                    self.funding_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            if exc.status == 418:
                retry_after = self._retry_after_seconds(exc, self.funding_backoff_seconds)
                self.logger.warning(
                    "Funding rate rate limited/banned (HTTP 418). Backing off for %ss.",
                    retry_after,
                )
                self.funding_backoff_until = now_ts() + retry_after
                self.funding_backoff_seconds = min(
                    self.funding_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            if exc.status == 429:
                retry_after = self._retry_after_seconds(exc, self.funding_backoff_seconds)
                self.logger.warning(
                    "Funding rate rate limited (HTTP 429). Backing off for %ss.",
                    retry_after,
                )
                self.funding_backoff_until = now_ts() + retry_after
                self.funding_backoff_seconds = min(
                    self.funding_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            raise
        except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
            self.logger.warning(
                "Funding request failed (%s). Backing off for %ss.",
                exc.__class__.__name__,
                self.funding_backoff_seconds,
            )
            self.funding_backoff_until = now_ts() + self.funding_backoff_seconds
            self.funding_backoff_seconds = min(
                self.funding_backoff_seconds * 2, settings.rest_backoff_max_seconds
            )
            return False
        self.funding_backoff_seconds = settings.rest_backoff_seconds
        return True

    async def refresh_htf_bias(self, session: aiohttp.ClientSession) -> bool:
        try:
            candles = await fetch_klines(
                session,
                settings.rest_base_url,
                settings.market_symbol,
                settings.htf_interval,
                settings.htf_candle_limit,
            )
        except aiohttp.ClientResponseError as exc:
            if exc.status in (418, 429, 451):
                self.htf_backoff_until = now_ts() + self.htf_backoff_seconds
                self.htf_backoff_seconds = min(
                    self.htf_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            raise
        except (asyncio.TimeoutError, aiohttp.ClientError):
            self.htf_backoff_until = now_ts() + self.htf_backoff_seconds
            self.htf_backoff_seconds = min(
                self.htf_backoff_seconds * 2, settings.rest_backoff_max_seconds
            )
            return False

        bias, context = classify_bias(
            candles,
            settings.htf_ema_fast,
            settings.htf_ema_slow,
            settings.htf_swing_lookback,
            settings.htf_ema_flat_ratio,
            settings.htf_allow_pullback_bias,
        )
        self.htf_bias = bias
        self.htf_context = context
        self.htf_backoff_seconds = settings.rest_backoff_seconds
        self.last_htf_refresh = now_ts()
        return True

    async def refresh_setup(self, session: aiohttp.ClientSession) -> bool:
        try:
            candles = await fetch_klines(
                session,
                settings.rest_base_url,
                settings.market_symbol,
                settings.setup_interval,
                settings.setup_candle_limit,
            )
        except aiohttp.ClientResponseError as exc:
            if exc.status in (418, 429, 451):
                self.setup_backoff_until = now_ts() + self.setup_backoff_seconds
                self.setup_backoff_seconds = min(
                    self.setup_backoff_seconds * 2, settings.rest_backoff_max_seconds
                )
                return False
            raise
        except (asyncio.TimeoutError, aiohttp.ClientError):
            self.setup_backoff_until = now_ts() + self.setup_backoff_seconds
            self.setup_backoff_seconds = min(
                self.setup_backoff_seconds * 2, settings.rest_backoff_max_seconds
            )
            return False

        setup, context = detect_setup(
            candles,
            settings.setup_swing_lookback,
            settings.setup_zone_buffer_mult,
        )
        bullish_sweep, bearish_sweep, sweep_ctx = detect_liquidity_sweep(
            candles,
            settings.setup_swing_lookback,
            settings.sweep_lookback_candles,
        )
        vwap_state, vwap_reclaim, vwap_reject, vwap_val = vwap_context(
            candles,
            settings.vwap_lookback_candles,
        )
        regime, regime_ctx = detect_regime(
            candles,
            settings.regime_lookback_candles,
            settings.htf_ema_fast,
            settings.htf_ema_slow,
            settings.htf_ema_flat_ratio,
            settings.regime_expansion_ratio,
            settings.regime_chop_crosses,
            settings.regime_range_ratio,
        )
        vol_state, vol_value = classify_volatility(
            candles,
            settings.volatility_atr_length,
            settings.volatility_low_ratio,
            settings.volatility_high_ratio,
        )
        self.setup_signal = setup
        self.setup_context = context
        self.sweep_context = {
            "bullish_sweep": bullish_sweep,
            "bearish_sweep": bearish_sweep,
            **sweep_ctx,
        }
        self.vwap_context = {
            "state": vwap_state,
            "reclaim": vwap_reclaim,
            "reject": vwap_reject,
        }
        self.vwap_value = vwap_val
        self.vwap_state = vwap_state
        self.vwap_reclaim = vwap_reclaim
        self.vwap_reject = vwap_reject
        self.market_regime = regime
        self.regime_context = regime_ctx
        self.volatility_state = vol_state
        self.volatility_value = vol_value
        self.setup_backoff_seconds = settings.rest_backoff_seconds
        self.last_setup_refresh = now_ts()
        return True

    async def periodic_rest_tasks(self, session: aiohttp.ClientSession) -> None:
        last_oi_refresh = 0.0
        last_funding_refresh = 0.0
        while self.running:
            now = now_ts()
            try:
                if now >= self.oi_backoff_until and now - last_oi_refresh >= settings.oi_poll_seconds:
                    if await self.refresh_oi(session):
                        last_oi_refresh = now
                if now >= self.funding_backoff_until and now - last_funding_refresh >= settings.funding_poll_seconds:
                    if await self.refresh_funding(session):
                        last_funding_refresh = now
                if now >= self.snapshot_backoff_until and now - self.last_snapshot_ts >= settings.snapshot_refresh_seconds:
                    await self.refresh_snapshot(session)
                if now >= self.htf_backoff_until and now - self.last_htf_refresh >= settings.htf_poll_seconds:
                    await self.refresh_htf_bias(session)
                if now >= self.setup_backoff_until and now - self.last_setup_refresh >= settings.setup_poll_seconds:
                    await self.refresh_setup(session)
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
        ok = self.book_sync.process_event(event)
        if not ok:
            if not self.book_sync.is_ready:
                if self.book_sync.buffer_len() > settings.depth_buffer_max:
                    self.logger.warning(
                        "Depth buffer overflow. Resetting sync... %s",
                        self.book_sync.buffer_summary(),
                    )
                    self.book_sync.reset()
                    now = now_ts()
                    if now - self.last_book_resync_ts >= settings.book_resync_min_seconds:
                        self.last_book_resync_ts = now
                        await self.refresh_snapshot(session)
                    return
                if self.book.last_update_id is None:
                    try:
                        await self.refresh_snapshot(session)
                    except Exception as exc:  # noqa: BLE001
                        self.logger.exception("Snapshot refresh failed during bootstrap: %s", exc)
                    return
                if self.book_sync.needs_snapshot_refresh():
                    now = now_ts()
                    if now - self.last_snapshot_ts >= 5 and now - self.last_book_resync_ts >= settings.book_resync_min_seconds:
                        self.last_book_resync_ts = now
                        if now - self.last_snapshot_warn_ts >= settings.log_throttle_seconds:
                            self.last_snapshot_warn_ts = now
                            self.logger.warning(
                                "Order book snapshot is behind buffered events. Refreshing snapshot... %s",
                                self.book_sync.buffer_summary(),
                            )
                        await self.refresh_snapshot(session)
                    return
            now = now_ts()
            if now - self.last_book_resync_ts >= settings.book_resync_min_seconds:
                self.last_book_resync_ts = now
                self.logger.warning("Order book out of sync. Reinitializing...")
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

    @staticmethod
    def _retry_after_seconds(exc: aiohttp.ClientResponseError, fallback: int) -> int:
        try:
            if exc.headers and "Retry-After" in exc.headers:
                return int(exc.headers["Retry-After"])
        except Exception:  # noqa: BLE001
            return fallback
        return fallback

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

    def price_window_stats(self, window_sec: int, offset_sec: int = 0) -> tuple[float, float, float]:
        now = now_ts()
        prices = [
            float(p["price"])
            for p in self.trades_buffer.prices
            if offset_sec < (now - float(p["ts"])) <= (offset_sec + window_sec)
        ]
        if not prices:
            return 0.0, 0.0, 0.0
        return max(prices), min(prices), mean(prices)

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
        delta_5s = self.cvd.window_delta(now, settings.delta_confirm_window_seconds)
        delta_15s = self.cvd.window_delta(now, settings.delta_window_seconds)
        cvd_change = self.cvd.window_delta(now, settings.cvd_window_seconds)
        oi_change = self.current_open_interest - self.previous_open_interest
        tick_size = settings.default_tick_size
        price_move_ticks = price_change / tick_size if tick_size > 0 else 0.0
        micro_atr = self.compute_micro_atr()
        entry_buffer = max(
            micro_atr * settings.entry_atr_buffer_mult,
            book_snapshot["spread"] * settings.entry_spread_buffer_mult,
        )

        recent_high, recent_low, _ = self.price_window_stats(settings.trigger_lookback_seconds)
        prev_high, prev_low, _ = self.price_window_stats(
            settings.trigger_lookback_seconds,
            settings.trigger_lookback_seconds,
        )
        swing_high, swing_low, _ = self.price_window_stats(settings.swing_lookback_seconds)
        trend_high, trend_low, _ = self.price_window_stats(settings.trend_window_seconds)
        prev_trend_high, prev_trend_low, _ = self.price_window_stats(
            settings.trend_window_seconds,
            settings.trend_window_seconds,
        )

        trend_buffer = micro_atr * settings.trend_buffer_atr_mult
        trend_higher_highs = prev_trend_high > 0 and trend_high > (prev_trend_high + trend_buffer)
        trend_lower_lows = prev_trend_low > 0 and trend_low < (prev_trend_low - trend_buffer)

        stop_buffer = micro_atr * settings.stop_buffer_atr_mult
        mid_price = book_snapshot["mid_price"]
        if mid_price > 0:
            self.price_history.append(
                {
                    "ts": now,
                    "price": mid_price,
                    "vwap": self.vwap_value,
                }
            )
        stopped_making_lows = recent_low > 0 and mid_price > (recent_low + stop_buffer)
        stopped_making_highs = recent_high > 0 and mid_price < (recent_high - stop_buffer)

        setup_trigger_high = float(self.setup_context.get("trigger_high", 0.0))
        setup_trigger_low = float(self.setup_context.get("trigger_low", 0.0))
        long_trigger = setup_trigger_high if setup_trigger_high > 0 else recent_high
        short_trigger = setup_trigger_low if setup_trigger_low > 0 else recent_low
        long_entry = (long_trigger + entry_buffer) if long_trigger > 0 else 0.0
        short_entry = (short_trigger - entry_buffer) if short_trigger > 0 else 0.0
        long_reclaim = long_entry > 0 and mid_price >= long_entry
        short_break = short_entry > 0 and mid_price <= short_entry

        delta_expanding_up = (
            delta_5s > 0
            and delta_15s > 0
            and abs(delta_5s) >= abs(delta_15s) * settings.delta_expand_ratio
        )
        delta_expanding_down = (
            delta_5s < 0
            and delta_15s < 0
            and abs(delta_5s) >= abs(delta_15s) * settings.delta_expand_ratio
        )

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
        liq_active_summary = self.liquidations.summarize(
            now,
            settings.liq_active_window_sec,
            settings.liq_price_bin,
            settings.liq_min_cluster_count,
        )

        features: Dict[str, Any] = {
            "ts": iso_utc(now),
            "mid_price": mid_price,
            "spread": book_snapshot["spread"],
            "imbalance": book_snapshot["imbalance"],
            "cvd": self.cvd.value,
            "delta_5s": delta_5s,
            "delta_15s": delta_15s,
            "price_change": price_change,
            "price_move_ticks": price_move_ticks,
            "htf_bias": self.htf_bias,
            "setup_signal": self.setup_signal,
            "bullish_sweep": self.sweep_context.get("bullish_sweep", False),
            "bearish_sweep": self.sweep_context.get("bearish_sweep", False),
            "vwap": self.vwap_value,
            "vwap_context": self.vwap_state,
            "vwap_reclaim": self.vwap_reclaim,
            "vwap_reject": self.vwap_reject,
            "market_regime": self.market_regime,
            "volatility_state": self.volatility_state,
            "volatility_value": self.volatility_value,
            "funding_rate": self.current_funding_rate,
            "open_interest": self.current_open_interest,
            "oi_change": oi_change,
            "micro_atr": micro_atr,
            "entry_buffer": entry_buffer,
            "recent_high": recent_high,
            "recent_low": recent_low,
            "prev_high": prev_high,
            "prev_low": prev_low,
            "swing_high": swing_high,
            "swing_low": swing_low,
            "swing_high_15m": float(self.setup_context.get("recent_high", 0.0)),
            "swing_low_15m": float(self.setup_context.get("recent_low", 0.0)),
            "support_15m": float(self.setup_context.get("support", 0.0)),
            "resistance_15m": float(self.setup_context.get("resistance", 0.0)),
            "swing_high_1h": float(self.htf_context.get("recent_high", 0.0)),
            "swing_low_1h": float(self.htf_context.get("recent_low", 0.0)),
            "trend_high": trend_high,
            "trend_low": trend_low,
            "trend_higher_highs": trend_higher_highs,
            "trend_lower_lows": trend_lower_lows,
            "stopped_making_lows": stopped_making_lows,
            "stopped_making_highs": stopped_making_highs,
            "long_trigger": long_trigger,
            "short_trigger": short_trigger,
            "long_reclaim": long_reclaim,
            "short_break": short_break,
            "long_entry": long_entry,
            "short_entry": short_entry,
            "delta_expanding_up": delta_expanding_up,
            "delta_expanding_down": delta_expanding_down,
            "bullish_absorption": bullish_absorption,
            "bearish_absorption": bearish_absorption,
            "bullish_divergence": detect_bullish_divergence(
                price_change,
                cvd_change,
                oi_change,
                self.current_funding_rate,
                settings.divergence_min_price_change,
            ),
            "bearish_divergence": detect_bearish_divergence(
                price_change,
                cvd_change,
                oi_change,
                self.current_funding_rate,
                settings.divergence_min_price_change,
            ),
            **spoof_summary,
            **liq_summary,
            "active_sell_liq_cluster": liq_active_summary.get("recent_sell_liq_cluster", False),
            "active_buy_liq_cluster": liq_active_summary.get("recent_buy_liq_cluster", False),
        }
        features["quality_score"] = 0
        features["quality_grade"] = ""
        self.last_feature_payload = features
        return features

    async def feature_loop(self, session: aiohttp.ClientSession) -> None:
        while self.running:
            try:
                features = self.build_feature_snapshot()
                self.feature_store.append(features)
                signal, quality_score, quality_grade, reason_summary = decide_signal(features)
                self.last_decision_signal = signal or "NONE"
                self.last_quality_score = quality_score
                self.last_quality_grade = quality_grade
                current_price = features.get("mid_price", 0.0)
                now = now_ts()
                if settings.decision_log_interval_seconds > 0 and now - self.last_decision_log_ts >= settings.decision_log_interval_seconds:
                    self.last_decision_log_ts = now
                    self.logger.info(
                        "Decision | htf=%s setup=%s sweep=%s/%s vwap=%s(reclaim=%s reject=%s) regime=%s vol=%s | "
                        "quality=%s(%s) | signal=%s | reason=%s",
                        self.htf_bias,
                        self.setup_signal,
                        features.get("bullish_sweep"),
                        features.get("bearish_sweep"),
                        self.vwap_state,
                        self.vwap_reclaim,
                        self.vwap_reject,
                        self.market_regime,
                        self.volatility_state,
                        quality_grade or "-",
                        quality_score,
                        signal or "NONE",
                        reason_summary or "-",
                    )
                if signal and current_price > 0 and signal_allowed(
                    self.last_signal_ts, now, settings.min_signal_cooldown_seconds
                ):
                    entry_price = (
                        features.get("long_entry", 0.0)
                        if signal == "LONG"
                        else features.get("short_entry", 0.0)
                    )
                    if entry_price <= 0:
                        await asyncio.sleep(settings.feature_interval_seconds)
                        continue
                    if not self._repeat_signal_allowed(signal, current_price, quality_score, quality_score):
                        await asyncio.sleep(settings.feature_interval_seconds)
                        continue
                    features["quality_score"] = quality_score
                    features["quality_grade"] = quality_grade
                    features["reason_summary"] = reason_summary
                    plan = build_trade_plan(signal, entry_price, features)
                    message = format_signal(
                        settings.market_symbol,
                        signal,
                        features,
                        plan,
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
                        "htf_bias": self.htf_bias,
                        "setup_signal": self.setup_signal,
                        "bullish_sweep": self.sweep_context.get("bullish_sweep", False),
                        "bearish_sweep": self.sweep_context.get("bearish_sweep", False),
                        "vwap_context": self.vwap_state,
                        "vwap_reclaim": self.vwap_reclaim,
                        "vwap_reject": self.vwap_reject,
                        "vwap": self.vwap_value,
                        "market_regime": self.market_regime,
                        "volatility_state": self.volatility_state,
                        "trigger_high": features.get("long_trigger"),
                        "trigger_low": features.get("short_trigger"),
                        "quality_score": quality_score,
                        "quality_grade": quality_grade,
                        "reason_summary": reason_summary,
                    }
                    self.signal_store.append(signal_payload)
                    self.last_signal_payload = signal_payload
                    self.last_trade_plan = plan
                    self.recent_signals.append(signal_payload)
                    self.last_signal_ts = now
                    self.last_signal_side = signal
                    self.last_signal_price = current_price
                    self.last_signal_long_score = quality_score
                    self.last_signal_short_score = quality_score
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
            "last_signal_side": self.last_signal_side,
            "last_signal_price": self.last_signal_price,
            "last_signal_long_score": self.last_signal_long_score,
            "last_signal_short_score": self.last_signal_short_score,
            "htf_bias": self.htf_bias,
            "setup_signal": self.setup_signal,
            "bullish_sweep": self.sweep_context.get("bullish_sweep", False),
            "bearish_sweep": self.sweep_context.get("bearish_sweep", False),
            "vwap_context": self.vwap_state,
            "vwap_reclaim": self.vwap_reclaim,
            "vwap_reject": self.vwap_reject,
            "market_regime": self.market_regime,
            "volatility_state": self.volatility_state,
            "last_features": self.last_feature_payload,
        }
        self.state_store.save(payload)

    def _repeat_signal_allowed(self, side: str, price: float, long_score: int, short_score: int) -> bool:
        if self.last_signal_side is None or self.last_signal_price is None:
            return True
        if side != self.last_signal_side:
            return True

        price_change = abs(price - self.last_signal_price)
        min_change = settings.min_repeat_price_change
        if min_change > 0 and price_change >= min_change:
            return True

        if side == "LONG":
            return self.last_signal_long_score is None or long_score > self.last_signal_long_score
        return self.last_signal_short_score is None or short_score > self.last_signal_short_score


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

