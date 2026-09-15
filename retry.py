import argparse
import asyncio
import sys

if sys.platform.startswith("win") and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from pipelines.monitor import RunMonitor, send_alert, write_status
from pipelines.reset import reset_retry_pipeline
from pipelines.retry_loader import load_failed_ids
from pipelines.retry_runner import run_retry


def parse_args():
    parser = argparse.ArgumentParser(description="Retry failed Tiki product IDs")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear retry output/final errors/retry checkpoint and retry from the beginning.",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    if args.reset:
        print("[RESET RETRY] Clearing previous retry state...")
        reset_retry_pipeline()

    monitor = RunMonitor()
    failed_records = load_failed_ids()

    if not failed_records:
        print("NO RETRYABLE FAILED IDs FOUND.")
        return

    print(f"RETRYABLE FAILED IDs: {len(failed_records):,}")
    write_status(
        "Retry pipeline started",
        {"retryable_ids": len(failed_records)},
    )

    try:
        result = await run_retry(failed_records)
        await asyncio.sleep(0.25)

        print("\nRETRY PIPELINE FINISHED")
        print(f"RECOVERED THIS RUN: {result['recovered']:,}")
        print(f"STILL FAILED THIS RUN: {result['failed']:,}")
        print(f"PROCESSING TIME: {monitor.elapsed_seconds():.2f} seconds")

        write_status(
            "Retry pipeline finished",
            {
                "recovered": result["recovered"],
                "still_failed": result["failed"],
                "elapsed_seconds": round(monitor.elapsed_seconds(), 2),
            },
        )

    except KeyboardInterrupt:
        send_alert("Retry pipeline interrupted by user (KeyboardInterrupt).")
        raise
    except Exception as exc:
        send_alert(
            "Retry pipeline crashed",
            {"error_type": type(exc).__name__, "error": str(exc)},
        )
        raise


if __name__ == "__main__":
    asyncio.run(main())
