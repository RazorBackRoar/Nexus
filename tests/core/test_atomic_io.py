"""Exclusive no-follow JSON writes."""

from __future__ import annotations

from pathlib import Path

from nexus.core.atomic_io import atomic_replace_json


def test_atomic_replace_json_writes_payload(tmp_path: Path) -> None:
    target = tmp_path / "bookmarks_v2.json"
    atomic_replace_json(target, [{"url": "https://example.com"}])
    assert target.read_text(encoding="utf-8").find("https://example.com") >= 0
    assert not (tmp_path / "bookmarks_v2.json.tmp").exists()


def test_atomic_replace_json_does_not_follow_tmp_symlink(tmp_path: Path) -> None:
    target = tmp_path / "groups.json"
    secret = tmp_path / "secret.txt"
    secret.write_text("keep-me", encoding="utf-8")
    tmp = tmp_path / "groups.json.tmp"
    tmp.symlink_to(secret)

    atomic_replace_json(target, [{"id": "grp"}])

    assert secret.read_text(encoding="utf-8") == "keep-me"
    assert target.is_file()
    assert not tmp.exists() or not tmp.is_symlink()
