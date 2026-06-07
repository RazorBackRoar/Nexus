from __future__ import annotations

import asyncio

from nexus.core import safari
from nexus.core.safari import SafariController


def test_group_urls_by_domain_lowercases_domains() -> None:
    grouped = SafariController._group_urls_by_domain(
        [
            "https://Example.com/a",
            "https://example.com/b",
            "https://Other.test/path",
        ]
    )

    assert grouped == {
        "example.com": ["https://Example.com/a", "https://example.com/b"],
        "other.test": ["https://Other.test/path"],
    }


def test_open_urls_returns_false_for_empty_input() -> None:
    assert asyncio.run(SafariController.open_urls([])) is False


def test_open_urls_returns_false_when_safari_is_not_ready(monkeypatch) -> None:
    async def fake_check_safari_status() -> bool:
        return False

    monkeypatch.setattr(safari, "check_safari_status", fake_check_safari_status)

    assert asyncio.run(SafariController.open_urls(["https://example.com"])) is False


def test_open_urls_batches_plain_mode_and_sleeps_between_batches(
    monkeypatch,
) -> None:
    batches: list[tuple[list[str], bool, bool]] = []
    sleeps: list[float] = []

    async def fake_check_safari_status() -> bool:
        return True

    async def fake_run_batch(
        urls: list[str],
        *,
        create_window: bool = False,
        private_mode: bool = True,
    ) -> bool:
        batches.append((urls, create_window, private_mode))
        return True

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(safari, "check_safari_status", fake_check_safari_status)
    monkeypatch.setattr(SafariController, "_run_batch", fake_run_batch)
    monkeypatch.setattr(safari.random, "uniform", lambda _min, _max: 0.25)
    monkeypatch.setattr(safari.asyncio, "sleep", fake_sleep)

    result = asyncio.run(
        SafariController.open_urls(
            ["https://a.test", "https://b.test", "https://c.test"],
            max_batch_size=2,
            use_stealth=False,
            private_mode=False,
        )
    )

    assert result is True
    assert batches == [
        (["https://a.test", "https://b.test"], True, False),
        (["https://c.test"], True, False),
    ]
    assert sleeps == [0.25]


def test_open_urls_uses_stealth_grouping_when_enabled(monkeypatch) -> None:
    received_groups: list[dict[str, list[str]]] = []

    async def fake_check_safari_status() -> bool:
        return True

    async def fake_open_urls_with_stealth(
        domain_groups: dict[str, list[str]], private_mode: bool = True
    ) -> bool:
        received_groups.append(domain_groups)
        assert private_mode is False
        return True

    monkeypatch.setattr(safari, "check_safari_status", fake_check_safari_status)
    monkeypatch.setattr(safari.Config, "STEALTH_MODE", True)
    monkeypatch.setattr(
        SafariController, "_open_urls_with_stealth", fake_open_urls_with_stealth
    )

    result = asyncio.run(
        SafariController.open_urls(
            ["https://Example.com/a", "https://other.test"],
            use_stealth=True,
            private_mode=False,
        )
    )

    assert result is True
    assert received_groups == [
        {
            "example.com": ["https://Example.com/a"],
            "other.test": ["https://other.test"],
        }
    ]


def test_open_urls_in_front_window_returns_false_on_applescript_error(
    monkeypatch,
) -> None:
    async def fake_check_safari_status() -> bool:
        return True

    async def fake_run_applescript(script: str) -> tuple[str, str, int]:
        assert "https://example.com" in script
        return "", "error", 1

    monkeypatch.setattr(safari, "check_safari_status", fake_check_safari_status)
    monkeypatch.setattr(safari, "run_applescript", fake_run_applescript)

    result = asyncio.run(
        SafariController.open_urls_in_front_window(["https://example.com"])
    )

    assert result is False


def test_run_batch_handles_empty_script_and_nonzero_return(monkeypatch) -> None:
    async def fake_run_applescript(script: str) -> tuple[str, str, int]:
        return "", "failed", 1

    monkeypatch.setattr(safari, "build_batch_script", lambda *_args, **_kwargs: "")
    assert asyncio.run(SafariController._run_batch(["https://example.com"])) is True

    monkeypatch.setattr(
        safari,
        "build_batch_script",
        lambda *_args, **_kwargs: "tell application \"Safari\"",
    )
    monkeypatch.setattr(safari, "run_applescript", fake_run_applescript)

    assert asyncio.run(SafariController._run_batch(["https://example.com"])) is False
