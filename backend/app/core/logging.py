import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Attributes every stdlib LogRecord has by default — anything else set via
# `logger.info(..., extra={...})` is "extra" and gets folded into the JSON output.
_STANDARD_RECORD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__.keys())


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_ATTRS
        }
        if extra:
            payload.update(extra)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Configure the root logger to emit single-line JSON to stdout.

    Lambda ships stdout to CloudWatch Logs automatically, so no separate log
    handler/transport is needed for either local `uvicorn` runs or Lambda.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
