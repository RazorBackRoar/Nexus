"""
Bookmark Manager to handle loading and saving of bookmarks.
"""
import json
from pathlib import Path
from typing import List, Dict, Any

from nexus.core.config import logger
from nexus.core.models import Bookmark, BookmarkFolder, BookmarkNode

class BookmarkManager:
    """Handles loading and saving hierarchical bookmarks safely with support for nesting."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_bookmarks(self) -> List[BookmarkNode]:
        """Loads bookmarks, handles errors, and creates defaults."""
        if not self.file_path.exists():
            logger.info("No bookmark file found, creating defaults")
            return self._create_default_bookmarks()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            bookmarks = [self._deserialize_node(node_data) for node_data in data]
            logger.info("Loaded %d top-level bookmark sections", len(bookmarks))
            return bookmarks
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Failed to load bookmarks, creating defaults: %s", e)
            return self._create_default_bookmarks()

    def save_bookmarks(self, bookmarks: List[BookmarkNode]) -> bool:
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
        except (OSError, IOError) as e:
            logger.error("Failed to save bookmarks: %s", e)
            if backup_path.exists() and not self.file_path.exists():
                try:
                    backup_path.replace(self.file_path)
                    logger.info("Restored bookmarks from backup.")
                except (OSError, IOError) as restore_error:
                    logger.error(
                        "CRITICAL: Failed to restore backup: %s", restore_error
                    )
            return False

    def _serialize_node(self, node: BookmarkNode) -> Dict[str, Any]:
        """Converts dataclass objects to dictionaries for JSON saving."""
        if isinstance(node, BookmarkFolder):
            return {
                "name": node.name,
                "type": "folder",
                "children": [self._serialize_node(child) for child in node.children],
            }
        else:  # It's a Bookmark
            return {"name": node.name, "type": "bookmark", "url": node.url}

    def _deserialize_node(self, data: Dict[str, Any]) -> BookmarkNode:
        """Converts dictionaries from JSON back into dataclass objects."""
        if data.get("type") == "folder":
            children = [
                self._deserialize_node(child) for child in data.get("children", [])
            ]
            return BookmarkFolder(name=data["name"], children=children)
        else:  # It's a bookmark
            return Bookmark(name=data["name"], url=data["url"])

    def _create_default_bookmarks(self) -> List[BookmarkNode]:
        """Creates default bookmark folders for common categories."""
        return [
            BookmarkFolder(name="News", children=[]),
            BookmarkFolder(name="Apple", children=[]),
            BookmarkFolder(name="Misc", children=[]),
            BookmarkFolder(name="Google", children=[]),
            BookmarkFolder(name="Github", children=[]),
            BookmarkFolder(name="Fun", children=[]),
        ]
