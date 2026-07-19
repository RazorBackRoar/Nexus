"""Data models for Nexus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string (seconds precision)."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


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
    """Represents a folder that can contain bookmarks, folders, or markers."""

    name: str
    children: list[BookmarkNode] = field(default_factory=list)
    type: str = "folder"  # Used for serialization/deserialization
    accent: str | None = None  # hex color set via NewFolderDialog


# Union type for items that can exist in the bookmark tree.  Group markers are
# raw ``dict`` refs (``{"type": "group", "id": ...}``) so the tree can hold
# them alongside the dataclass nodes.
BookmarkNode = BookmarkFolder | Bookmark | dict[str, Any]


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


@dataclass
class QuickSaveEntry:
    """One Quick Save batch shown as a dated block under the Quick Save tab.

    Stored as a raw marker dict in ``bookmarks_v2.json`` so it round-trips
    through the existing folder tree without a separate sidecar file.
    """

    id: str
    created_at: str = field(default_factory=_now_iso)  # ISO 8601 timestamp
    urls: list[str] = field(default_factory=list)
    notes: str = ""
    type: str = "quick_save"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "quick_save",
            "id": self.id,
            "created_at": self.created_at,
            "urls": list(self.urls),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuickSaveEntry:
        return cls(
            id=str(data.get("id") or ""),
            created_at=str(data.get("created_at") or _now_iso()),
            urls=[str(u) for u in data.get("urls") or [] if str(u).strip()],
            notes=str(data.get("notes") or ""),
        )
