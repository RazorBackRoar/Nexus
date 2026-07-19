"""Quick Save column: migration, block persistence, and panel wiring."""

from __future__ import annotations

import json
import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from nexus.gui.main_window import QUICK_SAVE_FOLDER_NAME, MainWindow


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    yield a


@pytest.fixture
def window(tmp_path, monkeypatch, app):
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda *_: str(tmp_path))
    w = MainWindow()
    try:
        yield w
    finally:
        w.close()


def _folder_names(window: MainWindow) -> list[str]:
    tree = window.bookmark_tree
    return [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())]


def test_quick_save_folder_is_first_and_has_no_tree_children(window):
    names = _folder_names(window)
    assert names[0] == QUICK_SAVE_FOLDER_NAME
    folder = window._find_folder_by_name(QUICK_SAVE_FOLDER_NAME)
    assert folder is not None
    assert folder.childCount() == 0


def test_retired_hey_and_sort_tabs_are_removed(tmp_path, monkeypatch, app):
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda *_: str(tmp_path))
    bookmark_path = tmp_path / "bookmarks_v2.json"
    bookmark_path.write_text(
        json.dumps(
            [
                {"name": "hey", "type": "folder", "children": []},
                {"name": "Sort", "type": "folder", "children": []},
                {"name": "Fun", "type": "folder", "children": []},
            ]
        ),
        encoding="utf-8",
    )

    window = MainWindow()
    try:
        names = _folder_names(window)
        assert "hey" not in names
        assert "Sort" not in names
        assert names[0] == QUICK_SAVE_FOLDER_NAME
        assert "Fun" in names
    finally:
        window.close()


def test_quick_save_urls_creates_newest_first_block(window):
    window.url_table.add_urls(
        ["https://example.com/one", "https://example.com/two"]
    )
    window._quick_save_urls()

    folder = window._find_folder_by_name(QUICK_SAVE_FOLDER_NAME)
    assert folder is not None
    data = folder.data(0, Qt.ItemDataRole.UserRole)
    children = data.get("children") or []
    assert len(children) == 1
    entry = children[0]
    assert entry["type"] == "quick_save"
    assert entry["urls"] == [
        "https://example.com/one",
        "https://example.com/two",
    ]
    assert entry.get("notes", "") == ""
    assert folder.childCount() == 0
    assert window.url_stack.currentWidget() is window.quick_save_panel


def test_legacy_quick_saves_bookmarks_migrate_to_blocks(tmp_path, monkeypatch, app):
    from PySide6.QtCore import QStandardPaths

    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda *_: str(tmp_path))
    bookmark_path = tmp_path / "bookmarks_v2.json"
    bookmark_path.write_text(
        json.dumps(
            [
                {
                    "name": "Quick Saves",
                    "type": "folder",
                    "children": [
                        {
                            "name": "Example",
                            "type": "bookmark",
                            "url": "https://example.com/legacy",
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    window = MainWindow()
    try:
        names = _folder_names(window)
        assert "Quick Saves" not in names
        assert names[0] == QUICK_SAVE_FOLDER_NAME
        folder = window._find_folder_by_name(QUICK_SAVE_FOLDER_NAME)
        data = folder.data(0, Qt.ItemDataRole.UserRole)
        children = data.get("children") or []
        assert len(children) == 1
        assert children[0]["type"] == "quick_save"
        assert children[0]["urls"] == ["https://example.com/legacy"]
        assert folder.childCount() == 0
    finally:
        window.close()
