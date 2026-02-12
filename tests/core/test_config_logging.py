"""Tests for Nexus logging setup behavior."""

from __future__ import annotations

import importlib
from pathlib import Path

import nexus.core.config as config_module


def test_logging_is_lazy_on_import(monkeypatch) -> None:
    """Importing config should not initialize file handlers."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    reloaded = importlib.reload(config_module)

    assert reloaded._LOGGER_INITIALIZED is False
    assert reloaded.logger.name == "nexus"


def test_setup_logging_respects_override_dir(tmp_path: Path, monkeypatch) -> None:
    """setup_logging should write to NEXUS_LOG_DIR when provided."""
    monkeypatch.setenv("NEXUS_LOG_DIR", str(tmp_path))
    reloaded = importlib.reload(config_module)

    reloaded.setup_logging(force=True)

    assert reloaded._LOGGER_INITIALIZED is True
    assert (tmp_path / reloaded.Config.LOG_FILE).exists()
