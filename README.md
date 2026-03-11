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
BOT_SL_USD=500
BOT_TP1_USD=1500
BOT_TP2_USD=2000
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
