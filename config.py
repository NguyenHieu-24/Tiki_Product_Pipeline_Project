from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent

# Input / API
CSV_FILE = ROOT_DIR / "products_id.csv"
API_URL = "https://api.tiki.vn/product-detail/api/v1/products/{}"

# Runtime folders
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_RETRY_DIR = ROOT_DIR / "output_retry"
ERROR_DIR = ROOT_DIR / "errors"
ERROR_FINAL_DIR = ROOT_DIR / "errors_final"
CHECKPOINT_DIR = ROOT_DIR / "checkpoints"
FINAL_DIR = ROOT_DIR / "final"

MAIN_CHECKPOINT_FILE = CHECKPOINT_DIR / "progress.json"
RETRY_CHECKPOINT_FILE = CHECKPOINT_DIR / "retry_progress.json"

# Main pipeline
BATCH_SIZE = 1000
MAX_CONNECTIONS = 40
MAX_WORKERS = 8
REQUEST_TIMEOUT = 20
MAIN_MAX_ATTEMPTS = 2
MAIN_BACKOFF_BASE = 1.0

# HTTP statuses that are normally worth retrying.
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}

# Retry pipeline: deliberately slower / safer
RETRY_BATCH_SIZE = 100
RETRY_MAX_CONNECTIONS = 8
RETRY_MAX_ATTEMPTS = 3
RETRY_REQUEST_TIMEOUT = 30
RETRY_BACKOFF_BASE = 2.0
RETRY_BACKOFF_MAX = 20.0

# Auto-restart supervisor
AUTO_RESTART_MAX = 10
AUTO_RESTART_DELAY = 10

# Alert/status files.
# To sync to Google Drive Desktop, set environment variable GDRIVE_ALERT_DIR
# to a folder inside your Google Drive, e.g.
# GDRIVE_ALERT_DIR=G:\My Drive\tiki_pipeline_alerts
GDRIVE_ALERT_DIR = Path(
    os.getenv("GDRIVE_ALERT_DIR", str(ROOT_DIR / "gdrive_alert"))
)
