import asyncio
import random

import aiohttp

from config import (
    API_URL,
    RETRY_BACKOFF_BASE,
    RETRY_BACKOFF_MAX,
    RETRY_MAX_ATTEMPTS,
    RETRY_REQUEST_TIMEOUT,
    RETRYABLE_HTTP_STATUS,
)


async def _backoff(attempt):
    delay = min(
        RETRY_BACKOFF_BASE * (2 ** (attempt - 1)),
        RETRY_BACKOFF_MAX,
    )
    delay += random.uniform(0.0, min(1.5, delay * 0.25))
    await asyncio.sleep(delay)


async def retry_fetch_product(session, product_id):
    url = API_URL.format(product_id)
    last_error = None
    last_status = None

    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            timeout = aiohttp.ClientTimeout(total=RETRY_REQUEST_TIMEOUT)

            async with session.get(url, timeout=timeout) as response:
                last_status = response.status

                if response.status == 200:
                    try:
                        return {
                            "product_id": str(product_id),
                            "data": await response.json(content_type=None),
                            "error": None,
                            "status": 200,
                            "attempts": attempt,
                        }
                    except Exception as exc:
                        last_error = f"Invalid JSON: {exc}"

                elif response.status in RETRYABLE_HTTP_STATUS:
                    last_error = f"HTTP {response.status}"

                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        await asyncio.sleep(min(int(retry_after), RETRY_BACKOFF_MAX))
                    elif attempt < RETRY_MAX_ATTEMPTS:
                        await _backoff(attempt)

                    continue

                else:
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

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            last_status = None
            break

        if attempt < RETRY_MAX_ATTEMPTS:
            await _backoff(attempt)

    return {
        "product_id": str(product_id),
        "data": None,
        "error": last_error or "Unknown retry error",
        "status": last_status,
        "attempts": RETRY_MAX_ATTEMPTS,
    }


async def retry_fetch_batch(session, product_ids):
    tasks = [retry_fetch_product(session, pid) for pid in product_ids]
    return await asyncio.gather(*tasks)
