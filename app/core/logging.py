from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import Settings
from app.core.middleware import get_correlation_id

SENSITIVE_KEY_MARKERS = (
    "authorization",
    "cookie",
    "set-cookie",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "password",
)
REDACTION_PATTERNS = [
    re.compile(
        r"""(?ix)
        (["']?(?:authorization|cookie|set-cookie|token|access_token|refresh_token|secret|password)["']?\s*:\s*["'])
        (.*?)
        (["'])
        """
    ),
    re.compile(
        r"""(?ix)
        \b((?:authorization|cookie|set-cookie|token|access_token|refresh_token|secret|password)\b\s*[=:]\s*)
        ([^\n\r,&}]+)
        """
    ),
]
REDACTION_TOKEN = "***REDACTED***"


def _replace_sensitive_match(match: re.Match[str]) -> str:
    suffix = match.group(3) if match.lastindex and match.lastindex >= 3 else ""
    return match.group(1) + REDACTION_TOKEN + suffix


def _redact_string(value: str) -> str:
    redacted = value
    for pattern in REDACTION_PATTERNS:
        redacted = pattern.sub(_replace_sensitive_match, redacted)
    return redacted


def _is_sensitive_key(value: Any) -> bool:
    return isinstance(value, str) and any(marker in value.lower() for marker in SENSITIVE_KEY_MARKERS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_string(value)
    if isinstance(value, dict):
        return {
            key: REDACTION_TOKEN if _is_sensitive_key(key) else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact_value(record.msg)
        if record.args:
            record.args = _redact_value(record.args)
        return True


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(settings: Settings) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())
    handler.addFilter(CorrelationIdFilter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
