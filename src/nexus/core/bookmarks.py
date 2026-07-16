"""Bookmark Manager to handle loading and saving of bookmarks."""

import json
from pathlib import Path
from typing import Any

from nexus.core.config import logger
from nexus.core.models import Bookmark, BookmarkFolder, BookmarkNode
from nexus.utils.url_processor import URLProcessor


DEFAULT_BOOKMARK_FOLDER_NAMES = (
    "Favorites",
    "Tech",
    "Misc",
    "Work",
    "Later",
    "News",
)


class BookmarkManager:
    """Handles loading and saving hierarchical bookmarks safely with support for nesting."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.url_processor = URLProcessor()

    def load_bookmarks(self) -> list[BookmarkNode]:
        """Loads bookmarks, handles errors, and creates defaults.

        Prefer the primary file; if it is missing, unreadable, or empty, fall
        back to ``.bak`` (left behind by an interrupted atomic save) before
        defaults.
        """
        backup_path = self.file_path.with_suffix(".bak")
        for candidate in (self.file_path, backup_path):
            if not candidate.exists():
                continue
            loaded = self._load_bookmarks_from_path(candidate)
            if loaded is None:
                continue
            if not loaded:
                # An empty primary usually means a bad save (e.g. pre-recovery
                # wipe). Keep looking for a populated backup before defaults.
                continue
            if candidate != self.file_path:
                logger.warning(
                    "Restored bookmarks from backup %s after primary file "
                    "was missing, unreadable, or empty",
                    candidate,
                )
                # Re-materialize the primary file so the next save does not
                # treat an empty library as authoritative.
                self.save_bookmarks(loaded)
            return loaded

        logger.info("No bookmark file found, creating defaults")
        return self._create_default_bookmarks()

    def _load_bookmarks_from_path(self, path: Path) -> list[BookmarkNode] | None:
        """Parse one bookmark JSON file.

        Returns ``None`` when the file is corrupt or not a bookmark array so
        callers can try ``.bak`` / defaults. Individual bad nodes are skipped
        without discarding the rest of the library.
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to read bookmarks from %s: %s", path, e)
            return None

        if not isinstance(data, list):
            logger.error(
                "Bookmark file %s is not a JSON array (got %s)",
                path,
                type(data).__name__,
            )
            return None

        bookmarks: list[BookmarkNode] = []
        for node_data in data:
            try:
                bookmarks.append(self._deserialize_node(node_data))
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                logger.warning("Skipping invalid bookmark entry: %s", e)
        logger.info(
            "Loaded %d top-level bookmark sections from %s",
            len(bookmarks),
            path,
        )
        return bookmarks

    def save_bookmarks(self, bookmarks: list[BookmarkNode]) -> bool:
        """Saves bookmarks using an atomic write process to prevent data loss."""
        backup_path = self.file_path.with_suffix(".bak")
        temp_path = self.file_path.with_suffix(".tmp")
        try:
            data = [self._serialize_node(node) for node in bookmarks]
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if self.file_path.exists():
                self.file_path.replace(backup_path)
            temp_path.replace(self.file_path)
            logger.info("Saved bookmarks successfully.")
            return True
        except OSError as e:
            logger.error("Failed to save bookmarks: %s", e)
            if backup_path.exists() and not self.file_path.exists():
                try:
                    backup_path.replace(self.file_path)
                    logger.info("Restored bookmarks from backup.")
                except OSError as restore_error:
                    logger.error(
                        "CRITICAL: Failed to restore backup: %s", restore_error
                    )
            return False

    def _serialize_node(self, node: BookmarkNode) -> dict[str, Any]:
        """Converts dataclass objects to dictionaries for JSON saving."""
        if isinstance(node, BookmarkFolder):
            return {
                "name": node.name,
                "type": "folder",
                "children": [self._serialize_node(child) for child in node.children],
            }
        else:  # It's a Bookmark
            return {"name": node.name, "type": "bookmark", "url": node.url}

    def _deserialize_node(self, data: dict[str, Any]) -> BookmarkNode:
        """Converts dictionaries from JSON back into dataclass objects."""
        if not isinstance(data, dict):
            raise TypeError(
                f"Bookmark node must be an object, got {type(data).__name__}"
            )
        if data.get("type") == "folder":
            children = []
            for child in data.get("children", []):
                try:
                    children.append(self._deserialize_node(child))
                except (ValueError, KeyError, TypeError, AttributeError) as e:
                    logger.warning("Skipping invalid bookmark child entry: %s", e)
            return BookmarkFolder(name=data["name"], children=children)
        else:  # It's a bookmark
            normalized_url = self.url_processor._normalize_url(str(data["url"]))
            if not normalized_url:
                raise ValueError("Bookmark URL failed validation")
            return Bookmark(name=data["name"], url=normalized_url)

    def _create_default_bookmarks(self) -> list[BookmarkNode]:
        """Creates default bookmark folders for common categories."""
        return [
            BookmarkFolder(name=name, children=[])
            for name in DEFAULT_BOOKMARK_FOLDER_NAMES
        ]
