import asyncio
import random

import aiohttp

from config import (
    API_URL,
    MAIN_BACKOFF_BASE,
    MAIN_MAX_ATTEMPTS,
    REQUEST_TIMEOUT,
    RETRYABLE_HTTP_STATUS,
)


async def _sleep_backoff(attempt, base):
    delay = base * (2 ** (attempt - 1))
    delay += random.uniform(0.0, min(1.0, delay * 0.25))
    await asyncio.sleep(delay)


async def fetch_product(session, product_id):
    """
    Fetch one product. Transient errors are retried a small number of times.

    Returns:
        {
            "product_id": "...",
            "data": dict | None,
            "error": str | None,
            "status": int | None,
            "attempts": int
        }
    """
    url = API_URL.format(product_id)
    last_error = None
    last_status = None

    for attempt in range(1, MAIN_MAX_ATTEMPTS + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

            async with session.get(url, timeout=timeout) as response:
                last_status = response.status

                if response.status == 200:
                    try:
                        data = await response.json(content_type=None)
                        return {
                            "product_id": str(product_id),
                            "data": data,
                            "error": None,
                            "status": 200,
                            "attempts": attempt,
                        }
                    except Exception as exc:
                        last_error = f"Invalid JSON: {exc}"
                        if attempt < MAIN_MAX_ATTEMPTS:
                            await _sleep_backoff(attempt, MAIN_BACKOFF_BASE)
                            continue

                elif response.status in RETRYABLE_HTTP_STATUS:
                    last_error = f"HTTP {response.status}"

                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        await asyncio.sleep(min(int(retry_after), 30))
                    elif attempt < MAIN_MAX_ATTEMPTS:
                        await _sleep_backoff(attempt, MAIN_BACKOFF_BASE)

                    continue

                else:
                    # 404/400/etc. normally will not improve by immediate retry.
                    return {
                        "product_id": str(product_id),
                        "data": None,
                        "error": f"HTTP {response.status}",
                        "status": response.status,
                        "attempts": attempt,
                    }

        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            last_status = None

            if attempt < MAIN_MAX_ATTEMPTS:
                await _sleep_backoff(attempt, MAIN_BACKOFF_BASE)
                continue

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            last_status = None
            break

    return {
        "product_id": str(product_id),
        "data": None,
        "error": last_error or "Unknown fetch error",
        "status": last_status,
        "attempts": MAIN_MAX_ATTEMPTS,
    }


async def fetch_batch(session, product_ids):
    tasks = [fetch_product(session, pid) for pid in product_ids]
    return await asyncio.gather(*tasks)
