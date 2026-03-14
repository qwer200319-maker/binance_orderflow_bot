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
    htf_interval: str = os.getenv("BOT_HTF_INTERVAL", "1h")
    setup_interval: str = os.getenv("BOT_SETUP_INTERVAL", "15m")
    htf_candle_limit: int = int(os.getenv("BOT_HTF_CANDLE_LIMIT", "200"))
    setup_candle_limit: int = int(os.getenv("BOT_SETUP_CANDLE_LIMIT", "200"))
    htf_poll_seconds: int = int(os.getenv("BOT_HTF_POLL_SECONDS", "60"))
    setup_poll_seconds: int = int(os.getenv("BOT_SETUP_POLL_SECONDS", "30"))
    htf_ema_fast: int = int(os.getenv("BOT_HTF_EMA_FAST", "20"))
    htf_ema_slow: int = int(os.getenv("BOT_HTF_EMA_SLOW", "50"))
    htf_ema_flat_ratio: float = float(os.getenv("BOT_HTF_EMA_FLAT_RATIO", "0.0005"))
    htf_allow_pullback_bias: bool = os.getenv("BOT_HTF_ALLOW_PULLBACK_BIAS", "false").lower() == "true"
    htf_swing_lookback: int = int(os.getenv("BOT_HTF_SWING_LOOKBACK", "12"))
    setup_swing_lookback: int = int(os.getenv("BOT_SETUP_SWING_LOOKBACK", "16"))
    setup_zone_buffer_mult: float = float(os.getenv("BOT_SETUP_ZONE_BUFFER_MULT", "0.35"))
    sweep_lookback_candles: int = int(os.getenv("BOT_SWEEP_LOOKBACK_CANDLES", "2"))
    vwap_lookback_candles: int = int(os.getenv("BOT_VWAP_LOOKBACK_CANDLES", "96"))
    regime_lookback_candles: int = int(os.getenv("BOT_REGIME_LOOKBACK_CANDLES", "48"))
    regime_expansion_ratio: float = float(os.getenv("BOT_REGIME_EXPANSION_RATIO", "1.6"))
    regime_chop_crosses: int = int(os.getenv("BOT_REGIME_CHOP_CROSSES", "6"))
    regime_range_ratio: float = float(os.getenv("BOT_REGIME_RANGE_RATIO", "0.85"))
    volatility_atr_length: int = int(os.getenv("BOT_VOLATILITY_ATR_LENGTH", "14"))
    volatility_low_ratio: float = float(os.getenv("BOT_VOLATILITY_LOW_RATIO", "0.0015"))
    volatility_high_ratio: float = float(os.getenv("BOT_VOLATILITY_HIGH_RATIO", "0.004"))
    quality_grade_a: int = int(os.getenv("BOT_QUALITY_GRADE_A", "8"))
    quality_grade_b: int = int(os.getenv("BOT_QUALITY_GRADE_B", "6"))
    min_quality_grade: str = os.getenv("BOT_MIN_QUALITY_GRADE", "C")
    high_vol_min_quality: str = os.getenv("BOT_HIGH_VOL_MIN_QUALITY", "B")
    allowed_regimes: list[str] | str = os.getenv("BOT_ALLOWED_REGIMES", "TRENDING,RANGING,CHOPPY")

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
    delta_confirm_window_seconds: int = int(os.getenv("BOT_DELTA_CONFIRM_WINDOW_SECONDS", "5"))
    cvd_window_seconds: int = int(os.getenv("BOT_CVD_WINDOW_SECONDS", "120"))
    price_change_window_seconds: int = int(os.getenv("BOT_PRICE_CHANGE_WINDOW_SECONDS", "60"))
    trigger_lookback_seconds: int = int(os.getenv("BOT_TRIGGER_LOOKBACK_SECONDS", "20"))
    swing_lookback_seconds: int = int(os.getenv("BOT_SWING_LOOKBACK_SECONDS", "180"))
    trend_window_seconds: int = int(os.getenv("BOT_TREND_WINDOW_SECONDS", "60"))

    absorption_delta_threshold: float = float(os.getenv("BOT_ABSORPTION_DELTA_THRESHOLD", "50.0"))
    absorption_max_price_move_ticks: int = int(os.getenv("BOT_ABSORPTION_MAX_PRICE_MOVE_TICKS", "2"))
    absorption_persistence_levels: int = int(os.getenv("BOT_ABSORPTION_PERSISTENCE_LEVELS", "3"))

    spoof_lifetime_ms: int = int(os.getenv("BOT_SPOOF_LIFETIME_MS", "1200"))
    spoof_min_size_multiplier: float = float(os.getenv("BOT_SPOOF_MIN_SIZE_MULTIPLIER", "4.0"))
    spoof_max_execution_ratio: float = float(os.getenv("BOT_SPOOF_MAX_EXECUTION_RATIO", "0.10"))

    liq_cluster_window_sec: int = int(os.getenv("BOT_LIQ_CLUSTER_WINDOW_SEC", "60"))
    liq_active_window_sec: int = int(os.getenv("BOT_LIQ_ACTIVE_WINDOW_SEC", "20"))
    liq_min_cluster_count: int = int(os.getenv("BOT_LIQ_MIN_CLUSTER_COUNT", "3"))
    liq_price_bin: float = float(os.getenv("BOT_LIQ_PRICE_BIN", "10.0"))

    long_signal_score: int = int(os.getenv("BOT_LONG_SIGNAL_SCORE", "6"))
    short_signal_score: int = int(os.getenv("BOT_SHORT_SIGNAL_SCORE", "6"))
    setup_long_score: int = int(os.getenv("BOT_SETUP_LONG_SCORE", "3"))
    setup_short_score: int = int(os.getenv("BOT_SETUP_SHORT_SCORE", "3"))
    confirm_long_score: int = int(os.getenv("BOT_CONFIRM_LONG_SCORE", "2"))
    confirm_short_score: int = int(os.getenv("BOT_CONFIRM_SHORT_SCORE", "2"))
    min_signal_cooldown_seconds: int = int(os.getenv("BOT_SIGNAL_COOLDOWN_SECONDS", "900"))
    min_repeat_price_change: float = float(os.getenv("BOT_MIN_REPEAT_PRICE_CHANGE", "0"))

    atr_length: int = int(os.getenv("BOT_ATR_LENGTH", "14"))
    sl_atr_multiplier: float = float(os.getenv("BOT_SL_ATR_MULTIPLIER", "1.2"))
    tp1_rr: float = float(os.getenv("BOT_TP1_RR", "1.5"))
    tp2_rr: float = float(os.getenv("BOT_TP2_RR", "2.5"))
    default_tick_size: float = float(os.getenv("BOT_DEFAULT_TICK_SIZE", "0.1"))
    entry_atr_buffer_mult: float = float(os.getenv("BOT_ENTRY_ATR_BUFFER_MULT", "0.25"))
    entry_spread_buffer_mult: float = float(os.getenv("BOT_ENTRY_SPREAD_BUFFER_MULT", "1.5"))
    stop_buffer_atr_mult: float = float(os.getenv("BOT_STOP_BUFFER_ATR_MULT", "0.2"))
    trend_buffer_atr_mult: float = float(os.getenv("BOT_TREND_BUFFER_ATR_MULT", "0.2"))
    delta_expand_ratio: float = float(os.getenv("BOT_DELTA_EXPAND_RATIO", "0.6"))
    sl_volatility_atr_mult: float = float(os.getenv("BOT_SL_VOLATILITY_ATR_MULT", "1.2"))
    sl_spread_buffer_mult: float = float(os.getenv("BOT_SL_SPREAD_BUFFER_MULT", "3.0"))
    tp1_structure_fraction: float = float(os.getenv("BOT_TP1_STRUCTURE_FRACTION", "0.5"))
    tp1_atr_fallback: float = float(os.getenv("BOT_TP1_ATR_FALLBACK", "2.0"))
    tp2_atr_fallback: float = float(os.getenv("BOT_TP2_ATR_FALLBACK", "3.0"))
    divergence_min_price_change: float = float(os.getenv("BOT_DIVERGENCE_MIN_PRICE_CHANGE", "0.0"))
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
    decision_log_interval_seconds: int = int(os.getenv("BOT_DECISION_LOG_INTERVAL_SECONDS", "60"))
    book_resync_min_seconds: int = int(os.getenv("BOT_BOOK_RESYNC_MIN_SECONDS", "5"))

    def __post_init__(self) -> None:
        if not self.streams:
            self.streams = [
                f"{self.symbol}@depth@{self.depth_speed}",
                f"{self.symbol}@aggTrade",
                f"{self.symbol}@forceOrder",
            ]
        if isinstance(self.allowed_regimes, str):
            self.allowed_regimes = [v.strip().upper() for v in self.allowed_regimes.split(",") if v.strip()]
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        RAW_EVENTS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()

