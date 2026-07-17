"""Round-trip the new `accent` field on Bookmark and BookmarkFolder."""

import json

from nexus.core.bookmarks import BookmarkManager
from nexus.core.models import Bookmark, BookmarkFolder


def test_bookmark_accent_defaults_to_none():
    """A freshly created bookmark has no accent set."""
    assert Bookmark(name="x", url="https://x.com").accent is None


def test_bookmark_folder_accent_defaults_to_none():
    """A freshly created folder has no accent set."""
    assert BookmarkFolder(name="Favorites").accent is None


def test_bookmark_accent_round_trips(tmp_path):
    """Save and reload preserves the per-bookmark accent."""
    manager = BookmarkManager(tmp_path / "bookmarks.json")
    folder = BookmarkFolder(
        name="Favorites",
        children=[Bookmark(name="Pink Site", url="https://x.com", accent="#E5738A")],
    )
    assert manager.save_bookmarks([folder]) is True

    reloaded = manager.load_bookmarks()
    assert len(reloaded) == 1
    inner = reloaded[0].children
    assert len(inner) == 1
    assert isinstance(inner[0], Bookmark)
    assert inner[0].accent == "#E5738A"


def test_bookmark_folder_accent_round_trips(tmp_path):
    """Save and reload preserves the per-folder accent."""
    manager = BookmarkManager(tmp_path / "bookmarks.json")
    folder = BookmarkFolder(name="Tech", accent="#5B8DEF")
    manager.save_bookmarks([folder])

    reloaded = manager.load_bookmarks()
    assert reloaded[0].accent == "#5B8DEF"
