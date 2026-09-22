"""Tests for Safari tab import functionality."""

import asyncio

from nexus.applescript.builder import GET_ALL_TABS_SCRIPT
from nexus.core.safari import SafariController


def test_get_all_tabs_script_structure():
    """Verify GET_ALL_TABS_SCRIPT targets Safari and retrieves tab URLs and names."""
    assert 'tell application "Safari"' in GET_ALL_TABS_SCRIPT
    assert "repeat with w in windows" in GET_ALL_TABS_SCRIPT
    assert "repeat with t in tabs of w" in GET_ALL_TABS_SCRIPT
    assert "tabURL" in GET_ALL_TABS_SCRIPT
    assert "tabTitle" in GET_ALL_TABS_SCRIPT


def test_import_safari_tabs_success(monkeypatch):
    """Verify tabs are parsed into structured dicts with titles and URLs."""
    raw_output = (
        "GitHub\thttps://github.com\n"
        "Apple Developer\thttps://developer.apple.com/macos\n"
        "Duplicate\thttps://github.com\n"
        "NoTitle\thttps://news.ycombinator.com\n"
        "InvalidScheme\tjavascript:void(0)\n"
    )

    async def fake_status():
        return True

    async def fake_run_script(script):
        assert script == GET_ALL_TABS_SCRIPT
        return raw_output, "", 0

    monkeypatch.setattr("nexus.core.safari.check_safari_status", fake_status)
    monkeypatch.setattr("nexus.core.safari.run_applescript", fake_run_script)

    tabs = asyncio.run(SafariController.import_safari_tabs())

    assert len(tabs) == 3
    assert tabs[0] == {"title": "GitHub", "url": "https://github.com"}
    assert tabs[1] == {"title": "Apple Developer", "url": "https://developer.apple.com/macos"}
    assert tabs[2] == {"title": "NoTitle", "url": "https://news.ycombinator.com"}


def test_import_safari_tabs_safari_not_ready(monkeypatch):
    """Verify empty list when Safari is not available."""
    async def fake_status():
        return False

    monkeypatch.setattr("nexus.core.safari.check_safari_status", fake_status)
    tabs = asyncio.run(SafariController.import_safari_tabs())
    assert tabs == []


def test_import_safari_tabs_nonzero_exit(monkeypatch):
    """Verify empty list when AppleScript exits with error."""
    async def fake_status():
        return True

    async def fake_run_script(script):
        return "", "Safari not running", 1

    monkeypatch.setattr("nexus.core.safari.check_safari_status", fake_status)
    monkeypatch.setattr("nexus.core.safari.run_applescript", fake_run_script)

    tabs = asyncio.run(SafariController.import_safari_tabs())
    assert tabs == []
