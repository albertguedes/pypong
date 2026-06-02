import logging
import sys
import json
from datetime import datetime, timezone
from uuid import UUID


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "level": record.levelname,
            "ts": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_data["trace_id"] = record.request_id
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data)


def setup_logging(name: str = "pypong", level: int = logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    return logger


def get_log_extra(request_id: str = None, **kwargs):
    extra = {k: v for k, v in kwargs.items() if v is not None}
    if request_id:
        extra["trace_id"] = request_id
    return extra
