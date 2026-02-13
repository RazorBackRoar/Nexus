"""Data models for Nexus."""

from dataclasses import dataclass, field


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
    children: list["BookmarkFolder | Bookmark"] = field(default_factory=list)
    type: str = "folder"  # Used for serialization/deserialization


# Union type for items that can exist in the bookmark tree
BookmarkNode = BookmarkFolder | Bookmark
