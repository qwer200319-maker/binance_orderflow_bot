from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = Path(os.getenv("BOT_STORAGE_DIR", str(BASE_DIR / "storage")))
RAW_EVENTS_DIR = STORAGE_DIR / "raw_events"


@dataclass
class Settings:
    symbol: str = os.getenv("BOT_SYMBOL", "btcusdt").lower()
    market_symbol: str = os.getenv("BOT_MARKET_SYMBOL", "BTCUSDT").upper()

    ws_base_url: str = os.getenv("BINANCE_WS_BASE_URL", "wss://fstream.binance.com/stream")
    rest_base_url: str = os.getenv("BINANCE_REST_BASE_URL", "https://fapi.binance.com")

    depth_speed: str = os.getenv("BOT_DEPTH_SPEED", "100ms")
    depth_limit: int = int(os.getenv("BOT_DEPTH_LIMIT", "1000"))
    top_levels: int = int(os.getenv("BOT_TOP_LEVELS", "20"))

    feature_interval_seconds: float = float(os.getenv("BOT_FEATURE_INTERVAL_SECONDS", "1.0"))
    oi_poll_seconds: int = int(os.getenv("BOT_OI_POLL_SECONDS", "15"))
    funding_poll_seconds: int = int(os.getenv("BOT_FUNDING_POLL_SECONDS", "60"))
    snapshot_refresh_seconds: int = int(os.getenv("BOT_SNAPSHOT_REFRESH_SECONDS", "1800"))
    ping_interval_seconds: int = int(os.getenv("BOT_PING_INTERVAL_SECONDS", "20"))
    reconnect_delay_seconds: int = int(os.getenv("BOT_RECONNECT_DELAY_SECONDS", "5"))
    rest_backoff_seconds: int = int(os.getenv("BOT_REST_BACKOFF_SECONDS", "30"))
    rest_backoff_max_seconds: int = int(os.getenv("BOT_REST_BACKOFF_MAX_SECONDS", "300"))
    depth_buffer_max: int = int(os.getenv("BOT_DEPTH_BUFFER_MAX", "2000"))

    streams: List[str] = field(default_factory=list)

    imbalance_long_threshold: float = float(os.getenv("BOT_IMBALANCE_LONG_THRESHOLD", "0.18"))
    imbalance_short_threshold: float = float(os.getenv("BOT_IMBALANCE_SHORT_THRESHOLD", "-0.18"))
    wall_multiplier: float = float(os.getenv("BOT_WALL_MULTIPLIER", "4.0"))
    wall_min_lifetime_ms: int = int(os.getenv("BOT_WALL_MIN_LIFETIME_MS", "800"))

    delta_window_seconds: int = int(os.getenv("BOT_DELTA_WINDOW_SECONDS", "15"))
    cvd_window_seconds: int = int(os.getenv("BOT_CVD_WINDOW_SECONDS", "120"))
    price_change_window_seconds: int = int(os.getenv("BOT_PRICE_CHANGE_WINDOW_SECONDS", "60"))

    absorption_delta_threshold: float = float(os.getenv("BOT_ABSORPTION_DELTA_THRESHOLD", "50.0"))
    absorption_max_price_move_ticks: int = int(os.getenv("BOT_ABSORPTION_MAX_PRICE_MOVE_TICKS", "2"))
    absorption_persistence_levels: int = int(os.getenv("BOT_ABSORPTION_PERSISTENCE_LEVELS", "3"))

    spoof_lifetime_ms: int = int(os.getenv("BOT_SPOOF_LIFETIME_MS", "1200"))
    spoof_min_size_multiplier: float = float(os.getenv("BOT_SPOOF_MIN_SIZE_MULTIPLIER", "4.0"))
    spoof_max_execution_ratio: float = float(os.getenv("BOT_SPOOF_MAX_EXECUTION_RATIO", "0.10"))

    liq_cluster_window_sec: int = int(os.getenv("BOT_LIQ_CLUSTER_WINDOW_SEC", "60"))
    liq_min_cluster_count: int = int(os.getenv("BOT_LIQ_MIN_CLUSTER_COUNT", "3"))
    liq_price_bin: float = float(os.getenv("BOT_LIQ_PRICE_BIN", "10.0"))

    long_signal_score: int = int(os.getenv("BOT_LONG_SIGNAL_SCORE", "6"))
    short_signal_score: int = int(os.getenv("BOT_SHORT_SIGNAL_SCORE", "6"))
    min_signal_cooldown_seconds: int = int(os.getenv("BOT_SIGNAL_COOLDOWN_SECONDS", "90"))
    min_repeat_price_change: float = float(os.getenv("BOT_MIN_REPEAT_PRICE_CHANGE", "0"))

    atr_length: int = int(os.getenv("BOT_ATR_LENGTH", "14"))
    sl_atr_multiplier: float = float(os.getenv("BOT_SL_ATR_MULTIPLIER", "1.2"))
    tp1_rr: float = float(os.getenv("BOT_TP1_RR", "1.5"))
    tp2_rr: float = float(os.getenv("BOT_TP2_RR", "2.5"))
    default_tick_size: float = float(os.getenv("BOT_DEFAULT_TICK_SIZE", "0.1"))
    sl_usd: float = float(os.getenv("BOT_SL_USD", "500"))
    tp1_usd: float = float(os.getenv("BOT_TP1_USD", "1500"))
    tp2_usd: float = float(os.getenv("BOT_TP2_USD", "2000"))

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_enabled: bool = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    persist_raw_events: bool = os.getenv("BOT_PERSIST_RAW_EVENTS", "false").lower() == "true"
    log_throttle_seconds: int = int(os.getenv("BOT_LOG_THROTTLE_SECONDS", "30"))
    buffer_log_interval_seconds: float = float(os.getenv("BOT_BUFFER_LOG_INTERVAL_SECONDS", "5"))
    no_match_warn_throttle_seconds: float = float(os.getenv("BOT_NO_MATCH_WARN_THROTTLE_SECONDS", "30"))

    def __post_init__(self) -> None:
        if not self.streams:
            self.streams = [
                f"{self.symbol}@depth@{self.depth_speed}",
                f"{self.symbol}@aggTrade",
                f"{self.symbol}@forceOrder",
            ]
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        RAW_EVENTS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
