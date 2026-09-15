import json
import os
from pathlib import Path


def _atomic_json_dump(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(tmp_path, path)


def write_batch(data, batch_index, output_dir, prefix="products_batch"):
    output_dir = Path(output_dir)
    path = output_dir / f"{prefix}_{batch_index}.json"
    _atomic_json_dump(data, path)
    return path


def count_saved_records(output_dir, pattern="products_batch_*.json"):
    total = 0
    output_dir = Path(output_dir)

    for path in sorted(output_dir.glob(pattern)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
            if isinstance(records, list):
                total += len(records)
        except Exception:
            # A corrupt file should be investigated separately; do not hide the run.
            continue

    return total
