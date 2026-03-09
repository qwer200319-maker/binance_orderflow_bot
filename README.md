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
```

## Run
```bash
python app.py
```

## Project notes
- The book sync follows Binance futures guidance: buffer diff-depth events, fetch snapshot, then apply updates only when sequence rules are satisfied.
- Spoofing and absorption logic are heuristic, not ground-truth market intent.
- This bot is designed for forward testing and research, not guaranteed profitability.
