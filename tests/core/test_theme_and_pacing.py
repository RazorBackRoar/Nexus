"""Tests for DomainPacer and ThemeManager."""

from __future__ import annotations

import asyncio
from typing import cast

from PySide6.QtWidgets import QApplication, QWidget

from nexus.core.pacing import DomainPacer
from nexus.gui.theme import DARK_TOKENS, LIGHT_TOKENS, ThemeManager, get_theme_manager
from nexus.gui.widgets import BookmarkSearchBar, URLTableWidget, WindowTitleBar


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


# ============================================================================
# DomainPacer Tests
# ============================================================================


def test_domain_pacer_extract_domain():
    pacer = DomainPacer()
    assert pacer.extract_domain("https://example.com/path?query=1") == "example.com"
    assert pacer.extract_domain("https://SUB.DOMAIN.ORG/test") == "sub.domain.org"
    assert pacer.extract_domain("invalid-url") == "unknown"


def test_domain_pacer_group_by_domain():
    pacer = DomainPacer()
    urls = [
        "https://github.com/repo1",
        "https://apple.com/mac",
        "https://github.com/repo2",
        "https://google.com/search",
    ]
    groups = pacer.group_by_domain(urls)
    assert len(groups) == 3
    assert len(groups["github.com"]) == 2
    assert groups["github.com"] == [
        "https://github.com/repo1",
        "https://github.com/repo2",
    ]
    assert groups["apple.com"] == ["https://apple.com/mac"]


def test_domain_pacer_delays(monkeypatch):
    monkeypatch.setattr("random.uniform", lambda a, b: (a + b) / 2)
    pacer = DomainPacer(
        same_domain_delay_min=2.0,
        same_domain_delay_max=3.0,
        different_domain_delay=0.2,
    )
    same_delay_0 = pacer.get_same_domain_delay(batch_index=0)
    assert 2.0 <= same_delay_0 <= 3.5

    same_delay_2 = pacer.get_same_domain_delay(batch_index=2)
    assert same_delay_2 > same_delay_0

    cross_delay = pacer.get_cross_domain_delay()
    assert 0.2 <= cross_delay <= 0.45


def test_domain_pacer_calculate_backoff():
    b1 = DomainPacer.calculate_backoff(attempt=1, base_delay=2.0, max_delay=10.0)
    assert 2.0 <= b1 <= 3.0

    b2 = DomainPacer.calculate_backoff(attempt=2, base_delay=2.0, max_delay=10.0)
    assert 4.0 <= b2 <= 5.0

    b5 = DomainPacer.calculate_backoff(attempt=5, base_delay=2.0, max_delay=10.0)
    assert 10.0 <= b5 <= 11.0


def test_domain_pacer_wait_for_domain():
    async def _runner():
        pacer = DomainPacer(same_domain_delay_min=0.1, same_domain_delay_max=0.2)
        # First request: immediate (no previous dispatch recorded)
        slept = await pacer.wait_for_domain("example.com")
        assert slept == 0.0

        # Immediate second request to same domain should wait
        slept2 = await pacer.wait_for_domain("example.com")
        assert slept2 > 0.0

        pacer.reset()
        assert len(pacer._last_domain_dispatch) == 0

    asyncio.run(_runner())


# ============================================================================
# ThemeManager Tests
# ============================================================================


def test_theme_manager_toggle_and_tokens():
    tm = ThemeManager()
    assert tm.is_dark is True
    assert tm.tokens == DARK_TOKENS

    events: list[str] = []
    tm.theme_changed.connect(lambda mode: events.append(mode))

    new_mode = tm.toggle_theme()
    assert new_mode == "light"
    assert tm.is_dark is False
    assert tm.tokens == LIGHT_TOKENS
    assert events == ["light"]

    tm.set_mode("dark")
    assert tm.is_dark is True
    assert tm.tokens == DARK_TOKENS
    assert events == ["light", "dark"]


def test_global_theme_manager_singleton():
    tm1 = get_theme_manager()
    tm2 = get_theme_manager()
    assert tm1 is tm2


# ============================================================================
# Widget Integration Tests
# ============================================================================


def test_search_bar_debounced_signal():
    _app()
    search = BookmarkSearchBar()
    received: list[str] = []
    search.debounced_text_changed.connect(lambda t: received.append(t))

    search.setText("nexus")
    assert search.text() == "nexus"
    QApplication.processEvents()


def test_url_table_batched_replace():
    _app()
    table = URLTableWidget()
    urls = [f"https://example{i}.com" for i in range(100)]
    table.replace_urls(urls)
    assert table.rowCount() == 100
    assert len(table.get_all_urls()) == 100


def test_window_titlebar_theme_toggle():
    _app()
    dummy = QWidget()
    bar = WindowTitleBar(dummy)
    assert hasattr(bar, "theme_toggle")
    assert bar.theme_toggle is not None
