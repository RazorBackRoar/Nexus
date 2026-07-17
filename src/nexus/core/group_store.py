"""Sidecar JSON store for saved bookmark groups.

Mirrors :class:`nexus.core.bookmarks.BookmarkManager` — atomic write with
``.bak`` fallback so a partial write never leaves the file unreadable.
"""

import json
from pathlib import Path

from nexus.core.config import logger
from nexus.core.models import BookmarkGroup, GroupItem


class GroupStore:
    """Read/write the ``bookmark_groups.json`` sidecar file."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_path = file_path.with_name(file_path.name + ".bak")
        self.temp_path = file_path.with_name(file_path.name + ".tmp")

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_groups(self) -> list[BookmarkGroup]:
        """Load every saved group, falling back to ``.bak`` if needed."""
        for candidate in (self.file_path, self.backup_path):
            if not candidate.exists():
                continue
            groups = self._load_from(candidate)
            if groups is not None:
                if candidate != self.file_path:
                    logger.warning(
                        "Restored groups from backup %s after primary file was missing, unreadable, or empty",
                        candidate,
                    )
                    self.save_groups(groups)
                return groups
        return []

    def _load_from(self, path: Path) -> list[BookmarkGroup] | None:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to read groups from %s: %s", path, e)
            return None
        if not isinstance(data, list):
            return None
        out: list[BookmarkGroup] = []
        for entry in data:
            try:
                out.append(self._deserialize(entry))
            except (KeyError, TypeError, ValueError, AttributeError) as e:
                logger.warning("Skipping invalid group entry: %s", e)
        return out

    def get_group(self, group_id: str) -> BookmarkGroup | None:
        """Return a single group by id, or None if not present."""
        for g in self.load_groups():
            if g.id == group_id:
                return g
        return None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save_groups(self, groups: list[BookmarkGroup]) -> bool:
        """Atomically persist the full group list."""
        try:
            with open(self.temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    [self._serialize(g) for g in groups],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            if self.file_path.exists():
                self.file_path.replace(self.backup_path)
            self.temp_path.replace(self.file_path)
            return True
        except OSError as e:
            logger.error("Failed to save groups: %s", e)
            return False

    def upsert_group(self, group: BookmarkGroup) -> None:
        """Insert or replace a group by id, then save."""
        groups = self.load_groups()
        for i, existing in enumerate(groups):
            if existing.id == group.id:
                groups[i] = group
                break
        else:
            groups.append(group)
        self.save_groups(groups)

    def delete_group(self, group_id: str) -> None:
        """Remove a group by id.  No-op if not present."""
        groups = self.load_groups()
        kept = [g for g in groups if g.id != group_id]
        if len(kept) < len(groups):
            self.save_groups(kept)

    # ------------------------------------------------------------------
    # (De)serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(group: BookmarkGroup) -> dict:
        return {
            "id": group.id,
            "name": group.name,
            "created_at": group.created_at,
            "items": [{"title": i.title, "url": i.url} for i in group.items],
        }

    @staticmethod
    def _deserialize(data: dict) -> BookmarkGroup:
        if not isinstance(data, dict):
            raise TypeError(f"group entry must be a dict, got {type(data).__name__}")
        if "id" not in data or "name" not in data:
            raise KeyError("group entry missing id or name")
        items_raw = data.get("items", [])
        items = [
            GroupItem(
                title=str(i.get("title", "")),
                url=str(i["url"]),
            )
            for i in items_raw
        ]
        return BookmarkGroup(
            id=str(data["id"]),
            name=str(data["name"]),
            created_at=str(data.get("created_at", "")),
            items=items,
        )
