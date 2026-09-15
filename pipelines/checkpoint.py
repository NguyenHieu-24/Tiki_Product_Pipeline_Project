import json
import os
from pathlib import Path

from config import MAIN_CHECKPOINT_FILE, RETRY_CHECKPOINT_FILE


def _load(path):
    path = Path(path)
    if not path.exists():
        return {"last_batch": 0}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return {"last_batch": int(data.get("last_batch", 0))}


def _save(path, batch_index):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({"last_batch": int(batch_index)}, f, indent=2)

    os.replace(tmp_path, path)


def load_checkpoint():
    return _load(MAIN_CHECKPOINT_FILE)


def save_checkpoint(batch_index):
    _save(MAIN_CHECKPOINT_FILE, batch_index)


def load_retry_checkpoint():
    return _load(RETRY_CHECKPOINT_FILE)


def save_retry_checkpoint(batch_index):
    _save(RETRY_CHECKPOINT_FILE, batch_index)
