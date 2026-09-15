import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from config import GDRIVE_ALERT_DIR


class RunMonitor:
    def __init__(self):
        self.started_at = time.perf_counter()
        self.collected = 0
        self.failed = 0

    def record_batch(self, success_count, failed_count):
        self.collected += int(success_count)
        self.failed += int(failed_count)

    def elapsed_seconds(self):
        return time.perf_counter() - self.started_at

    def summary(self):
        return {
            "run_collected": self.collected,
            "run_failed": self.failed,
            "elapsed_seconds": self.elapsed_seconds(),
        }


def _write_alert_file(kind, message, extra=None):
    target_dir = Path(GDRIVE_ALERT_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    payload = {
        "type": kind,
        "time_utc": now.isoformat(),
        "message": message,
    }
    if extra:
        payload.update(extra)

    safe_ts = now.strftime("%Y%m%d_%H%M%S_%f")
    path = target_dir / f"{kind}_{safe_ts}.json"

    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    os.replace(tmp, path)
    return path


def send_alert(message, extra=None):
    return _write_alert_file("ALERT", message, extra)


def write_status(message, extra=None):
    return _write_alert_file("STATUS", message, extra)
