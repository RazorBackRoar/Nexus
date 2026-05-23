"""Focused GUI skin regression tests."""

import json
import os
import sys

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QApplication,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
)

import nexus.gui.main_window as main_window_module
from nexus.gui.widgets import BookmarkTreeDelegate, URLTableWidget


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_url_table_uses_named_status_states():
    _app()
    table = URLTableWidget()
    table.add_urls(["https://example.com"])

    assert table.isColumnHidden(0)
    assert table.item(0, 2).text() == "Ready"
    assert table.item(0, 2).data(Qt.ItemDataRole.UserRole) == "ready"

    table.set_status_state(0, "opening")
    assert table.item(0, 2).text() == "Opening"

    table.update_status(0, True)
    assert table.item(0, 2).text() == "Opened"
    assert table.item(0, 2).data(Qt.ItemDataRole.UserRole) == "opened"


def test_url_table_emits_url_activation_and_replacement_state():
    _app()
    table = URLTableWidget()
    activated: list[tuple[int, str]] = []
    changed: list[list[str]] = []
    table.url_activated.connect(lambda row, url: activated.append((row, url)))
    table.urls_changed.connect(lambda urls: changed.append(urls))

    table.add_urls(["https://example.com"])
    table._activate_item_url(table.item(0, 1))

    assert activated == [(0, "https://example.com")]
    assert changed[-1] == ["https://example.com"]

    table.replace_urls(["https://openai.com", "https://github.com"])
    assert table.get_all_urls() == ["https://openai.com", "https://github.com"]
    assert changed[-1] == ["https://openai.com", "https://github.com"]


def test_bookmark_delegate_gives_folders_more_height():
    _app()
    tree = QTreeWidget()
    delegate = BookmarkTreeDelegate(tree)
    option = QStyleOptionViewItem()

    folder = QTreeWidgetItem(["Favorites"])
    folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": "Favorites"})
    tree.addTopLevelItem(folder)

    bookmark = QTreeWidgetItem(["Example"])
    bookmark.setData(
        0,
        Qt.ItemDataRole.UserRole,
        {"type": "bookmark", "name": "Example", "url": "https://example.com"},
    )
    folder.addChild(bookmark)

    folder_height = delegate.sizeHint(option, tree.indexFromItem(folder)).height()
    bookmark_height = delegate.sizeHint(option, tree.indexFromItem(bookmark)).height()

    assert folder_height > bookmark_height
    assert folder_height >= 64


def test_main_window_starts_with_empty_url_state(tmp_path, monkeypatch):
    _app()

    class _TestPaths:
        class StandardLocation:
            AppDataLocation = object()

        @staticmethod
        def writableLocation(_location):
            return str(tmp_path)

    monkeypatch.setattr(main_window_module, "QStandardPaths", _TestPaths)
    monkeypatch.setattr(
        main_window_module,
        "QSettings",
        lambda: QSettings(str(tmp_path / "ui.ini"), QSettings.Format.IniFormat),
    )

    window = main_window_module.MainWindow()
    try:
        assert window.url_table.rowCount() == 0
        assert window.url_stack.currentWidget() is window.url_empty_state
        assert not window.run_btn.isEnabled()
        assert not window.save_btn.isEnabled()
        assert not window.clear_btn.isEnabled()
    finally:
        window.close()


def test_main_window_uses_custom_titlebar_shell_on_macos(tmp_path, monkeypatch):
    _app()

    class _TestPaths:
        class StandardLocation:
            AppDataLocation = object()

        @staticmethod
        def writableLocation(_location):
            return str(tmp_path)

    monkeypatch.setattr(main_window_module, "QStandardPaths", _TestPaths)
    monkeypatch.setattr(
        main_window_module,
        "QSettings",
        lambda: QSettings(str(tmp_path / "ui.ini"), QSettings.Format.IniFormat),
    )

    window = main_window_module.MainWindow()
    try:
        flags = window.windowFlags()
        if sys.platform == "darwin":
            assert flags & Qt.WindowType.FramelessWindowHint
            assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            assert hasattr(window, "window_titlebar")
            assert window.window_titlebar.title_label.text() == ""
            assert window.window_titlebar.title_label.isHidden()
            assert window.window_titlebar.close_button.width() == 16
            assert window.window_titlebar.minimize_button.width() == 16
    finally:
        window.close()


def test_main_window_migrates_sidebar_folders_to_reference_set(tmp_path, monkeypatch):
    _app()

    class _TestPaths:
        class StandardLocation:
            AppDataLocation = object()

        @staticmethod
        def writableLocation(_location):
            return str(tmp_path)

    monkeypatch.setattr(main_window_module, "QStandardPaths", _TestPaths)
    monkeypatch.setattr(
        main_window_module,
        "QSettings",
        lambda: QSettings(str(tmp_path / "ui.ini"), QSettings.Format.IniFormat),
    )

    bookmark_path = tmp_path / main_window_module.Config.BOOKMARKS_FILE
    bookmark_path.write_text(
        json.dumps(
            [
                {"name": "Favorites", "type": "folder", "children": []},
                {"name": "Tech", "type": "folder", "children": []},
                {"name": "Misc", "type": "folder", "children": []},
                {"name": "Work", "type": "folder", "children": []},
                {"name": "Later", "type": "folder", "children": []},
                {"name": "Apple", "type": "folder", "children": []},
                {"name": "Google", "type": "folder", "children": []},
                {"name": "Github", "type": "folder", "children": []},
                {"name": "Fun", "type": "folder", "children": []},
                {
                    "name": "Reading",
                    "type": "folder",
                    "children": [
                        {"name": "Example", "type": "bookmark", "url": "https://example.com"}
                    ],
                },
            ]
        ),
        encoding="utf-8",
    )

    window = main_window_module.MainWindow()
    try:
        names = [
            window.bookmark_tree.topLevelItem(index).text(0)
            for index in range(window.bookmark_tree.topLevelItemCount())
        ]
        assert names == ["Favorites", "Tech", "Misc", "Work", "Later", "News"]

        misc_item = window.bookmark_tree.topLevelItem(2)
        assert misc_item.text(0) == "Misc"
        assert misc_item.childCount() == 1
        assert misc_item.child(0).text(0) == "Example"

        misc_style = misc_item.data(0, Qt.ItemDataRole.UserRole + 1)
        assert misc_style["start"] == "#7025CF"
    finally:
        window.close()
