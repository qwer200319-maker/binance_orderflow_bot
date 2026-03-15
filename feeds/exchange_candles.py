from __future__ import annotations

import asyncio
from typing import List

import aiohttp

FALLBACK_REST_BASE = "https://fstream.binance.com"


def _normalize_binance(rows: List[list]) -> List[dict]:
    candles: List[dict] = []
    for row in rows:
        try:
            open_time = int(row[0])
            candles.append(
                {
                    "time": open_time // 1000,
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
            )
        except (TypeError, ValueError, IndexError):
            continue
    return candles


async def _fetch_klines(
    session: aiohttp.ClientSession,
    base_url: str,
    symbol: str,
    interval: str,
    limit: int,
) -> List[dict]:
    url = f"{base_url}/fapi/v1/klines"
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        payload = await resp.json()
        return _normalize_binance(payload)


async def fetch_binance_candles(
    session: aiohttp.ClientSession,
    rest_base_url: str,
    symbol: str,
    interval: str,
    limit: int,
) -> List[dict]:
    try:
        return await _fetch_klines(session, rest_base_url, symbol, interval, limit)
    except (aiohttp.ClientResponseError, aiohttp.ClientConnectorError, asyncio.TimeoutError) as exc:
        fallback = FALLBACK_REST_BASE
        if rest_base_url.rstrip("/") == fallback:
            raise
        return await _fetch_klines(session, fallback, symbol, interval, limit)
