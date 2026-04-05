import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

LOG_PATH = os.getenv("PRED_LOG_PATH", "app/assets/pred_log.csv")

def append_log(row: Dict[str, Any]) -> None:
    path = Path(LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()

    payload = dict(row)
    payload["timestamp"] = payload.get("timestamp") or datetime.utcnow().isoformat()

    fieldnames = [
        "timestamp","label","prob_hoax","tau","used_ocr","ocr_type",
        "title_len","body_len","ocr_len","text_len",
    ]
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if is_new:
            writer.writeheader()
        writer.writerow({k: payload.get(k, "") for k in fieldnames})
