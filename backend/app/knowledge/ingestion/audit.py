
import json
from datetime import datetime, timezone
from pathlib import Path


def write_audit_record(
    log_path: Path,
    record: dict,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        **record,
    }

    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload) + "\n")
