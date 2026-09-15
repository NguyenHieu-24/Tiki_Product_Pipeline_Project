import argparse
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from math import ceil

# Helps avoid noisy Proactor transport cleanup messages on some
# Windows + Python 3.10 aiohttp environments.
if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import aiohttp
from tqdm import tqdm

from config import (
    BATCH_SIZE,
    CSV_FILE,
    MAX_CONNECTIONS,
    MAX_WORKERS,
    OUTPUT_DIR,
)
from pipelines.checkpoint import load_checkpoint, save_checkpoint
from pipelines.error_handler import write_failed_batch
from pipelines.fetcher import fetch_batch
from pipelines.loader import load_product_ids
from pipelines.monitor import RunMonitor, send_alert, write_status
from pipelines.reset import reset_main_pipeline
from pipelines.transformer import transform
from pipelines.writer import count_saved_records, write_batch


def parse_args():
    parser = argparse.ArgumentParser(description="Tiki main product pipeline")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete previous main/retry/final runtime state and start from batch 1.",
    )
    return parser.parse_args()


async def run_main(reset=False):
    if reset:
        print("[RESET] Clearing previous runtime state...")
        reset_main_pipeline()

    monitor = RunMonitor()

    product_ids = load_product_ids(CSV_FILE)
    if not product_ids:
        raise RuntimeError(f"No valid product IDs found in {CSV_FILE}")

    total_batches = ceil(len(product_ids) / BATCH_SIZE)
    checkpoint = load_checkpoint()
    start_batch = checkpoint["last_batch"] + 1

    print(f"TOTAL VALID PRODUCT IDs: {len(product_ids):,}")
    print(f"TOTAL BATCHES: {total_batches:,}")
    print(f"START BATCH: {start_batch:,}")

    write_status(
        "Main pipeline started",
        {
            "product_ids": len(product_ids),
            "total_batches": total_batches,
            "start_batch": start_batch,
        },
    )

    if start_batch > total_batches:
        total_saved = count_saved_records(OUTPUT_DIR)
        print("MAIN PIPELINE ALREADY COMPLETED.")
        print(f"TOTAL SAVED RECORDS: {total_saved:,}")
        return

    connector = aiohttp.TCPConnector(limit=MAX_CONNECTIONS)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        async with aiohttp.ClientSession(connector=connector) as session:
            progress = tqdm(
                total=total_batches,
                initial=start_batch - 1,
                desc="Main batches",
            )

            try:
                for batch_index in range(start_batch, total_batches + 1):
                    start = (batch_index - 1) * BATCH_SIZE
                    batch_ids = product_ids[start:start + BATCH_SIZE]

                    results = await fetch_batch(session, batch_ids)

                    successful_raw = [
                        result["data"]
                        for result in results
                        if result["error"] is None
                    ]
                    failed_results = [
                        result
                        for result in results
                        if result["error"] is not None
                    ]

                    loop = asyncio.get_running_loop()
                    transformed = await asyncio.gather(
                        *[
                            loop.run_in_executor(executor, transform, data)
                            for data in successful_raw
                        ]
                    )
                    transformed = [item for item in transformed if item is not None]

                    output_path = write_batch(
                        transformed,
                        batch_index,
                        OUTPUT_DIR,
                    )
                    write_failed_batch(failed_results, batch_index)

                    # Checkpoint last: a batch is complete only after all artifacts exist.
                    save_checkpoint(batch_index)
                    monitor.record_batch(len(transformed), len(failed_results))

                    print(
                        f"[Batch {batch_index}/{total_batches}] "
                        f"requested={len(batch_ids)} | "
                        f"collected={len(transformed)} | "
                        f"failed={len(failed_results)} | "
                        f"elapsed={monitor.elapsed_seconds():.1f}s | "
                        f"saved={output_path.name}"
                    )
                    progress.update(1)

            finally:
                progress.close()

    # Let aiohttp transports finish clean shutdown before asyncio.run closes the loop.
    await asyncio.sleep(0.25)

    run_summary = monitor.summary()
    total_saved = count_saved_records(OUTPUT_DIR)

    print("\nMAIN PIPELINE FINISHED")
    print(f"RUN COLLECTED: {run_summary['run_collected']:,}")
    print(f"RUN FAILED: {run_summary['run_failed']:,}")
    print(f"TOTAL SAVED RECORDS: {total_saved:,}")
    print(f"PROCESSING TIME: {run_summary['elapsed_seconds']:.2f} seconds")

    write_status(
        "Main pipeline finished",
        {
            "run_collected": run_summary["run_collected"],
            "run_failed": run_summary["run_failed"],
            "total_saved": total_saved,
            "elapsed_seconds": round(run_summary["elapsed_seconds"], 2),
        },
    )


async def main():
    args = parse_args()

    try:
        await run_main(reset=args.reset)
    except KeyboardInterrupt:
        send_alert("Main pipeline interrupted by user (KeyboardInterrupt).")
        raise
    except Exception as exc:
        send_alert(
            "Main pipeline crashed",
            {"error_type": type(exc).__name__, "error": str(exc)},
        )
        raise


if __name__ == "__main__":
    asyncio.run(main())
