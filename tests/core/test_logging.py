from __future__ import annotations

import logging

from app.core.logging import JsonFormatter, RedactionFilter


def _render_log_output(*, msg, args=()) -> str:
    record = logging.LogRecord(
        name="tests.logging",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=None,
    )
    assert RedactionFilter().filter(record) is True
    return JsonFormatter().format(record)


def test_redaction_filter_masks_nested_header_values_inside_tuple_args() -> None:
    output = _render_log_output(
        msg="provider_request headers=%s",
        args=(
            {
                "Authorization": "Bearer super-secret",
                "Cookie": "sessionid=abc123; path=/",
                "nested": [{"token": "refresh-me"}],
            },
        ),
    )

    assert "***REDACTED***" in output
    assert "super-secret" not in output
    assert "sessionid=abc123" not in output
    assert "refresh-me" not in output


def test_redaction_filter_masks_header_style_strings() -> None:
    output = _render_log_output(
        msg='{"Authorization": "Bearer secret-1", "Cookie": "session=secret-2", "token": "secret-3"}',
    )

    assert "***REDACTED***" in output
    assert "secret-1" not in output
    assert "secret-2" not in output
    assert "secret-3" not in output
