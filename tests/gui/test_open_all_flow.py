"""Tests for Open All clipboard auto-paste, private mode toggle, and resilient URL launching."""

from __future__ import annotations

import asyncio
import os
from typing import cast

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from nexus.core.config import Config
from nexus.core.safari import SafariController
from nexus.gui import main_window as main_window_module
from nexus.gui.main_window import MainWindow


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def _make_window(tmp_path, monkeypatch) -> MainWindow:
    _app()

    class _TestPaths:
        class StandardLocation:
            AppDataLocation = object()

        @staticmethod
        def writableLocation(_location):
            return str(tmp_path)

    monkeypatch.setattr(main_window_module, "QStandardPaths", _TestPaths)
    monkeypatch.setattr(
        main_window_module,
        "QSettings",
        lambda: QSettings(str(tmp_path / "ui.ini"), QSettings.Format.IniFormat),
    )
    return MainWindow()


def test_default_private_mode_is_false():
    assert Config.DEFAULT_PRIVATE_MODE is False


def test_private_mode_toggle_switch(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    assert window.private_mode_enabled is False
    assert "Standard Safari" in window.private_mode_btn.text()

    window.private_mode_btn.click()
    assert window.private_mode_enabled is True
    assert "Private Safari" in window.private_mode_btn.text()

    window.private_mode_btn.click()
    assert window.private_mode_enabled is False
    assert "Standard Safari" in window.private_mode_btn.text()


def test_open_all_auto_pastes_from_clipboard_when_table_empty(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    assert window.url_table.rowCount() == 0

    # Put 34 links into clipboard
    raw_urls = [f"https://example{i:02d}.org/page" for i in range(34)]
    clipboard = QApplication.clipboard()
    assert clipboard is not None
    clipboard.setText("\n".join(raw_urls))

    launched_urls: list[list[str]] = []

    def fake_start_worker(worker):
        # Intercept worker fn arguments
        if hasattr(worker, "args") and worker.args:
            launched_urls.append(worker.args[0])

    monkeypatch.setattr(window, "_start_worker", fake_start_worker)

    window._run_urls_in_safari()

    # Verify all 34 URLs were loaded into table and launched
    assert window.url_table.rowCount() == 34
    assert len(launched_urls) == 1
    assert len(launched_urls[0]) == 34
    assert set(launched_urls[0]) == set(raw_urls)


def test_open_urls_fallback_when_private_mode_fails(tmp_path, monkeypatch):
    window = _make_window(tmp_path, monkeypatch)
    urls = [f"https://example{i}.org" for i in range(5)]

    calls: list[bool] = []

    async def fake_open_urls(batch, private_mode=False):
        calls.append(private_mode)
        if private_mode:
            # Simulate failure (e.g. System Events Accessibility denied)
            return False
        return True

    monkeypatch.setattr(window.safari_controller, "open_urls", fake_open_urls)

    res = asyncio.run(window._open_urls_with_tracking(urls, private_mode=True))
    assert res is True
    assert calls == [True, False]
    assert "Standard Safari" in window.status_bar.text()


def test_staggered_opening_slices_remaining_without_duplication(monkeypatch):
    batches: list[list[str]] = []

    async def fake_run_batch(batch, create_window=False, private_mode=False):
        batches.append(list(batch))
        return True

    monkeypatch.setattr(SafariController, "_run_batch", fake_run_batch)

    test_urls = [f"https://example.com/{i}" for i in range(25)]
    res = asyncio.run(
        SafariController._open_domain_urls_staggered(
            test_urls, domain="example.com", is_first_domain=True, private_mode=False
        )
    )
    assert res is True

    # Flatten batches
    flattened = [url for b in batches for url in b]
    assert len(flattened) == 25
    # Ensure no duplicates
    assert len(set(flattened)) == 25
    assert flattened == test_urls
