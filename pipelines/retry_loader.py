import json
import re
from pathlib import Path

from config import ERROR_DIR, RETRYABLE_HTTP_STATUS


def detect_status(record):
    """
    Lấy HTTP status từ field status.
    Nếu file error cũ không có status thì thử đọc từ error text.
    """
    status = record.get("status")

    if status is not None:
        try:
            return int(status)
        except (TypeError, ValueError):
            pass

    error = str(record.get("error", ""))

    match = re.search(r"HTTP\s+(\d{3})", error, re.IGNORECASE)

    if match:
        return int(match.group(1))

    return None


def is_retryable(record):
    """
    Xác định lỗi nào đáng retry.
    """

    status = detect_status(record)
    error = str(record.get("error", "")).lower()

    # =====================================
    # 1. Invalid JSON -> RETRY
    # =====================================
    #
    # Ví dụ:
    # HTTP 200 nhưng response rỗng / không phải JSON
    #
    invalid_json_keywords = [
        "invalid json",
        "expecting value",
        "jsondecodeerror",
        "unexpected end of json",
    ]

    if any(keyword in error for keyword in invalid_json_keywords):
        return True

    # =====================================
    # 2. Network / timeout -> RETRY
    # =====================================

    network_keywords = [
        "timeout",
        "timeouterror",
        "connection",
        "connection reset",
        "disconnect",
        "server disconnected",
        "clienterror",
        "clientconnectorerror",
        "clientoserror",
    ]

    if any(keyword in error for keyword in network_keywords):
        return True

    # =====================================
    # 3. Không xác định status -> RETRY
    # =====================================

    if status is None:
        return True

    # =====================================
    # 4. HTTP transient errors -> RETRY
    # =====================================

    if status in RETRYABLE_HTTP_STATUS:
        return True

    # =====================================
    # 5. Permanent errors -> KHÔNG retry
    # =====================================

    return False


def load_failed_ids(error_dir=ERROR_DIR):
    """
    Load tất cả errors/*.json.

    - Chỉ lấy lỗi retryable
    - Deduplicate product_id
    - Hỗ trợ JSON list và JSON object
    """

    records_by_id = {}

    paths = sorted(Path(error_dir).glob("*.json"))

    print(f"[RETRY LOADER] Error files found: {len(paths)}")

    total_records = 0
    retryable_count = 0
    skipped_count = 0

    for path in paths:

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = json.load(f)

        except Exception as e:
            print(
                f"[WARNING] Cannot read {path.name}: {e}"
            )
            continue

        if isinstance(content, dict):
            records = [content]

        elif isinstance(content, list):
            records = content

        else:
            print(
                f"[WARNING] Invalid JSON structure: {path.name}"
            )
            continue

        for record in records:

            total_records += 1

            pid = (
                record.get("product_id")
                or record.get("id")
                or record.get("pid")
            )

            if pid is None:
                skipped_count += 1
                continue

            pid = str(pid).strip()

            if not pid:
                skipped_count += 1
                continue

            if not is_retryable(record):
                skipped_count += 1
                continue

            retryable_count += 1

            # Chuẩn hóa lại record
            record["product_id"] = pid
            record["status"] = detect_status(record)

            # Deduplicate theo product_id
            records_by_id[pid] = record

    retry_records = list(records_by_id.values())

    print()
    print("========== RETRY LOADER SUMMARY ==========")
    print(f"Total error records   : {total_records}")
    print(f"Retryable records     : {retryable_count}")
    print(f"Unique retryable IDs  : {len(retry_records)}")
    print(f"Skipped/permanent     : {skipped_count}")
    print("==========================================")

    return retry_records