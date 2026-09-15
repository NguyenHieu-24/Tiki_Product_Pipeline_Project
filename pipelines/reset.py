import shutil
from pathlib import Path

from config import (
    CHECKPOINT_DIR,
    ERROR_DIR,
    ERROR_FINAL_DIR,
    FINAL_DIR,
    OUTPUT_DIR,
    OUTPUT_RETRY_DIR,
    RETRY_CHECKPOINT_FILE,
)


def _clear_dir(path):
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def reset_main_pipeline():
    """
    Fresh main run:
    clears main output, main errors and checkpoints.
    Also clears retry/final derived outputs because they belong to the old run.
    """
    for path in [
        OUTPUT_DIR,
        ERROR_DIR,
        CHECKPOINT_DIR,
        OUTPUT_RETRY_DIR,
        ERROR_FINAL_DIR,
        FINAL_DIR,
    ]:
        _clear_dir(path)


def reset_retry_pipeline():
    """
    Fresh retry run:
    keeps the main output/errors, but clears retry-derived state.
    """
    for path in [OUTPUT_RETRY_DIR, ERROR_FINAL_DIR]:
        _clear_dir(path)

    retry_checkpoint = Path(RETRY_CHECKPOINT_FILE)
    if retry_checkpoint.exists():
        retry_checkpoint.unlink()


def reset_final_output():
    _clear_dir(FINAL_DIR)
