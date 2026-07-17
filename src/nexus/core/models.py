"""Data models for Nexus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string (seconds precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# Note: ``type`` is a built-in but not a reserved word.  It is used here
# as a dataclass field on purpose — it keeps the on-disk bookmark JSON
# format stable (``{"type": "bookmark", "name": ..., "url": ...}``) and
# renaming it would require a one-shot migration of every user's saved
# bookmarks.  Avoid using the built-in ``type()`` on instances of these
# dataclasses; ``type(bookmark)`` will return ``<class Bookmark>``, not
# the bookmark kind.  Use ``bookmark.type`` for that.
@dataclass
class Bookmark:
    """Represents a single bookmark with name and URL."""

    name: str
    url: str
    type: str = "bookmark"  # Used for serialization/deserialization
    accent: str | None = None  # hex color, e.g. "#E5738A"; None = inherit folder


@dataclass
class BookmarkFolder:
    """Represents a folder that can contain bookmarks or other folders."""

    name: str
    children: list[BookmarkFolder | Bookmark] = field(default_factory=list)
    type: str = "folder"  # Used for serialization/deserialization
    accent: str | None = None  # hex color set via NewFolderDialog


# Union type for items that can exist in the bookmark tree
BookmarkNode = BookmarkFolder | Bookmark


@dataclass
class GroupItem:
    """A single URL captured in a bookmark group."""

    title: str
    url: str


@dataclass
class BookmarkGroup:
    """A saved bundle of URLs, identified by a stable id."""

    id: str
    name: str
    created_at: str = field(default_factory=_now_iso)  # ISO 8601 timestamp
    items: list[GroupItem] = field(default_factory=list)
