"""Tests for Safari AppleScript modules (builder + poller)."""

import asyncio

from nexus.applescript import builder
from nexus.applescript.builder import escape_string
from nexus.applescript.poller import check_safari_status, wait_for_safari_ready


class _DummyProcess:
    def __init__(
        self, returncode: int, stdout: bytes = b"", stderr: bytes = b""
    ) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


def test_escape_applescript_string():
    """Escape quotes, backslashes, and control characters for AppleScript."""
    raw = 'https://example.com/path?"x"=1\\2\nnext\rline'
    escaped = escape_string(raw)

    assert '\\"' in escaped
    assert "\\\\" in escaped
    assert "\\n" in escaped
    assert "\\r" in escaped


def test_check_safari_status_fails_when_launch_fails(monkeypatch):
    """Return False when Safari launch returns non-zero."""
    processes = [
        _DummyProcess(returncode=0, stdout=b"false\n"),
        _DummyProcess(returncode=1, stderr=b"launch failed"),
    ]

    async def fake_create_subprocess_exec(*args, **kwargs):
        return processes.pop(0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    result = asyncio.run(check_safari_status())

    assert result is False


def test_wait_for_safari_ready_retries_until_success(monkeypatch):
    """Retry polling until Safari responds successfully."""
    attempt = {"count": 0}

    async def fake_create_subprocess_exec(*args, **kwargs):
        attempt["count"] += 1
        if attempt["count"] < 3:
            return _DummyProcess(returncode=1, stderr=b"not ready")
        return _DummyProcess(returncode=0, stdout=b"1\n")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    ready = asyncio.run(wait_for_safari_ready(attempts=5, delay_seconds=0))

    assert ready is True
    assert attempt["count"] == 3


def test_build_batch_script_creates_window_for_first_url():
    """First URL opens a new window; rest become tabs."""
    script = builder.build_batch_script(
        ["https://a.com", "https://b.com"], create_window=True
    )
    assert "make new document" in script
    assert "make new tab" in script


def test_build_batch_script_tabs_only():
    """All URLs become tabs when create_window is False."""
    script = builder.build_batch_script(
        ["https://a.com", "https://b.com"], create_window=False
    )
    assert "make new document" not in script
    assert "make new tab" in script


def test_build_batch_script_empty_returns_empty():
    """Empty URL list produces empty script string."""
    assert builder.build_batch_script([]) == ""
