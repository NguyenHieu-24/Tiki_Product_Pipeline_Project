import argparse
import json
from pathlib import Path

from config import FINAL_DIR, OUTPUT_DIR, OUTPUT_RETRY_DIR
from pipelines.reset import reset_final_output
from pipelines.writer import write_batch


FINAL_BATCH_SIZE = 1000


def iter_products():
    for directory, pattern in [
        (Path(OUTPUT_DIR), "products_batch_*.json"),
        (Path(OUTPUT_RETRY_DIR), "products_retry_batch_*.json"),
    ]:
        for path in sorted(directory.glob(pattern)):
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)

            if isinstance(records, list):
                for record in records:
                    yield record


def main():
    parser = argparse.ArgumentParser(
        description="Merge main + retry output and de-duplicate by product id."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear final/ before writing merged files.",
    )
    args = parser.parse_args()

    if args.reset:
        reset_final_output()

    seen_ids = set()
    buffer = []
    batch_index = 1
    total = 0
    duplicates = 0

    for product in iter_products():
        product_id = product.get("id")
        key = str(product_id)

        if product_id is None or key in seen_ids:
            duplicates += 1
            continue

        seen_ids.add(key)
        buffer.append(product)

        if len(buffer) >= FINAL_BATCH_SIZE:
            write_batch(
                buffer,
                batch_index,
                FINAL_DIR,
                prefix="products_final_batch",
            )
            total += len(buffer)
            batch_index += 1
            buffer = []

    if buffer:
        write_batch(
            buffer,
            batch_index,
            FINAL_DIR,
            prefix="products_final_batch",
        )
        total += len(buffer)

    print(f"FINAL UNIQUE PRODUCTS: {total:,}")
    print(f"SKIPPED DUPLICATES/INVALID IDs: {duplicates:,}")
    print(f"FINAL OUTPUT: {FINAL_DIR}")


if __name__ == "__main__":
    main()
