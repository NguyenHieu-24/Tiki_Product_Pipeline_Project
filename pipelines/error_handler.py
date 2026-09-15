import json
import os
from datetime import datetime, timezone
from pathlib import Path

from config import ERROR_DIR, ERROR_FINAL_DIR


def _atomic_dump(records, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        # Remove a stale error file if this batch now succeeds.
        if path.exists():
            path.unlink()
        return path

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    os.replace(tmp_path, path)
    return path


def build_error_record(result, batch_index, stage):
    return {
        "product_id": str(result.get("product_id")),
        "batch": int(batch_index),
        "stage": stage,
        "status": result.get("status"),
        "attempts": result.get("attempts"),
        "error": result.get("error"),
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_failed_batch(failed_results, batch_index):
    records = [
        build_error_record(r, batch_index, "fetch")
        for r in failed_results
    ]
    path = Path(ERROR_DIR) / f"failed_batch_{batch_index}.json"
    return _atomic_dump(records, path)


def write_final_failed_batch(failed_results, batch_index):
    records = [
        build_error_record(r, batch_index, "retry")
        for r in failed_results
    ]
    path = Path(ERROR_FINAL_DIR) / f"final_failed_batch_{batch_index}.json"
    return _atomic_dump(records, path)
