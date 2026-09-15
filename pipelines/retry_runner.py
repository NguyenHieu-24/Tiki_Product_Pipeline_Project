import asyncio
from concurrent.futures import ThreadPoolExecutor
from math import ceil

import aiohttp
from tqdm import tqdm

from config import (
    MAX_WORKERS,
    OUTPUT_RETRY_DIR,
    RETRY_BATCH_SIZE,
    RETRY_MAX_CONNECTIONS,
)
from pipelines.checkpoint import (
    load_retry_checkpoint,
    save_retry_checkpoint,
)
from pipelines.error_handler import write_final_failed_batch
from pipelines.retry_fetcher import retry_fetch_batch
from pipelines.transformer import transform
from pipelines.writer import write_batch


async def run_retry(failed_records):
    if not failed_records:
        return {"recovered": 0, "failed": 0}

    total_batches = ceil(len(failed_records) / RETRY_BATCH_SIZE)
    checkpoint = load_retry_checkpoint()
    start_batch = checkpoint["last_batch"] + 1

    recovered_total = 0
    failed_total = 0

    connector = aiohttp.TCPConnector(limit=RETRY_MAX_CONNECTIONS)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        async with aiohttp.ClientSession(connector=connector) as session:
            progress = tqdm(
                total=total_batches,
                initial=min(start_batch - 1, total_batches),
                desc="Retry batches",
            )

            try:
                for batch_index in range(start_batch, total_batches + 1):
                    start = (batch_index - 1) * RETRY_BATCH_SIZE
                    batch = failed_records[start:start + RETRY_BATCH_SIZE]
                    ids = [str(record["product_id"]) for record in batch]

                    results = await retry_fetch_batch(session, ids)

                    successes = [r["data"] for r in results if r["error"] is None]
                    failures = [r for r in results if r["error"] is not None]

                    loop = asyncio.get_running_loop()
                    transformed = await asyncio.gather(
                        *[
                            loop.run_in_executor(executor, transform, data)
                            for data in successes
                        ]
                    )
                    transformed = [item for item in transformed if item is not None]

                    write_batch(
                        transformed,
                        batch_index,
                        OUTPUT_RETRY_DIR,
                        prefix="products_retry_batch",
                    )
                    write_final_failed_batch(failures, batch_index)

                    # Only checkpoint after success output and final-error output exist.
                    save_retry_checkpoint(batch_index)

                    recovered_total += len(transformed)
                    failed_total += len(failures)

                    print(
                        f"[Retry {batch_index}/{total_batches}] "
                        f"requested={len(ids)} | "
                        f"recovered={len(transformed)} | "
                        f"still_failed={len(failures)}"
                    )
                    progress.update(1)
            finally:
                progress.close()

    return {"recovered": recovered_total, "failed": failed_total}
