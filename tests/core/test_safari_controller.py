"""Tests for SafariController safety helpers."""

import asyncio

from nexus.core.safari import SafariController


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
    raw = 'https://example.com/path?"x"=1\\2\nnext\rline'
    escaped = SafariController._escape_applescript_string(raw)

    assert '\\"' in escaped
    assert "\\\\" in escaped
    assert "\\n" in escaped
    assert "\\r" in escaped


def test_check_safari_status_fails_when_launch_fails(monkeypatch):
    processes = [
        _DummyProcess(returncode=0, stdout=b"false\n"),
        _DummyProcess(returncode=1, stderr=b"launch failed"),
    ]

    async def fake_create_subprocess_exec(*args, **kwargs):
        return processes.pop(0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    result = asyncio.run(SafariController.check_safari_status())

    assert result is False


def test_wait_for_safari_ready_retries_until_success(monkeypatch):
    attempt = {"count": 0}

    async def fake_create_subprocess_exec(*args, **kwargs):
        attempt["count"] += 1
        if attempt["count"] < 3:
            return _DummyProcess(returncode=1, stderr=b"not ready")
        return _DummyProcess(returncode=0, stdout=b"1\n")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    ready = asyncio.run(SafariController._wait_for_safari_ready(attempts=5, delay_seconds=0))

    assert ready is True
    assert attempt["count"] == 3
