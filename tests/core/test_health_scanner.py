"""Tests for Bookmark health scanner (duplicate finder and link liveness)."""

from email.message import Message
from io import BytesIO
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

from nexus.core.bookmarks import BookmarkManager
from nexus.core.health_scanner import (
    check_url_liveness,
    find_duplicates,
    normalize_url,
    scan_dead_links_concurrently,
)
from nexus.core.models import Bookmark, BookmarkFolder, BookmarkGroup, GroupItem


def test_normalize_url():
    """Verify normalize_url standardizes schemes, trailing slashes, and lowercases domain."""
    assert normalize_url("https://Example.COM/path/") == "https://example.com/path"
    assert normalize_url("http://example.com:80/path") == "http://example.com:80/path"
    assert normalize_url("example.com/test") == "https://example.com/test"
    assert (
        normalize_url("  https://github.com/foo/bar?q=1#frag  ")
        == "https://github.com/foo/bar?q=1"
    )
    assert normalize_url("") == ""


def test_find_duplicates_in_folders(tmp_path):
    """Detect duplicate bookmarks across multiple folders."""
    bm_file = tmp_path / "bookmarks.json"
    bm = BookmarkManager(bm_file)

    tree = [
        BookmarkFolder(
            name="Folder A",
            children=[
                Bookmark(name="GitHub", url="https://github.com"),
                Bookmark(name="Apple", url="https://developer.apple.com"),
            ],
        ),
        BookmarkFolder(
            name="Folder B",
            children=[
                Bookmark(name="GH", url="https://github.com/"),  # duplicate of GitHub
                Bookmark(name="Python", url="https://python.org"),
            ],
        ),
    ]
    bm.save_bookmarks(tree)

    duplicates = find_duplicates(bm)
    assert len(duplicates) == 1
    assert "https://github.com" in duplicates
    occs = duplicates["https://github.com"]
    assert len(occs) == 2
    assert occs[0].name == "GitHub"
    assert occs[0].container_name == "Folder A"
    assert occs[1].name == "GH"
    assert occs[1].container_name == "Folder B"


def test_find_duplicates_across_groups_and_folders(tmp_path):
    """Detect duplicates between bookmark folders and saved groups."""
    bm_file = tmp_path / "bookmarks.json"
    bm = BookmarkManager(bm_file)
    bm.save_bookmarks(
        [
            BookmarkFolder(
                name="Tech",
                children=[Bookmark(name="Rust", url="https://rust-lang.org")],
            )
        ]
    )

    group_store = MagicMock()
    group_store.load_groups.return_value = [
        BookmarkGroup(
            id="g1",
            name="Saved Session",
            items=[GroupItem(title="Rust Lang", url="https://rust-lang.org/")],
        )
    ]

    duplicates = find_duplicates(bm, group_store)
    assert "https://rust-lang.org" in duplicates
    assert len(duplicates["https://rust-lang.org"]) == 2


def test_check_url_liveness_success(monkeypatch):
    """Mock successful HEAD response (200 OK)."""
    resp_mock = MagicMock()
    resp_mock.status = 200
    resp_mock.__enter__.return_value = resp_mock

    def fake_urlopen(req, timeout=None):
        return resp_mock

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    is_alive, code, err = check_url_liveness("https://example.com")
    assert is_alive is True
    assert code == 200
    assert err is None


def test_check_url_liveness_404(monkeypatch):
    """Mock HTTP 404 response."""

    def fake_urlopen(req, timeout=None):
        raise HTTPError(
            "https://example.com/notfound", 404, "Not Found", Message(), BytesIO(b"")
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    is_alive, code, err = check_url_liveness("https://example.com/notfound")
    assert is_alive is False
    assert code == 404
    assert err == "Not Found"


def test_check_url_liveness_head_405_fallback_get_success(monkeypatch):
    """Mock 405 Method Not Allowed on HEAD, followed by successful GET."""

    def fake_urlopen(req, timeout=None):
        if req.get_method() == "HEAD":
            raise HTTPError(
                "https://example.com",
                405,
                "Method Not Allowed",
                Message(),
                BytesIO(b""),
            )
        resp = MagicMock()
        resp.status = 200
        resp.__enter__.return_value = resp
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    is_alive, code, err = check_url_liveness("https://example.com")
    assert is_alive is True
    assert code == 200


def test_check_url_liveness_connection_error(monkeypatch):
    """Mock URLError (e.g. DNS failure or connection refused)."""

    def fake_urlopen(req, timeout=None):
        raise URLError("nodename nor servname provided, or not known")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    is_alive, code, err = check_url_liveness("https://nonexistent-domain-xyz.fake")
    assert is_alive is False
    assert code is None
    assert "nodename" in (err or "")


def test_scan_dead_links_concurrently(monkeypatch):
    """Check batch dead link scanning with mock responses."""

    def fake_urlopen(req, timeout=None):
        if "dead" in req.full_url:
            raise HTTPError(req.full_url, 404, "Not Found", Message(), BytesIO(b""))
        resp = MagicMock()
        resp.status = 200
        resp.__enter__.return_value = resp
        return resp

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    items = [
        ("https://alive1.com", "Alive 1", "Folder A"),
        ("https://dead1.com", "Dead 1", "Folder A"),
        ("https://alive2.com", "Alive 2", "Folder B"),
    ]

    progress_reports = []
    dead_results = scan_dead_links_concurrently(
        items,
        max_workers=2,
        progress_callback=lambda d, t: progress_reports.append((d, t)),
    )

    assert len(dead_results) == 1
    assert dead_results[0].url == "https://dead1.com"
    assert dead_results[0].status_code == 404
    assert len(progress_reports) == 3
