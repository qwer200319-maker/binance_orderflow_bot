from __future__ import annotations

from typing import List

import aiohttp


def _parse_kline(row: list) -> dict:
    return {
        "open_time": int(row[0]),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": float(row[5]),
        "close_time": int(row[6]),
    }


async def fetch_klines(
    session: aiohttp.ClientSession,
    rest_base_url: str,
    symbol: str,
    interval: str,
    limit: int,
) -> List[dict]:
    url = f"{rest_base_url}/fapi/v1/klines"
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        payload = await resp.json()
        return [_parse_kline(row) for row in payload]
