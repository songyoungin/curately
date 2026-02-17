import json
import logging

from backend.config import get_settings
from backend.main import _configure_logging


def test_settings_reads_log_format_from_env(monkeypatch) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.log_format == "json"


def test_configure_logging_uses_json_formatter(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    monkeypatch.setenv("LOG_FORMAT", "json")
    get_settings.cache_clear()

    _configure_logging()
    root = logging.getLogger()
    assert root.handlers
    formatter = root.handlers[0].formatter
    assert formatter is not None

    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    rendered = formatter.format(record)
    payload = json.loads(rendered)

    assert payload["message"] == "hello"
    assert payload["name"] == "test.logger"
    assert payload["levelname"] == "INFO"
