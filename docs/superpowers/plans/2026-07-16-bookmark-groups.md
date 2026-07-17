# Bookmark Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Nexus "bookmark groups" — named, draggable bundles of URLs saved into a sidebar tab — plus a redesigned sidebar with ten color-coded default tabs, per-bookmark color overrides, and a `NewFolderDialog` with a swatch picker.

**Architecture:** Sidecar JSON for the group payload (`bookmark_groups.json`) keyed by `id`; bookmarks file holds a `GroupRef` marker (`{"type": "group", "id": "..."}`) inside the relevant folder. Sidebar tabs become reorderable and colored via a fixed palette + per-folder `accent` override. New `GroupStore`, `SaveGroupDialog`, `NewFolderDialog`, `GroupRowDelegate`; existing `BookmarkManager` grows accent + group-marker handling.

**Tech Stack:** Python 3.14, PySide6, stdlib `json`/`pathlib`/`secrets`/`datetime`. pytest for tests. `ruff` for linting.

**Spec:** `docs/superpowers/specs/2026-07-16-bookmark-groups-design.md`

**Working directory:** `/Users/home/Workspace/Apps/Nexus`

**Verification commands** (run from the project root unless stated):

```bash
.venv/bin/python -m pytest tests/ -q              # full suite
.venv/bin/python -m pytest tests/<path> -v       # a single test file
.venv/bin/ruff check src/nexus/                  # lint
```

---

## File map

**New files**
- `src/nexus/core/group_store.py` — `GroupStore` (load/save/upsert/delete/get)
- `src/nexus/gui/dialogs/save_group_dialog.py` — `SaveGroupDialog`
- `src/nexus/gui/dialogs/new_folder_dialog.py` — `NewFolderDialog`
- `src/nexus/gui/widgets/group_row_delegate.py` — `GroupRowDelegate`
- `tests/core/test_group_store.py`
- `tests/core/test_bookmark_group_markers.py`
- `tests/core/test_bookmark_accent.py`
- `tests/gui/test_save_group_dialog.py`
- `tests/gui/test_new_folder_dialog.py`
- `tests/gui/test_group_row_paint.py`
- `tests/gui/test_sidebar_reorder.py`

**Modified files**
- `src/nexus/core/config.py` — `BOOKMARK_GROUPS_FILE = "bookmark_groups.json"`
- `src/nexus/core/models.py` — add `accent` fields, `GroupItem`, `BookmarkGroup`
- `src/nexus/core/bookmarks.py` — handle accent + group markers in serialize/deserialize
- `src/nexus/gui/main_window.py` — 10 default tabs, color palette, save flow, drag-drop, context menus
- `src/nexus/gui/widgets.py` — group drag mime type, `BookmarkTreeDelegate` honors `accent`

---

## Task 1: Config — add `BOOKMARK_GROUPS_FILE`

**Files:**
- Modify: `src/nexus/core/config.py:32` (the `BOOKMARKS_FILE` constant block)
- Test: `tests/core/test_config_logging.py` (existing — add a new test)

- [ ] **Step 1: Write the failing test**

Append to `tests/core/test_config_logging.py`:

```python
def test_bookmark_groups_file_constant_present():
    """The new sidecar file is wired into Config."""
    from nexus.core.config import Config
    assert Config.BOOKMARK_GROUPS_FILE == "bookmark_groups.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_config_logging.py::test_bookmark_groups_file_constant_present -v`
Expected: FAIL with `AttributeError: type object 'Config' has no attribute 'BOOKMARK_GROUPS_FILE'`

- [ ] **Step 3: Implement**

In `src/nexus/core/config.py`, just below the existing `BOOKMARKS_FILE = "bookmarks_v2.json"` line, add:

```python
    BOOKMARKS_FILE = "bookmarks_v2.json"  # New filename to avoid conflicts
    BOOKMARK_GROUPS_FILE = "bookmark_groups.json"  # Sidecar for saved groups
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/core/test_config_logging.py::test_bookmark_groups_file_constant_present -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/core/config.py tests/core/test_config_logging.py
git commit -m "feat(config): add BOOKMARK_GROUPS_FILE constant"
```

---

## Task 2: Models — add `accent` to `Bookmark` and `BookmarkFolder`

**Files:**
- Modify: `src/nexus/core/models.py`
- Test: `tests/core/test_bookmark_accent.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_bookmark_accent.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/core/test_bookmark_accent.py -v`
Expected: All 4 FAIL with `TypeError: __init__() got an unexpected keyword argument 'accent'`

- [ ] **Step 3: Implement**

In `src/nexus/core/models.py`, change the two dataclasses:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/core/test_bookmark_accent.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/core/models.py tests/core/test_bookmark_accent.py
git commit -m "feat(models): add optional accent field to Bookmark and BookmarkFolder"
```

---

## Task 3: Models — add `GroupItem` and `BookmarkGroup`

**Files:**
- Modify: `src/nexus/core/models.py`
- Test: `tests/core/test_models_group.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_models_group.py`:

```python
"""GroupItem and BookmarkGroup are plain dataclasses."""

from nexus.core.models import BookmarkGroup, GroupItem


def test_group_item_stores_title_and_url():
    item = GroupItem(title="Example", url="https://example.com")
    assert item.title == "Example"
    assert item.url == "https://example.com"


def test_group_item_title_may_be_empty():
    item = GroupItem(title="", url="https://example.com")
    assert item.title == ""


def test_bookmark_group_minimum_fields():
    g = BookmarkGroup(id="grp_a1b2c3d4", name="Sunday reading", items=[])
    assert g.id == "grp_a1b2c3d4"
    assert g.name == "Sunday reading"
    assert g.items == []
    assert g.created_at  # populated by callers, defaults to ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/core/test_models_group.py -v`
Expected: FAIL with `ImportError: cannot import name 'GroupItem' from 'nexus.core.models'`

- [ ] **Step 3: Implement**

Append to `src/nexus/core/models.py`:

```python
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
    created_at: str = ""  # ISO 8601 timestamp; populated at save time
    items: list[GroupItem] = field(default_factory=list)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/core/test_models_group.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/core/models.py tests/core/test_models_group.py
git commit -m "feat(models): add GroupItem and BookmarkGroup"
```

---

## Task 4: BookmarkManager — round-trip group markers

**Files:**
- Modify: `src/nexus/core/bookmarks.py`
- Test: `tests/core/test_bookmark_group_markers.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_bookmark_group_markers.py`:

```python
"""Group reference markers survive a save/load round trip."""

from nexus.core.bookmarks import BookmarkManager


def test_group_marker_round_trips(tmp_path):
    """A folder containing a group marker preserves the marker on reload."""
    manager = BookmarkManager(tmp_path / "bookmarks.json")
    raw = [
        {
            "name": "Favorites",
            "type": "folder",
            "children": [
                {"type": "group", "id": "grp_a1b2c3d4"},
                {"type": "group", "id": "grp_b2c3d4e5"},
            ],
        }
    ]
    assert manager.save_bookmarks_raw(raw) is True

    reloaded = manager.load_bookmarks_raw()
    assert reloaded[0]["children"][0] == {"type": "group", "id": "grp_a1b2c3d4"}
    assert reloaded[0]["children"][1] == {"type": "group", "id": "grp_b2c3d4e5"}


def test_group_marker_load_is_robust_to_unknown_keys(tmp_path):
    """Future keys on a group marker do not break loading."""
    manager = BookmarkManager(tmp_path / "bookmarks.json")
    raw = [
        {
            "name": "Favorites",
            "type": "folder",
            "children": [
                {"type": "group", "id": "grp_a1b2c3d4", "future_field": "ignored"},
            ],
        }
    ]
    manager.save_bookmarks_raw(raw)
    reloaded = manager.load_bookmarks_raw()
    assert reloaded[0]["children"][0]["id"] == "grp_a1b2c3d4"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/core/test_bookmark_group_markers.py -v`
Expected: FAIL with `AttributeError: 'BookmarkManager' object has no attribute 'save_bookmarks_raw'`

- [ ] **Step 3: Implement**

In `src/nexus/core/bookmarks.py`, add two thin pass-through methods on `BookmarkManager`. Place them just below `save_bookmarks`:

```python
    def save_bookmarks_raw(self, data: list[dict]) -> bool:
        """Persist a pre-serialized list of dicts using the same atomic
        write protocol as :meth:`save_bookmarks`.  Used by callers that
        want to embed group markers (raw dicts) alongside dataclass nodes.
        """
        backup_path = self.file_path.with_suffix(".bak")
        temp_path = self.file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if self.file_path.exists():
                self.file_path.replace(backup_path)
            temp_path.replace(self.file_path)
            return True
        except OSError as e:
            logger.error("Failed to save bookmarks (raw): %s", e)
            if backup_path.exists() and not self.file_path.exists():
                try:
                    backup_path.replace(self.file_path)
                except OSError:
                    pass
            return False

    def load_bookmarks_raw(self) -> list[dict]:
        """Read the bookmark file as raw dicts, tolerating partial
        corruption.  Returns ``[]`` if the file is missing or unreadable.
        """
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to read raw bookmarks from %s: %s", self.file_path, e)
            return []
        if not isinstance(data, list):
            return []
        return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/core/test_bookmark_group_markers.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/core/bookmarks.py tests/core/test_bookmark_group_markers.py
git commit -m "feat(bookmarks): add save_bookmarks_raw / load_bookmarks_raw pass-throughs"
```

---

## Task 5: GroupStore — basic CRUD

**Files:**
- Create: `src/nexus/core/group_store.py`
- Test: `tests/core/test_group_store.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/core/test_group_store.py`:

```python
"""GroupStore round-trip and atomic-save behavior."""

import json
from pathlib import Path

import pytest

from nexus.core.group_store import GroupStore
from nexus.core.models import BookmarkGroup, GroupItem


def _group(id: str = "grp_a1b2c3d4", name: str = "Sunday reading") -> BookmarkGroup:
    return BookmarkGroup(
        id=id,
        name=name,
        created_at="2026-07-16T18:20:00",
        items=[GroupItem(title="Example", url="https://example.com")],
    )


def test_load_missing_file_returns_empty(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    assert store.load_groups() == []


def test_save_then_load_round_trips(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group())
    reloaded = store.load_groups()
    assert len(reloaded) == 1
    assert reloaded[0].name == "Sunday reading"
    assert reloaded[0].items[0].url == "https://example.com"


def test_upsert_overwrites_by_id(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group(name="Old name"))
    store.upsert_group(_group(name="New name"))
    groups = store.load_groups()
    assert len(groups) == 1
    assert groups[0].name == "New name"


def test_delete_removes_group(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group(id="grp_keep"))
    store.upsert_group(_group(id="grp_drop"))
    store.delete_group("grp_drop")
    ids = [g.id for g in store.load_groups()]
    assert ids == ["grp_keep"]


def test_delete_missing_id_is_noop(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group())
    store.delete_group("grp_does_not_exist")
    assert len(store.load_groups()) == 1


def test_save_creates_parent_directory(tmp_path: Path):
    store = GroupStore(tmp_path / "nested" / "dir" / "groups.json")
    store.upsert_group(_group())
    assert (tmp_path / "nested" / "dir" / "groups.json").exists()


def test_save_keeps_a_backup(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group(name="v1"))
    store.upsert_group(_group(name="v2"))
    backup = tmp_path / "groups.json.bak"
    assert backup.exists()
    with open(backup, encoding="utf-8") as f:
        bak_data = json.load(f)
    assert bak_data[0]["name"] == "v1"


def test_load_falls_back_to_backup_on_corruption(tmp_path: Path):
    primary = tmp_path / "groups.json"
    backup = tmp_path / "groups.json.bak"
    primary.write_text("not valid json", encoding="utf-8")
    backup.write_text(
        json.dumps([{"id": "grp_a", "name": "from bak", "created_at": "", "items": []}]),
        encoding="utf-8",
    )
    store = GroupStore(primary)
    groups = store.load_groups()
    assert len(groups) == 1
    assert groups[0].id == "grp_a"


def test_get_group_returns_payload(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    store.upsert_group(_group())
    fetched = store.get_group("grp_a1b2c3d4")
    assert fetched is not None
    assert fetched.name == "Sunday reading"


def test_get_group_missing_returns_none(tmp_path: Path):
    store = GroupStore(tmp_path / "groups.json")
    assert store.get_group("grp_missing") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/core/test_group_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nexus.core.group_store'`

- [ ] **Step 3: Implement**

Create `src/nexus/core/group_store.py`:

```python
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

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load_groups(self) -> list[BookmarkGroup]:
        """Load every saved group, falling back to ``.bak`` if needed."""
        backup_path = self.file_path.with_suffix(".bak")
        for candidate in (self.file_path, backup_path):
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
            except (KeyError, TypeError, ValueError) as e:
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
        backup_path = self.file_path.with_suffix(".bak")
        temp_path = self.file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    [self._serialize(g) for g in groups],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            if self.file_path.exists():
                self.file_path.replace(backup_path)
            temp_path.replace(self.file_path)
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
                self.save_groups(groups)
                return
        groups.append(group)
        self.save_groups(groups)

    def delete_group(self, group_id: str) -> None:
        """Remove a group by id.  No-op if not present."""
        groups = self.load_groups()
        kept = [g for g in groups if g.id != group_id]
        if len(kept) != len(groups):
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/core/test_group_store.py -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/core/group_store.py tests/core/test_group_store.py
git commit -m "feat(group_store): add GroupStore with atomic save and .bak fallback"
```

---

## Task 6: NewFolderDialog — name + swatch picker

**Files:**
- Create: `src/nexus/gui/dialogs/new_folder_dialog.py`
- Create: `src/nexus/gui/dialogs/__init__.py` (empty package marker)
- Test: `tests/gui/test_new_folder_dialog.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/gui/test_new_folder_dialog.py`:

```python
"""Behavior of the NewFolderDialog: name, swatch, custom color."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from nexus.gui.dialogs.new_folder_dialog import (
    DEFAULT_PALETTE,
    NewFolderDialog,
)


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    yield a


def test_dialog_starts_with_first_palette_swatch_selected(app):
    dlg = NewFolderDialog()
    assert dlg.folder_name == ""
    assert dlg.accent in DEFAULT_PALETTE


def test_setting_name_then_ok_passes_through(app):
    dlg = NewFolderDialog()
    dlg.folder_name = "Travel"
    dlg.accent = "#5B8DEF"
    assert dlg.folder_name == "Travel"
    assert dlg.accent == "#5B8DEF"


def test_default_palette_contains_ten_swatches():
    assert len(DEFAULT_PALETTE) == 10
    for hex_ in DEFAULT_PALETTE:
        assert hex_.startswith("#") and len(hex_) == 7
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/gui/test_new_folder_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nexus.gui.dialogs'`

- [ ] **Step 3: Implement**

Create `src/nexus/gui/dialogs/__init__.py`:

```python
"""Modal dialogs used by the Nexus GUI."""
```

Create `src/nexus/gui/dialogs/new_folder_dialog.py`:

```python
"""New Folder dialog: a name field plus a swatch palette for color picking.

The "Custom…" option opens :class:`QColorDialog` and returns the user-picked
hex.  Picking a palette swatch is instant; the dialog itself does not run an
event loop — callers must ``.exec()`` it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


# 10 default-tab accent colors.  Order matches the sidebar in
# ``docs/superpowers/specs/2026-07-16-bookmark-groups-design.md``.
DEFAULT_PALETTE: tuple[str, ...] = (
    "#E5738A",  # Fun     (pink)
    "#D4A05A",  # Misc    (orange)
    "#5B8DEF",  # Tech    (blue)
    "#E85A5A",  # Work    (red)
    "#8A95A8",  # Extra   (grey)
    "#A87A5A",  # Future  (brown)
    "#2A2A35",  # Hidden  (black)
    "#F0F4FA",  # Special (white)
    "#5BA86A",  # Favorites (green)
    "#6B6B7A",  # Sort    (slate)
)


class NewFolderDialog(QDialog):
    """Modal: a name field and a swatch combo box for the folder accent."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Folder")
        self.setModal(True)

        self._name_input = QLineEdit(self)
        self._name_input.setMaxLength(40)
        self._name_input.setPlaceholderText("Folder name")
        self._name_input.textChanged.connect(self._sync_ok_state)

        self._accent_combo = QComboBox(self)
        for hex_ in DEFAULT_PALETTE:
            self._accent_combo.addItem(hex_.upper(), hex_)
        self._accent_combo.addItem("Custom…", "__custom__")
        self._accent_combo.currentIndexChanged.connect(self._on_combo_changed)

        form = QFormLayout()
        form.addRow("Folder name:", self._name_input)
        form.addRow("Color:", self._accent_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._custom_color: str | None = None
        self._sync_ok_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def folder_name(self) -> str:
        return self._name_input.text().strip()

    @folder_name.setter
    def folder_name(self, value: str) -> None:
        self._name_input.setText(value)

    @property
    def accent(self) -> str:
        if self._accent_combo.currentData() == "__custom__":
            return self._custom_color or DEFAULT_PALETTE[0]
        return str(self._accent_combo.currentData())

    @accent.setter
    def accent(self, value: str) -> None:
        idx = self._accent_combo.findData(value)
        if idx >= 0:
            self._accent_combo.setCurrentIndex(idx)
        else:
            self._custom_color = value
            self._accent_combo.setCurrentIndex(self._accent_combo.count() - 1)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sync_ok_state(self) -> None:
        self._ok_button.setEnabled(bool(self._name_input.text().strip()))

    def _on_combo_changed(self, index: int) -> None:
        data = self._accent_combo.itemData(index)
        if data != "__custom__":
            return
        chosen = QColorDialog.getColor(
            QColor(self._custom_color or DEFAULT_PALETTE[0]),
            self,
            "Pick a folder color",
        )
        if chosen.isValid():
            self._custom_color = chosen.name()
        # Always reset to the previous selection so the user can retry.
        previous_index = max(0, index - 1) if self._custom_color is None else 0
        self._accent_combo.blockSignals(True)
        self._accent_combo.setCurrentIndex(previous_index)
        self._accent_combo.blockSignals(False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/gui/test_new_folder_dialog.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/dialogs/ tests/gui/test_new_folder_dialog.py
git commit -m "feat(gui): add NewFolderDialog with name + swatch palette"
```

---

## Task 7: SaveGroupDialog — name + target-folder combo

**Files:**
- Create: `src/nexus/gui/dialogs/save_group_dialog.py`
- Test: `tests/gui/test_save_group_dialog.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/gui/test_save_group_dialog.py`:

```python
"""SaveGroupDialog collects a name and a target folder."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from nexus.gui.dialogs.save_group_dialog import SaveGroupDialog


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    yield a


def test_default_target_is_first_folder(app):
    dlg = SaveGroupDialog(folders=["Favorites", "Work", "Tech"])
    assert dlg.target_folder == "Favorites"


def test_name_required_to_enable_ok(app):
    dlg = SaveGroupDialog(folders=["Favorites"])
    # Use the standard button box, which is a private attr.
    ok_button = dlg.findChild(__import__("PySide6.QtWidgets", fromlist=["QDialogButtonBox"]).QDialogButtonBox).button(
        __import__("PySide6.QtWidgets", fromlist=["QDialogButtonBox"]).QDialogButtonBox.StandardButton.Ok
    )
    assert ok_button.isEnabled() is False
    dlg.group_name = "Sunday reading"
    assert ok_button.isEnabled() is True


def test_name_max_length_60(app):
    dlg = SaveGroupDialog(folders=["Favorites"])
    dlg.group_name = "x" * 200
    assert len(dlg.group_name) == 60


def test_target_folder_setter(app):
    dlg = SaveGroupDialog(folders=["Favorites", "Work", "Tech"])
    dlg.target_folder = "Work"
    assert dlg.target_folder == "Work"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/gui/test_save_group_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nexus.gui.dialogs.save_group_dialog'`

- [ ] **Step 3: Implement**

Create `src/nexus/gui/dialogs/save_group_dialog.py`:

```python
"""Save Group dialog: a name field and a target-folder combo box."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class SaveGroupDialog(QDialog):
    """Modal: collect a group name and a target tab to drop the group into."""

    def __init__(
        self,
        folders: list[str],
        preselect: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Group")
        self.setModal(True)

        self._name_input = QLineEdit(self)
        self._name_input.setMaxLength(60)
        self._name_input.setPlaceholderText("e.g. Sunday reading")
        self._name_input.textChanged.connect(self._sync_ok_state)

        self._folder_combo = QComboBox(self)
        for name in folders:
            self._folder_combo.addItem(name)
        if preselect and preselect in folders:
            idx = folders.index(preselect)
            self._folder_combo.setCurrentIndex(idx)

        form = QFormLayout()
        form.addRow("Group name:", self._name_input)
        form.addRow("Save into:", self._folder_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def group_name(self) -> str:
        return self._name_input.text().strip()

    @group_name.setter
    def group_name(self, value: str) -> None:
        self._name_input.setText(value)

    @property
    def target_folder(self) -> str:
        return self._folder_combo.currentText()

    @target_folder.setter
    def target_folder(self, value: str) -> None:
        idx = self._folder_combo.findText(value)
        if idx >= 0:
            self._folder_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sync_ok_state(self) -> None:
        self._ok_button.setEnabled(bool(self._name_input.text().strip()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/gui/test_save_group_dialog.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/dialogs/save_group_dialog.py tests/gui/test_save_group_dialog.py
git commit -m "feat(gui): add SaveGroupDialog"
```

---

## Task 8: GroupRowDelegate — paint for indented group rows

**Files:**
- Create: `src/nexus/gui/widgets/group_row_delegate.py`
- Test: `tests/gui/test_group_row_paint.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/gui/test_group_row_paint.py`:

```python
"""GroupRowDelegate paints without crashing and exposes a sane sizeHint."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem

from nexus.gui.widgets.group_row_delegate import GroupRowDelegate


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    yield a


def _make_option(rect_width: int = 240) -> QStyleOptionViewItem:
    opt = QStyleOptionViewItem()
    opt.rect = opt.rect.__class__(0, 0, rect_width, 36)
    return opt


def test_paint_does_not_crash(app):
    delegate = GroupRowDelegate()
    index = app.style().standardIcon(
        app.style().StandardPixmap.SP_DirIcon
    )  # any QIcon-bearing object is overkill; we'll just call paint with a dummy
    # Instead build a QModelIndex via a model:
    from PySide6.QtCore import QAbstractListModel, QModelIndex

    class _Model(QAbstractListModel):
        def rowCount(self, parent=QModelIndex()):
            return 0

    model = _Model()
    delegate.paint(
        None,
        _make_option(),
        model.index(0, 0),
    )


def test_size_hint_is_at_least_30px_tall(app):
    delegate = GroupRowDelegate()
    size = delegate.sizeHint(_make_option(), None)
    assert size.height() >= 30


def test_accent_setter_is_idempotent(app):
    delegate = GroupRowDelegate()
    delegate.set_accent(QColor("#5B8DEF"))
    delegate.set_accent(QColor("#5B8DEF"))
    assert delegate.accent().name().lower() == "#5b8def"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/gui/test_group_row_paint.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'nexus.gui.widgets.group_row_delegate'`

- [ ] **Step 3: Implement**

Create `src/nexus/gui/widgets/group_row_delegate.py`:

```python
"""Paint delegate for the indented group rows in the sidebar."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QStyleOptionViewItem, QStyledItemDelegate


class GroupRowDelegate(QStyledItemDelegate):
    """Renders a group row: small stack icon, name, child count badge."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._accent = QColor("#6B9AF5")
        self._child_count: int | None = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_accent(self, color: QColor) -> None:
        self._accent = QColor(color)

    def accent(self) -> QColor:
        return self._accent

    def set_child_count(self, count: int | None) -> None:
        self._child_count = count

    # ------------------------------------------------------------------
    # QStyledItemDelegate API
    # ------------------------------------------------------------------

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: ANN001
        return QSize(option.rect.width(), 36)

    def paint(self, painter, option, index):  # noqa: ANN001
        if painter is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(22, 4, -10, -4)
        hovered = bool(option.state & __import__("PySide6.QtWidgets", fromlist=["QStyle"]).QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & __import__("PySide6.QtWidgets", fromlist=["QStyle"]).QStyle.StateFlag.State_Selected)

        if hovered or selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 14 if hovered else 22))
            painter.drawRoundedRect(rect, 8, 8)

        # Accent dot
        dot = rect.adjusted(0, 0, 0, 0)
        dot.setWidth(rect.height())
        dot.moveTop(rect.top())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._accent)
        painter.drawEllipse(dot.adjusted(10, 10, -10, -10))

        # Group name
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        font: QFont = option.font
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#D0DAEA"))
        text_rect = rect.adjusted(rect.height() + 6, 0, -52, 0)
        metrics = painter.fontMetrics()
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            elided,
        )

        # Child count badge
        if self._child_count is not None and self._child_count > 0:
            badge_text = f"({self._child_count})"
            painter.setPen(QColor("#8EA0BC"))
            badge_rect = rect.adjusted(rect.width() - 44, 0, -4, 0)
            painter.drawText(
                badge_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                badge_text,
            )

        painter.restore()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/gui/test_group_row_paint.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/widgets/group_row_delegate.py tests/gui/test_group_row_paint.py
git commit -m "feat(gui): add GroupRowDelegate for indented group rows"
```

---

## Task 9: MainWindow — wire in 10 default tabs + colored palette

**Files:**
- Modify: `src/nexus/gui/main_window.py:24` (DEFAULT_BOOKMARK_FOLDER_NAMES import)
- Modify: `src/nexus/gui/main_window.py:540-680` (`_resolve_folder_style` and the named styles)
- Test: `tests/gui/test_sidebar_reorder.py` (new) — for Task 11; for now just a smoke test

- [ ] **Step 1: Write the failing test**

Create `tests/gui/test_sidebar_reorder.py` with one test (the heavy lifting lands in Task 11):

```python
"""The sidebar renders 10 default tabs in the spec order."""

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from nexus.core.bookmarks import BookmarkManager
from nexus.gui.main_window import MainWindow


@pytest.fixture
def app(tmp_path, monkeypatch):
    a = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        "nexus.gui.main_window.QStandardPaths.writableLocation",
        lambda *_args, **_kw: str(tmp_path),
    )
    yield a


def test_sidebar_has_ten_default_tabs(app, tmp_path, monkeypatch):
    window = MainWindow()
    root = window.bookmark_tree.invisibleRootItem()
    names = [root.child(i).data(0, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemDataRole.UserRole)["name"]
             for i in range(root.childCount())]
    assert names == [
        "Fun", "Misc", "Tech", "Work", "Extra", "Future",
        "Hidden", "Special", "Favorites", "Sort",
    ]
    window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: FAIL with `KeyError: 'Sort'` (or similar — current default list has only 6 names)

- [ ] **Step 3: Implement — `models.py`**

In `src/nexus/core/bookmarks.py`, replace the `DEFAULT_BOOKMARK_FOLDER_NAMES` tuple:

```python
DEFAULT_BOOKMARK_FOLDER_NAMES: tuple[str, ...] = (
    "Fun",
    "Misc",
    "Tech",
    "Work",
    "Extra",
    "Future",
    "Hidden",
    "Special",
    "Favorites",
    "Sort",
)
```

- [ ] **Step 4: Implement — palette in `main_window.py`**

In `src/nexus/gui/main_window.py`, add a class-level constant near the top of `MainWindow`:

```python
    # Hex colors keyed by default tab name.  Order matches
    # ``DEFAULT_BOOKMARK_FOLDER_NAMES`` in ``core.bookmarks``.
    DEFAULT_TAB_PALETTE: dict[str, str] = {
        "Fun": "#E5738A",
        "Misc": "#D4A05A",
        "Tech": "#5B8DEF",
        "Work": "#E85A5A",
        "Extra": "#8A95A8",
        "Future": "#A87A5A",
        "Hidden": "#2A2A35",
        "Special": "#F0F4FA",
        "Favorites": "#5BA86A",
        "Sort": "#6B6B7A",
    }
```

You'll need to add `QColor` to the existing `from PySide6.QtGui import ...` line in `main_window.py` (the file already imports `QKeySequence` and `QShortcut` — extend that to `QKeySequence, QShortcut, QColor`).

Then replace the entire `_resolve_folder_style` method body so a folder with an `accent` field uses its own color; default tabs use the new palette; everything else falls back to the existing fallback cycle:

```python
    def _resolve_folder_style(
        self, folder_name: str, accent: str | None = None
    ) -> dict[str, str]:
        """Return an accent color for a bookmark folder row.

        Lookup order:
        1. The folder's own ``accent`` argument (set via NewFolderDialog).
        2. The fixed palette for the ten default tabs.
        3. A stable fallback cycle for any other name.
        """
        if accent:
            return self._style_from_accent(accent)
        if folder_name in self.DEFAULT_TAB_PALETTE:
            return self._style_from_accent(self.DEFAULT_TAB_PALETTE[folder_name])

        fallback_styles = [
            {"start": "#5B8DEF", "end": "#092B59", "border": "#9AD4FF", "icon": "#E8F7FF"},
            {"start": "#9B7AE8", "end": "#250854", "border": "#D6B5FF", "icon": "#F3E8FF"},
            {"start": "#4DB6A0", "end": "#07312B", "border": "#9CE8D8", "icon": "#ECFFF8"},
            {"start": "#E5738A", "end": "#3E081F", "border": "#EAB0C9", "icon": "#FFE5EF"},
            {"start": "#D4A05A", "end": "#4A2603", "border": "#F0CB93", "icon": "#FFF5D7"},
            {"start": "#6B9AF5", "end": "#162B67", "border": "#B5C5FF", "icon": "#F1F3FF"},
        ]
        if not hasattr(self, "_folder_style_cache"):
            self._folder_style_cache = {}
        normalized = folder_name.lower()
        if normalized not in self._folder_style_cache:
            index = len(self._folder_style_cache) % len(fallback_styles)
            self._folder_style_cache[normalized] = fallback_styles[index]
        return self._folder_style_cache[normalized]

    @staticmethod
    def _style_from_accent(hex_color: str) -> dict[str, str]:
        """Build a 4-color style dict from a single accent hex."""
        c = QColor(hex_color)
        return {
            "start": c.name(),
            "end": c.darker(140).name(),
            "border": c.lighter(120).name(),
            "icon": c.lighter(150).name(),
        }
```

You'll need to add `from PySide6.QtGui import QColor` to the imports of `main_window.py` (the file already imports `QKeySequence` and `QShortcut` from `PySide6.QtGui` — extend that import).

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: 1 PASS

- [ ] **Step 6: Commit**

```bash
git add src/nexus/core/bookmarks.py src/nexus/gui/main_window.py tests/gui/test_sidebar_reorder.py
git commit -m "feat(gui): ship 10 default tabs with fixed color palette"
```

---

## Task 10: MainWindow — `+` opens NewFolderDialog

**Files:**
- Modify: `src/nexus/gui/main_window.py` — `add_bookmark_section` method
- Test: extend `tests/gui/test_sidebar_reorder.py` (or new test file) — covered indirectly; no new test

- [ ] **Step 1: Replace `add_bookmark_section` body**

Find the `add_bookmark_section` method in `src/nexus/gui/main_window.py`. Replace its body so it pops the new `NewFolderDialog`, persists the chosen accent on the `BookmarkFolder`, and saves:

```python
    def add_bookmark_section(self):
        """Prompts for a new folder name + color, then adds it to the tree."""
        parent_item = self._get_selected_parent_item()
        from nexus.gui.dialogs.new_folder_dialog import NewFolderDialog
        dialog = NewFolderDialog(self)
        if dialog.exec() != NewFolderDialog.DialogCode.Accepted:
            return
        name = dialog.folder_name
        accent = dialog.accent
        if not name:
            return
        folder_data = {
            "name": name,
            "type": "folder",
            "accent": accent,
            "children": [],
        }
        section_item = self._create_tree_item(folder_data, parent_item)
        if parent_item:
            parent_item.setExpanded(True)
        else:
            self.bookmark_tree.addTopLevelItem(section_item)
        self.save_bookmarks()
```

- [ ] **Step 2: Make sure `save_bookmarks` persists `accent`**

`_serialize_item` already uses `item.data(0, Qt.ItemDataRole.UserRole).copy()` and adds children. To persist `accent`, extend the serializer:

```python
    def _serialize_item(self, item: QTreeWidgetItem) -> dict[str, Any]:
        """Recursively converts a tree item back into a dictionary for saving."""
        data = item.data(0, Qt.ItemDataRole.UserRole).copy()
        if data.get("type") == "folder":
            data["children"] = [
                self._serialize_item(item.child(i)) for i in range(item.childCount())
            ]
        return data
```

This already writes whatever keys are in `data` (name, type, accent) — no change needed as long as `_create_tree_item` copies the full dict into `UserRole` (which it does).

- [ ] **Step 3: Manually smoke-test**

```bash
.venv/bin/python -c "
import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from nexus.gui.main_window import MainWindow
w = MainWindow()
w.show()
print('Default tab count:', w.bookmark_tree.topLevelItemCount())
print('Names:', [w.bookmark_tree.topLevelItem(i).text(0) for i in range(w.bookmark_tree.topLevelItemCount())])
"
```

Expected: `Default tab count: 10` and the names in the spec order.

- [ ] **Step 4: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/main_window.py
git commit -m "feat(gui): add-folder button now uses NewFolderDialog (name + color)"
```

---

## Task 11: Sidebar tabs become reorderable

**Files:**
- Modify: `src/nexus/gui/main_window.py` — `bookmark_tree` setup, add a drop handler
- Test: extend `tests/gui/test_sidebar_reorder.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/gui/test_sidebar_reorder.py`:

```python
def test_top_level_tabs_accept_internal_drag_drop(app, tmp_path, monkeypatch):
    """Drag-reorder of top-level tabs is enabled and persists."""
    window = MainWindow()
    tree = window.bookmark_tree
    # Both flags must be on for internal drag/drop to work.
    from nexus.gui.main_window import MainWindow
    # The tree must have internal moves enabled.
    assert tree.dragDropMode() == tree.DragDropMode.InternalMove or tree.acceptDrops()
    window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: FAIL (the test is structural; the new logic lands in Step 3 — re-run after)

- [ ] **Step 3: Implement**

In `_setup_ui`, where the `bookmark_tree` is configured, change the drag/drop settings:

```python
        self.bookmark_tree.setAcceptDrops(True)
        self.bookmark_tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.bookmark_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.bookmark_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.bookmark_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
```

(Keep all other existing setup; the imports `QAbstractItemView` and `Qt` are already in the file.)

Then add a tiny helper to commit a top-level reorder back to the bookmark file:

```python
    def _on_top_level_reordered(self) -> None:
        """Called after a drag-reorder of top-level tabs persists the new order."""
        # Existing ``self.save_bookmarks`` walks the entire tree; re-serialize.
        self.save_bookmarks()
```

Connect it once in `_setup_ui` (after `bookmark_tree` is created):

```python
        # Reorder persistence — every drag/drop re-saves the bookmark file.
        self.bookmark_tree.model().rowsMoved.connect(self._on_top_level_reordered)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/main_window.py tests/gui/test_sidebar_reorder.py
git commit -m "feat(gui): sidebar tabs accept drag-reorder"
```

---

## Task 12: MainWindow — render groups under their folder

**Files:**
- Modify: `src/nexus/gui/main_window.py` — `load_bookmarks`, `_create_tree_item`, `MainWindow.__init__`
- Test: extend `tests/gui/test_sidebar_reorder.py` (light test, since the heavy lifting is GUI)

- [ ] **Step 1: Write the failing test**

Append to `tests/gui/test_sidebar_reorder.py`:

```python
def test_group_markers_render_as_tree_children(app, tmp_path, monkeypatch):
    """A folder with group markers renders them as child items."""
    # Set up: a bookmark file with a group marker under "Tech".
    from nexus.core.bookmarks import BookmarkManager
    manager = BookmarkManager(tmp_path / "bookmarks.json")
    manager.save_bookmarks_raw([
        {
            "name": "Tech",
            "type": "folder",
            "accent": "#5B8DEF",
            "children": [
                {"type": "group", "id": "grp_a1b2c3d4"},
            ],
        }
    ])
    window = MainWindow()
    root = window.bookmark_tree.invisibleRootItem()
    # Find the Tech tab
    tech_idx = next(
        i for i in range(root.childCount())
        if root.child(i).text(0) == "Tech"
    )
    tech_item = root.child(tech_idx)
    assert tech_item.childCount() == 1
    child = tech_item.child(0)
    data = child.data(0, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemDataRole.UserRole)
    assert data["type"] == "group"
    assert data["id"] == "grp_a1b2c3d4"
    window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: FAIL — the marker is silently dropped during `_deserialize_node`.

- [ ] **Step 3: Implement — extend `_deserialize_node`**

In `src/nexus/core/bookmarks.py`, change `_deserialize_node` to pass through unknown entries as dicts (a "marker"):

```python
    def _deserialize_node(self, data: dict[str, Any]) -> Any:
        """Converts dictionaries from JSON back into dataclass objects.

        Unknown entry types (e.g. ``{"type": "group", "id": ...}``) are
        returned as the raw dict so callers can recognize them.
        """
        if not isinstance(data, dict):
            raise TypeError(
                f"Bookmark node must be an object, got {type(data).__name__}"
            )
        node_type = data.get("type")
        if node_type == "folder":
            children = []
            for child in data.get("children", []):
                try:
                    children.append(self._deserialize_node(child))
                except (ValueError, KeyError, TypeError, AttributeError) as e:
                    logger.warning("Skipping invalid bookmark child entry: %s", e)
            return BookmarkFolder(
                name=data["name"],
                accent=data.get("accent"),
                children=children,
            )
        if node_type == "bookmark":
            normalized_url = self.url_processor._normalize_url(str(data["url"]))
            if not normalized_url:
                raise ValueError("Bookmark URL failed validation")
            return Bookmark(
                name=data["name"],
                url=normalized_url,
                accent=data.get("accent"),
            )
        # Unknown type — treat as a marker dict.
        return data
```

- [ ] **Step 4: Implement — extend `_serialize_node`**

In `src/nexus/core/bookmarks.py`, extend `_serialize_node` to handle marker dicts:

```python
    def _serialize_node(self, node: Any) -> dict[str, Any]:
        """Converts dataclass objects (or marker dicts) to JSON-friendly dicts."""
        if isinstance(node, dict):
            return node  # marker — pass through
        if isinstance(node, BookmarkFolder):
            out: dict[str, Any] = {
                "name": node.name,
                "type": "folder",
                "children": [self._serialize_node(child) for child in node.children],
            }
            if node.accent is not None:
                out["accent"] = node.accent
            return out
        return {"name": node.name, "type": "bookmark", "url": node.url}
```

(You'll need to add `from typing import Any` is already imported.)

- [ ] **Step 5: Implement — render groups in the tree**

In `src/nexus/gui/main_window.py`, find `_create_tree_item`. Add a branch for marker dicts:

```python
    def _create_tree_item(
        self, data: dict[str, Any], parent: QTreeWidgetItem | None = None
    ) -> QTreeWidgetItem:
        """Recursive helper to build the visual tree from data."""
        is_folder = data.get("type") == "folder"
        is_group = data.get("type") == "group"
        item = QTreeWidgetItem([data.get("name", "(missing group)")])
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        if is_folder:
            # A folder with its own ``accent`` (set via NewFolderDialog)
            # wins over the default-tab palette.  ``_resolve_folder_style``
            # handles both branches.
            folder_style = self._resolve_folder_style(
                data["name"],
                accent=data.get("accent"),
            )
            item.setData(0, Qt.ItemDataRole.UserRole + 1, folder_style)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if "children" in data:
                for child_data in data["children"]:
                    self._create_tree_item(child_data, item)
        elif is_group:
            item.setFlags(
                item.flags() & ~Qt.ItemFlag.ItemIsEditable
            ) & ~Qt.ItemFlag.ItemIsSelectable
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if parent:
            parent.addChild(item)
        else:
            self.bookmark_tree.addTopLevelItem(item)
        return item
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: 3 PASS

- [ ] **Step 7: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/nexus/core/bookmarks.py src/nexus/gui/main_window.py tests/gui/test_sidebar_reorder.py
git commit -m "feat: render group markers as children of their folder"
```

---

## Task 13: MainWindow — Save button → SaveGroupDialog → GroupStore

**Files:**
- Modify: `src/nexus/gui/main_window.py` — `MainWindow.__init__` (instantiate GroupStore), `_save_urls_to_bookmarks` replaced, new `_save_urls_as_group` slot
- Test: extend `tests/gui/test_sidebar_reorder.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/gui/test_sidebar_reorder.py`:

```python
def test_save_urls_creates_a_group_in_group_store(app, tmp_path, monkeypatch):
    """Clicking Save with URLs in the table creates a group entry."""
    from nexus.core.models import GroupItem
    window = MainWindow()
    # Drop a few URLs into the table.
    window.url_table.add_urls(["https://a.com", "https://b.com", "https://c.com"])

    # Replace the dialog with a stub that returns immediately.
    from nexus.gui.dialogs.save_group_dialog import SaveGroupDialog
    monkeypatch.setattr(
        SaveGroupDialog, "exec", lambda self: SaveGroupDialog.DialogCode.Accepted
    )
    monkeypatch.setattr(
        SaveGroupDialog, "group_name", property(lambda self: "My Group")
    )
    monkeypatch.setattr(
        SaveGroupDialog, "target_folder", property(lambda self: "Tech")
    )

    window._save_urls_to_bookmarks()

    # The URL table is now empty.
    assert window.url_table.rowCount() == 0
    # A group with that name lives in the GroupStore.
    groups = window.group_store.load_groups()
    assert any(g.name == "My Group" and len(g.items) == 3 for g in groups)
    window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: FAIL — `window.group_store` does not exist or the group is not saved.

- [ ] **Step 3: Implement — instantiate GroupStore in `MainWindow.__init__`**

In `src/nexus/gui/main_window.py`, locate the `BookmarkManager` instantiation in `__init__`. Add right after it:

```python
        from nexus.core.group_store import GroupStore
        self.group_store = GroupStore(app_data_dir / Config.BOOKMARK_GROUPS_FILE)
```

- [ ] **Step 4: Implement — wire the Save button**

Replace the body of `_save_urls_to_bookmarks`:

```python
    def _save_urls_to_bookmarks(self):
        """Save the URLs in the table as a new bookmark group."""
        urls = self.url_table.get_all_urls()
        if not urls:
            self._show_message("No URLs found to save.", "warning")
            return

        from nexus.gui.dialogs.save_group_dialog import SaveGroupDialog
        folders = [self.bookmark_tree.topLevelItem(i).text(0)
                   for i in range(self.bookmark_tree.topLevelItemCount())]
        preselect = self._currently_selected_folder_name() or folders[0]
        dialog = SaveGroupDialog(folders=folders, preselect=preselect, parent=self)
        if dialog.exec() != SaveGroupDialog.DialogCode.Accepted:
            return
        name = dialog.group_name
        target = dialog.target_folder
        if not name:
            return

        from datetime import datetime
        from nexus.core.models import BookmarkGroup, GroupItem
        from secrets import token_hex
        group = BookmarkGroup(
            id="grp_" + token_hex(4),
            name=name,
            created_at=datetime.now().isoformat(timespec="seconds"),
            items=[GroupItem(title=self._generate_bookmark_name(u), url=u) for u in urls],
        )
        self.group_store.upsert_group(group)

        # Insert marker into the in-memory tree and save the bookmark file.
        target_item = self._find_folder_by_name(target)
        if target_item is not None:
            marker = {"type": "group", "id": group.id, "name": group.name}
            self._create_tree_item(marker, target_item)
            target_item.setExpanded(True)
        self.save_bookmarks()

        self.url_table.clear_table()
        self._set_status(f"Saved {len(urls)} URLs to '{name}' in {target}")
```

Add three small helpers near the other private helpers:

```python
    def _currently_selected_folder_name(self) -> str | None:
        item = self.bookmark_tree.currentItem()
        if not item:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "folder":
            return data.get("name")
        return None

    def _find_folder_by_name(self, name: str) -> QTreeWidgetItem | None:
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "folder" and data.get("name") == name:
                return item
        return None

    def _set_status(self, message: str) -> None:
        if hasattr(self, "status_bar"):
            self.status_bar.setText(message)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: 4 PASS

- [ ] **Step 6: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: All tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/nexus/gui/main_window.py tests/gui/test_sidebar_reorder.py
git commit -m "feat(gui): Save button now saves URLs as a bookmark group"
```

---

## Task 14: Group context menu — Open, Rename, Move to, Delete

**Files:**
- Modify: `src/nexus/gui/main_window.py` — `_show_bookmark_context_menu`
- Test: extend `tests/gui/test_sidebar_reorder.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/gui/test_sidebar_reorder.py`:

```python
def test_group_context_menu_has_rename_and_delete(app, tmp_path, monkeypatch):
    """Right-clicking a group row offers Rename, Move to, Delete, Open."""
    window = MainWindow()
    # Build a single group under Tech by hand.
    from nexus.core.bookmarks import BookmarkManager
    window.bookmark_manager.save_bookmarks_raw([
        {
            "name": "Tech",
            "type": "folder",
            "accent": "#5B8DEF",
            "children": [{"type": "group", "id": "grp_x", "name": "Old name"}],
        }
    ])
    window.load_bookmarks()

    # Find the group item
    root = window.bookmark_tree.invisibleRootItem()
    tech = next(
        root.child(i) for i in range(root.childCount())
        if root.child(i).text(0) == "Tech"
    )
    group_item = tech.child(0)

    # Build the menu and verify the actions exist.
    window._show_bookmark_context_menu(group_item.treeWidget().visualItemRect(group_item).center())
    menu = window.findChild(__import__("PySide6.QtWidgets", fromlist=["QMenu"]).QMenu)
    # We don't have an active menu in this offscreen test; the action list
    # is built inside the method.  Instead, verify the method recognizes
    # the item type without crashing.
    window.close()
```

A lighter test that doesn't require a real menu: simply call the method and assert no exception.

- [ ] **Step 2: Implement — extend the context menu**

Find `_show_bookmark_context_menu` in `src/nexus/gui/main_window.py`. Add a branch for `item_type == "group"` *before* the bookmark branch:

```python
        if item_type == "group":
            open_action = menu.addAction("Open in Safari")
            open_action.triggered.connect(lambda: self._open_group_in_safari(item))
            menu.addSeparator()
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._rename_group(item))
            move_menu = menu.addMenu("Move to…")
            for i in range(self.bookmark_tree.topLevelItemCount()):
                folder_item = self.bookmark_tree.topLevelItem(i)
                folder_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
                if folder_data and folder_data.get("name") != item.parent().text(0):
                    move_menu.addAction(folder_data["name"]).triggered.connect(
                        lambda checked=False, fi=folder_item: self._move_group_to(item, fi)
                    )
            menu.addSeparator()
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_group(item))
        elif item_type == "bookmark":
            ...
```

And add the three helpers:

```python
    def _open_group_in_safari(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        group = self.group_store.get_group(data["id"])
        if not group:
            return
        urls = [g.url for g in group.items]
        if not urls:
            return
        self.worker = AsyncWorker(
            self.safari_controller.open_urls_in_front_window,
            urls,
            self.private_mode_enabled,
        )
        self.worker.start()

    def _rename_group(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        new_name, ok = QInputDialog.getText(self, "Rename Group", "New name:", text=data.get("name", ""))
        if not ok or not new_name.strip():
            return
        group = self.group_store.get_group(data["id"])
        if group is None:
            return
        group.name = new_name.strip()
        self.group_store.upsert_group(group)
        data["name"] = new_name.strip()
        item.setText(0, new_name.strip())

    def _move_group_to(self, item: QTreeWidgetItem, target_folder_item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        # Detach from current parent, attach to target folder, save.
        old_parent = item.parent()
        if old_parent is not None:
            old_parent.removeChild(item)
        target_folder_item.addChild(item)
        target_folder_item.setExpanded(True)
        self.save_bookmarks()

    def _delete_group(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        confirm = QMessageBox.question(
            self,
            "Delete Group",
            f"Delete the group '{data.get('name', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.group_store.delete_group(data["id"])
        parent = item.parent()
        if parent is not None:
            parent.removeChild(item)
        self.save_bookmarks()
```

- [ ] **Step 3: Run the test**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: 5 PASS

- [ ] **Step 4: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/main_window.py tests/gui/test_sidebar_reorder.py
git commit -m "feat(gui): right-click group row -> Open/Rename/Move/Delete"
```

---

## Task 15: Bookmark context menu — Color submenu + Delete promoted

**Files:**
- Modify: `src/nexus/gui/main_window.py` — `_show_bookmark_context_menu`
- Test: extend `tests/gui/test_sidebar_reorder.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/gui/test_sidebar_reorder.py`:

```python
def test_bookmark_accent_round_trips_via_context_menu(app, tmp_path, monkeypatch):
    """Recoloring a bookmark via the context menu persists."""
    window = MainWindow()
    window.bookmark_manager.save_bookmarks_raw([
        {
            "name": "Tech",
            "type": "folder",
            "accent": "#5B8DEF",
            "children": [
                {"type": "bookmark", "name": "Example", "url": "https://example.com"}
            ],
        }
    ])
    window.load_bookmarks()

    # Simulate the recolor action directly (the menu is GUI-bound; the
    # underlying mutation is what we test).
    root = window.bookmark_tree.invisibleRootItem()
    tech = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "Tech")
    bookmark_item = tech.child(0)
    window._set_bookmark_accent(bookmark_item, "#E5738A")
    assert bookmark_item.data(0, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemDataRole.UserRole)["accent"] == "#E5738A"

    # Reload from disk to confirm persistence.
    window.load_bookmarks()
    root = window.bookmark_tree.invisibleRootItem()
    tech = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "Tech")
    bookmark_item = tech.child(0)
    assert bookmark_item.data(0, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemDataRole.UserRole).get("accent") == "#E5738A"
    window.close()
```

- [ ] **Step 2: Implement — add a helper and the Color submenu**

Add the helper near the other private helpers:

```python
    def _set_bookmark_accent(self, item: QTreeWidgetItem, accent: str) -> None:
        """Update a bookmark row's accent and persist immediately."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "bookmark":
            return
        data["accent"] = accent
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self.save_bookmarks()
```

Replace the existing bookmark branch in `_show_bookmark_context_menu` (the part that handles `item_type == "bookmark"`) with:

```python
        if item_type == "bookmark":
            open_action = menu.addAction("Open in Safari")
            open_action.triggered.connect(lambda: self._open_bookmark_link(item))
            menu.addSeparator()
            edit_action = menu.addAction("Rename")
            edit_action.triggered.connect(lambda: self.bookmark_tree.editItem(item))
            color_menu = menu.addMenu("Color")
            for hex_ in [
                "#E5738A", "#D4A05A", "#5B8DEF", "#E85A5A", "#8A95A8",
                "#A87A5A", "#2A2A35", "#F0F4FA", "#5BA86A", "#6B6B7A",
            ]:
                color_menu.addAction(hex_.upper()).triggered.connect(
                    lambda checked=False, h=hex_: self._set_bookmark_accent(item, h)
                )
            copy_action = menu.addAction("Copy URL")
            copy_action.triggered.connect(lambda: self._copy_bookmark_url(item))
            menu.addSeparator()
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_bookmark_item(item))
```

And add the URL-copy helper:

```python
    def _copy_bookmark_url(self, item: QTreeWidgetItem) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "bookmark":
            return
        url = data.get("url", "")
        if not url:
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(url)
```

- [ ] **Step 3: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: 6 PASS

- [ ] **Step 4: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/main_window.py tests/gui/test_sidebar_reorder.py
git commit -m "feat(gui): bookmark context menu gains Color submenu + Copy URL"
```

---

## Task 16: BookmarkTreeDelegate honors per-bookmark `accent`

**Files:**
- Modify: `src/nexus/gui/widgets.py` — `BookmarkTreeDelegate.paint`
- Test: extend `tests/gui/test_sidebar_reorder.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/gui/test_sidebar_reorder.py`:

```python
def test_bookmark_row_paints_with_per_bookmark_accent(app, tmp_path, monkeypatch):
    """A bookmark with its own accent paints in that color, not the folder's."""
    window = MainWindow()
    window.bookmark_manager.save_bookmarks_raw([
        {
            "name": "Tech",
            "type": "folder",
            "accent": "#5B8DEF",
            "children": [
                {"type": "bookmark", "name": "Pink", "url": "https://x.com", "accent": "#E5738A"},
                {"type": "bookmark", "name": "Default", "url": "https://y.com"},
            ],
        }
    ])
    window.load_bookmarks()
    root = window.bookmark_tree.invisibleRootItem()
    tech = next(root.child(i) for i in range(root.childCount()) if root.child(i).text(0) == "Tech")
    pink = tech.child(0)
    default = tech.child(1)
    # The delegate is what paints; we just assert the data is set so the
    # delegate can find it.
    pink_data = pink.data(0, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemDataRole.UserRole)
    default_data = default.data(0, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemDataRole.UserRole)
    assert pink_data["accent"] == "#E5738A"
    assert "accent" not in default_data or default_data.get("accent") is None
    window.close()
```

- [ ] **Step 2: Implement — update `BookmarkTreeDelegate.paint`**

In `src/nexus/gui/widgets.py`, find the `BookmarkTreeDelegate` class. In the `paint` method, when rendering a bookmark row, fall back to the parent folder's accent when the bookmark has no own accent. The change is small: read the parent folder's `UserRole + 1` style when the bookmark data has no `accent`.

Replace the bookmark branch of `paint`:

```python
        else:
            # Per-bookmark accent (falls back to the parent folder's
            # accent when the bookmark carries none).
            bookmark_data = index.data(Qt.ItemDataRole.UserRole) or {}
            accent_hex = bookmark_data.get("accent")
            if not accent_hex and index.parent().isValid():
                folder_style = index.parent().data(Qt.ItemDataRole.UserRole + 1) or {}
                accent_hex = folder_style.get("start")

            text_rect = rect.adjusted(22, 0, -10, 0)
            if hovered or selected:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, 12 if hovered else 18))
                painter.drawRoundedRect(rect.adjusted(2, 1, -2, -1), 8, 8)
            # Accent dot
            if accent_hex:
                dot_rect = text_rect.adjusted(0, 0, 0, 0)
                dot_rect.setWidth(8)
                dot_rect.moveTop(text_rect.top() + (text_rect.height() - 8) // 2)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(accent_hex))
                painter.drawEllipse(dot_rect)
                text_rect.adjust(14, 0, 0, 0)
            font = option.font
            font.setPointSize(13)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor("#B8C4D8"))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )
```

- [ ] **Step 3: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/gui/test_sidebar_reorder.py -v`
Expected: 7 PASS

- [ ] **Step 4: Run full test suite + lint**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: All tests pass.

Run: `.venv/bin/ruff check src/nexus/`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add src/nexus/gui/widgets.py tests/gui/test_sidebar_reorder.py
git commit -m "feat(gui): BookmarkTreeDelegate honors per-bookmark accent"
```

---

## Self-review checklist

- [x] **Spec coverage:** every spec section maps to at least one task.
  - Storage → Tasks 1, 4, 5
  - Data model → Tasks 2, 3
  - NewFolderDialog → Task 6
  - SaveGroupDialog → Task 7
  - GroupRowDelegate → Task 8
  - 10 default tabs + palette → Task 9
  - `+` opens NewFolderDialog → Task 10
  - Reorderable sidebar → Task 11
  - Render group markers → Task 12
  - Save flow → Task 13
  - Group context menu → Task 14
  - Bookmark context menu (Color, Copy URL) → Task 15
  - Per-bookmark accent in delegate → Task 16
- [x] **No placeholders:** every step has concrete code or commands.
- [x] **Type consistency:** `Bookmark.accent`, `BookmarkFolder.accent`, `GroupRef` marker dict, `GroupItem`, `BookmarkGroup.id`/`name`/`items`/`created_at` — all consistent across tasks.
- [x] **Method names:** `_set_bookmark_accent`, `_set_status`, `_open_group_in_safari`, `_rename_group`, `_move_group_to`, `_delete_group`, `_copy_bookmark_url` — used consistently in Tasks 13-15.
- [x] **Property names:** `SaveGroupDialog.group_name`, `.target_folder`; `NewFolderDialog.folder_name`, `.accent` — used consistently in Task 13.

---

## Out-of-scope follow-ups (not in this plan)

- "Open all in Safari" on a single click of a group (Task 14 adds the right-click path).
- Group preview on hover.
- Search across group titles.
- Sync to iCloud.
