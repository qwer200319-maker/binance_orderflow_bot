from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import aiohttp
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app import BotApp
from config import settings
from utils.time_utils import iso_utc, now_ts


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = WEB_DIR / "static"

bot_app = BotApp()


def build_state_payload() -> Dict[str, Any]:
    features = bot_app.last_feature_payload or {}
    last_signal = bot_app.last_signal_payload or {}
    last_signal_ts = bot_app.last_signal_ts
    cooldown = settings.min_signal_cooldown_seconds
    now = now_ts()
    cooldown_remaining = 0.0
    if last_signal_ts:
        cooldown_remaining = max(0.0, cooldown - (now - last_signal_ts))

    payload = {
        "ts": iso_utc(now),
        "symbol": settings.market_symbol,
        "price": features.get("mid_price"),
        "htf_bias": bot_app.htf_bias,
        "setup_signal": bot_app.setup_signal,
        "market_regime": bot_app.market_regime,
        "volatility_state": bot_app.volatility_state,
        "volatility_value": bot_app.volatility_value,
        "vwap": bot_app.vwap_value,
        "vwap_state": bot_app.vwap_state,
        "vwap_reclaim": bot_app.vwap_reclaim,
        "vwap_reject": bot_app.vwap_reject,
        "bullish_sweep": bot_app.sweep_context.get("bullish_sweep", False),
        "bearish_sweep": bot_app.sweep_context.get("bearish_sweep", False),
        "delta_5s": features.get("delta_5s"),
        "delta_15s": features.get("delta_15s"),
        "imbalance": features.get("imbalance"),
        "bullish_absorption": features.get("bullish_absorption"),
        "bearish_absorption": features.get("bearish_absorption"),
        "recent_buy_liq_cluster": features.get("recent_buy_liq_cluster"),
        "recent_sell_liq_cluster": features.get("recent_sell_liq_cluster"),
        "active_buy_liq_cluster": features.get("active_buy_liq_cluster"),
        "active_sell_liq_cluster": features.get("active_sell_liq_cluster"),
        "signal_current": bot_app.last_decision_signal,
        "quality_score": bot_app.last_quality_score,
        "quality_grade": bot_app.last_quality_grade,
        "entry": last_signal.get("entry"),
        "sl": last_signal.get("sl"),
        "tp1": last_signal.get("tp1"),
        "tp2": last_signal.get("tp2"),
        "last_signal_side": last_signal.get("side"),
        "last_signal_time": iso_utc(last_signal_ts) if last_signal_ts else None,
        "cooldown_seconds": cooldown,
        "cooldown_remaining": cooldown_remaining,
        "running": bot_app.running,
        "swing_high_1h": features.get("swing_high_1h"),
        "swing_low_1h": features.get("swing_low_1h"),
        "swing_high_15m": features.get("swing_high_15m"),
        "swing_low_15m": features.get("swing_low_15m"),
        "logs": list(bot_app.log_buffer.records)[-120:],
        "signals": list(bot_app.recent_signals)[-20:],
    }
    return payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv(BASE_DIR / ".env")
    timeout = aiohttp.ClientTimeout(total=20)
    connector = aiohttp.TCPConnector(limit=50, ssl=False)
    session = aiohttp.ClientSession(timeout=timeout, connector=connector)
    tasks = []
    try:
        await bot_app.initialize(session)
        tasks = [
            asyncio.create_task(bot_app.consume_ws(session)),
            asyncio.create_task(bot_app.periodic_rest_tasks(session)),
            asyncio.create_task(bot_app.feature_loop(session)),
        ]
        yield
    finally:
        bot_app.running = False
        for task in tasks:
            task.cancel()
        await session.close()


app = FastAPI(title="Orderflow Bot Dashboard", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/manifest.json")
async def manifest() -> FileResponse:
    return FileResponse(WEB_DIR / "manifest.json")


@app.get("/sw.js")
async def service_worker() -> FileResponse:
    return FileResponse(WEB_DIR / "sw.js")


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "time": iso_utc()})


@app.get("/api/state")
async def state() -> JSONResponse:
    return JSONResponse(build_state_payload())


@app.get("/api/chart")
async def chart() -> JSONResponse:
    features = bot_app.last_feature_payload or {}
    last_signal = bot_app.last_signal_payload or {}
    overlays = {
        "vwap": bot_app.vwap_value,
        "swing_high_1h": features.get("swing_high_1h"),
        "swing_low_1h": features.get("swing_low_1h"),
        "swing_high_15m": features.get("swing_high_15m"),
        "swing_low_15m": features.get("swing_low_15m"),
        "entry": last_signal.get("entry"),
        "sl": last_signal.get("sl"),
        "tp1": last_signal.get("tp1"),
        "tp2": last_signal.get("tp2"),
    }
    return JSONResponse(
        {
            "points": list(bot_app.price_history),
            "overlays": overlays,
        }
    )


@app.get("/api/logs")
async def logs(limit: int = 120) -> JSONResponse:
    limit = max(1, min(limit, 500))
    return JSONResponse({"logs": list(bot_app.log_buffer.records)[-limit:]})


@app.get("/api/signals")
async def signals(limit: int = 20) -> JSONResponse:
    limit = max(1, min(limit, 200))
    return JSONResponse({"signals": list(bot_app.recent_signals)[-limit:]})


@app.get("/api/stream")
async def stream() -> StreamingResponse:
    async def event_generator():
        while True:
            payload = build_state_payload()
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
