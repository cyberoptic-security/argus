import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def get_with_backoff(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_retries: int = 3,
    initial_delay: float = 2.0,
) -> httpx.Response:
    """GET request with exponential backoff on HTTP 429 responses."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        resp = await client.get(url, params=params, headers=headers or {})
        if resp.status_code != 429:
            return resp
        if attempt < max_retries:
            logger.warning(
                "rate limited by %s (attempt %d/%d), retrying in %.0fs",
                url, attempt + 1, max_retries, delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
    return resp
