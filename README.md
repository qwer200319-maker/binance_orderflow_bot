# Binance Order Flow Bot

Advanced Binance USDⓈ-M Futures signal bot focused on:
- local order book reconstruction
- CVD / delta
- absorption detection
- spoofing heuristics
- liquidation clustering
- OI + funding + divergence filters
- Telegram alerting

## Important
This project is **signal-only** by default. It does **not** place orders.

## Features
- Rebuilds a local order book from REST snapshot + diff depth websocket events
- Tracks aggressive trade flow from `@aggTrade`
- Tracks liquidation snapshots from `@forceOrder`
- Polls open interest and funding rate from REST
- Computes a feature snapshot every second
- Emits LONG / SHORT signals when the scoring engine reaches threshold
- Saves feature and signal logs to `storage/*.jsonl`

## Install
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Configure
Create a `.env` file or export environment variables:
```env
BOT_SYMBOL=btcusdt
BOT_MARKET_SYMBOL=BTCUSDT
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
LOG_LEVEL=INFO
BOT_SIGNAL_COOLDOWN_SECONDS=900
BOT_MIN_REPEAT_PRICE_CHANGE=0
BOT_SETUP_LONG_SCORE=4
BOT_SETUP_SHORT_SCORE=4
BOT_CONFIRM_LONG_SCORE=3
BOT_CONFIRM_SHORT_SCORE=3
BOT_HTF_INTERVAL=1h
BOT_SETUP_INTERVAL=15m
BOT_HTF_CANDLE_LIMIT=200
BOT_SETUP_CANDLE_LIMIT=200
BOT_HTF_POLL_SECONDS=60
BOT_SETUP_POLL_SECONDS=30
BOT_HTF_EMA_LENGTH=55
BOT_HTF_SWING_LOOKBACK=12
BOT_SETUP_SWING_LOOKBACK=16
BOT_SETUP_ZONE_BUFFER_MULT=0.35
BOT_TRIGGER_LOOKBACK_SECONDS=20
BOT_SWING_LOOKBACK_SECONDS=180
BOT_LIQ_ACTIVE_WINDOW_SEC=20
BOT_ENTRY_ATR_BUFFER_MULT=0.1
BOT_ENTRY_SPREAD_BUFFER_MULT=1.5
BOT_STOP_BUFFER_ATR_MULT=0.2
BOT_SL_VOLATILITY_ATR_MULT=0.8
BOT_SL_SPREAD_BUFFER_MULT=3.0
BOT_TP1_STRUCTURE_FRACTION=0.5
BOT_TP1_ATR_FALLBACK=2.0
BOT_TP2_ATR_FALLBACK=3.0
BOT_DIVERGENCE_MIN_PRICE_CHANGE=0.0
```

## Run
```bash
python app.py
```

## Deploy on Render (Background Worker)
This runs the bot as a long-lived background worker.

1. Push this repo to GitHub.
2. In Render, create a new **Background Worker** and point it at the repo.
3. Render will detect `render.yaml` and configure the worker.
4. Set secrets in Render:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Optional: toggle `TELEGRAM_ENABLED=true`.

Notes:
- Logs written to `storage/*.jsonl` are ephemeral on Render unless you attach a disk or ship logs elsewhere.
- To keep raw events, set `BOT_PERSIST_RAW_EVENTS=true` (storage will grow).

Persistent logs on Render:
- `render.yaml` mounts a disk at `/var/data` and sets `BOT_STORAGE_DIR=/var/data/storage`.
- Logs will persist across restarts and deploys.

## Project notes
- The book sync follows Binance futures guidance: buffer diff-depth events, fetch snapshot, then apply updates only when sequence rules are satisfied.
- Spoofing and absorption logic are heuristic, not ground-truth market intent.
- This bot is designed for forward testing and research, not guaranteed profitability.
