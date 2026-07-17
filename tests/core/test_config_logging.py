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


def test_setup_logging_skips_file_handler_without_opt_in(
    tmp_path: Path, monkeypatch
) -> None:
    """setup_logging should not persist logs unless explicitly enabled."""
    monkeypatch.delenv("NEXUS_LOG_DIR", raising=False)
    monkeypatch.delenv("NEXUS_ENABLE_FILE_LOGGING", raising=False)
    monkeypatch.setattr(config_module, "_resolve_log_dir", lambda: tmp_path)
    reloaded = importlib.reload(config_module)

    reloaded.setup_logging(force=True)

    assert reloaded._LOGGER_INITIALIZED is True
    assert not (tmp_path / reloaded.Config.LOG_FILE).exists()


def test_setup_logging_honors_file_logging_opt_in(tmp_path: Path, monkeypatch) -> None:
    """setup_logging should persist logs when explicitly opted in."""
    monkeypatch.delenv("NEXUS_LOG_DIR", raising=False)
    monkeypatch.setenv("NEXUS_ENABLE_FILE_LOGGING", "1")
    reloaded = importlib.reload(config_module)
    monkeypatch.setattr(reloaded, "_resolve_log_dir", lambda: tmp_path)

    reloaded.setup_logging(force=True)

    assert reloaded._LOGGER_INITIALIZED is True
    assert (tmp_path / reloaded.Config.LOG_FILE).exists()


def test_bookmark_groups_file_constant_present():
    """The new sidecar file is wired into Config."""
    from nexus.core.config import Config
    assert Config.BOOKMARK_GROUPS_FILE == "bookmark_groups.json"
