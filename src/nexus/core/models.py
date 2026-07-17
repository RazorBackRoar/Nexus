"""Data models for Nexus."""

from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass
class BookmarkFolder:
    """Represents a folder that can contain bookmarks or other folders."""

    name: str
    children: list[BookmarkFolder | Bookmark] = field(default_factory=list)
    type: str = "folder"  # Used for serialization/deserialization


# Union type for items that can exist in the bookmark tree
BookmarkNode = BookmarkFolder | Bookmark
