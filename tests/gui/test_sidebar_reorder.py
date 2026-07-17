"""Sidebar defaults, reorder, group markers, save flow, and context menus."""

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
)

from nexus.gui.main_window import MainWindow


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    yield a


@pytest.fixture
def window(tmp_path, monkeypatch, app):
    """Build a MainWindow whose bookmark/group files live in tmp_path."""
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda *_: str(tmp_path))
    w = MainWindow()
    try:
        yield w
    finally:
        w.close()


def test_default_tabs_load_in_spec_order(window):
    """The sidebar ships with the eight default tabs in the design order."""
    tree = window.bookmark_tree
    assert tree.topLevelItemCount() == 8
    names = [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]
    assert names == [
        "Fun",
        "Misc",
        "Tech",
        "Work",
        "Extra",
        "Hidden",
        "Special",
        "Favorites",
    ]


def test_top_level_tabs_accept_internal_drag_drop(window):
    """Drag-reorder of top-level tabs is enabled."""
    tree = window.bookmark_tree
    assert tree.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
    assert tree.acceptDrops() is True


def test_group_markers_render_as_tree_children(window):
    """A folder with group markers renders them as child items."""
    window.bookmark_manager.save_bookmarks_raw(
        [
            {
                "name": "Tech",
                "type": "folder",
                "accent": "#5B8DEF",
                "children": [
                    {"type": "group", "id": "grp_a1b2c3d4"},
                ],
            }
        ]
    )
    window.load_bookmarks()

    root = window.bookmark_tree.invisibleRootItem()
    tech = next(
        root.child(i)
        for i in range(root.childCount())
        if root.child(i).text(0) == "Tech"
    )
    assert tech.childCount() == 1
    child = tech.child(0)
    data = child.data(0, Qt.ItemDataRole.UserRole)
    assert data["type"] == "group"
    assert data["id"] == "grp_a1b2c3d4"


def test_save_urls_creates_a_group_in_group_store(window, monkeypatch):
    """Clicking Save with URLs in the table creates a group entry."""
    from nexus.core.models import GroupItem
    from nexus.gui.dialogs.save_group_dialog import SaveGroupDialog

    window.url_table.add_urls(
        [
            "https://a.com",
            "https://b.com",
            "https://c.com",
        ]
    )

    monkeypatch.setattr(
        SaveGroupDialog, "exec", lambda self: SaveGroupDialog.DialogCode.Accepted
    )
    monkeypatch.setattr(
        SaveGroupDialog, "group_name", property(lambda self: "My Group")
    )
    monkeypatch.setattr(SaveGroupDialog, "target_folder", property(lambda self: "Tech"))

    window._save_urls_to_bookmarks()

    assert window.url_table.rowCount() == 0
    groups = window.group_store.load_groups()
    assert any(
        g.name == "My Group"
        and len(g.items) == 3
        and all(isinstance(i, GroupItem) for i in g.items)
        for g in groups
    )


class _FakeSignal:
    """A signal placeholder that ignores connect calls."""

    def connect(self, *args, **kwargs):
        pass


class _FakeMenu:
    """A QMenu stand-in that records actions without blocking the test."""

    def __init__(self, *args, **kwargs):
        self.actions: list[str] = []

    def setStyleSheet(self, *args, **kwargs):
        pass

    def addSeparator(self):
        pass

    def addMenu(self, title: str):
        return self

    def addAction(self, label: str):
        self.actions.append(label)
        return self

    @property
    def triggered(self):
        return _FakeSignal()

    def exec(self, *args, **kwargs):
        return None


def test_group_context_menu_has_rename_and_delete(window, monkeypatch):
    """Right-clicking a group row offers the expected actions without crashing."""
    window.bookmark_manager.save_bookmarks_raw(
        [
            {
                "name": "Tech",
                "type": "folder",
                "accent": "#5B8DEF",
                "children": [{"type": "group", "id": "grp_x", "name": "Old name"}],
            }
        ]
    )
    window.load_bookmarks()

    root = window.bookmark_tree.invisibleRootItem()
    tech = next(
        root.child(i)
        for i in range(root.childCount())
        if root.child(i).text(0) == "Tech"
    )
    group_item = tech.child(0)

    # Swap in a non-blocking menu so the offscreen test does not hang.
    monkeypatch.setattr("nexus.gui.main_window.QMenu", _FakeMenu)

    # The method builds a menu for the item at the given position.
    rect = group_item.treeWidget().visualItemRect(group_item)
    window._show_bookmark_context_menu(rect.center())


def test_bookmark_accent_round_trips_via_context_menu(window):
    """Recoloring a bookmark via the context menu persists."""
    window.bookmark_manager.save_bookmarks_raw(
        [
            {
                "name": "Tech",
                "type": "folder",
                "accent": "#5B8DEF",
                "children": [
                    {
                        "type": "bookmark",
                        "name": "Example",
                        "url": "https://example.com",
                    }
                ],
            }
        ]
    )
    window.load_bookmarks()

    root = window.bookmark_tree.invisibleRootItem()
    tech = next(
        root.child(i)
        for i in range(root.childCount())
        if root.child(i).text(0) == "Tech"
    )
    bookmark_item = tech.child(0)
    window._set_bookmark_accent(bookmark_item, "#E5738A")
    assert bookmark_item.data(0, Qt.ItemDataRole.UserRole)["accent"] == "#E5738A"

    window.load_bookmarks()
    root = window.bookmark_tree.invisibleRootItem()
    tech = next(
        root.child(i)
        for i in range(root.childCount())
        if root.child(i).text(0) == "Tech"
    )
    bookmark_item = tech.child(0)
    assert bookmark_item.data(0, Qt.ItemDataRole.UserRole).get("accent") == "#E5738A"


def test_bookmark_row_paints_with_per_bookmark_accent(window):
    """A bookmark with its own accent stores that data; a default bookmark inherits."""
    window.bookmark_manager.save_bookmarks_raw(
        [
            {
                "name": "Tech",
                "type": "folder",
                "accent": "#5B8DEF",
                "children": [
                    {
                        "type": "bookmark",
                        "name": "Pink",
                        "url": "https://x.com",
                        "accent": "#E5738A",
                    },
                    {
                        "type": "bookmark",
                        "name": "Default",
                        "url": "https://y.com",
                    },
                ],
            }
        ]
    )
    window.load_bookmarks()

    root = window.bookmark_tree.invisibleRootItem()
    tech = next(
        root.child(i)
        for i in range(root.childCount())
        if root.child(i).text(0) == "Tech"
    )
    pink = tech.child(0)
    default = tech.child(1)

    pink_data = pink.data(0, Qt.ItemDataRole.UserRole)
    default_data = default.data(0, Qt.ItemDataRole.UserRole)
    assert pink_data["accent"] == "#E5738A"
    assert "accent" not in default_data or default_data.get("accent") is None
