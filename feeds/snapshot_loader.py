from __future__ import annotations

import aiohttp


async def fetch_depth_snapshot(session: aiohttp.ClientSession, rest_base_url: str, symbol: str, limit: int = 1000) -> dict:
    url = f"{rest_base_url}/fapi/v1/depth"
    params = {"symbol": symbol.upper(), "limit": limit}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        return await resp.json()
