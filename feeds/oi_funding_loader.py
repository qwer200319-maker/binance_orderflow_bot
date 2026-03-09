from __future__ import annotations

import aiohttp


async def fetch_open_interest(session: aiohttp.ClientSession, rest_base_url: str, symbol: str) -> float:
    url = f"{rest_base_url}/fapi/v1/openInterest"
    params = {"symbol": symbol.upper()}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        payload = await resp.json()
        return float(payload.get("openInterest", 0.0))


async def fetch_funding_rate(session: aiohttp.ClientSession, rest_base_url: str, symbol: str) -> float:
    url = f"{rest_base_url}/fapi/v1/fundingRate"
    params = {"symbol": symbol.upper(), "limit": 1}
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
        resp.raise_for_status()
        payload = await resp.json()
        if not payload:
            return 0.0
        return float(payload[-1].get("fundingRate", 0.0))
