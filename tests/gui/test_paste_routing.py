"""Unit tests for BookmarkSearchBar, URLEmptyStateWidget, and paste routing."""

import os
from typing import cast

from PySide6.QtCore import QMimeData, Qt, QUrl
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QMenu

from nexus.gui.main_window import MainWindow
from nexus.gui.widgets import (
    BookmarkSearchBar,
    URLEmptyStateWidget,
    extract_urls_from_mime_data,
)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return cast(QApplication, app)


def test_bookmark_search_bar_intercepts_url_paste():
    _app()
    search_bar = BookmarkSearchBar()
    pasted = []
    search_bar.urls_pasted.connect(pasted.extend)

    clipboard = QApplication.clipboard()
    assert clipboard is not None
    clipboard.setText("https://apple.com\nhttps://google.com")

    # Simulate Cmd+V paste event
    key_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_V,
        Qt.KeyboardModifier.ControlModifier,
    )
    search_bar.keyPressEvent(key_event)

    assert pasted == ["https://apple.com", "https://google.com"]
    assert search_bar.text() == ""  # Search bar filter remains clean


def test_bookmark_search_bar_allows_plain_text_search():
    _app()
    search_bar = BookmarkSearchBar()
    pasted = []
    search_bar.urls_pasted.connect(pasted.extend)

    key_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_A,
        Qt.KeyboardModifier.NoModifier,
        "a",
    )
    search_bar.keyPressEvent(key_event)

    assert len(pasted) == 0
    assert search_bar.text() == "a"


def test_bookmark_search_bar_does_not_swallow_non_url_paste():
    _app()
    search_bar = BookmarkSearchBar()
    pasted = []
    search_bar.urls_pasted.connect(pasted.extend)

    clipboard = QApplication.clipboard()
    assert clipboard is not None
    clipboard.setText("search bookmarks")

    key_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_V,
        Qt.KeyboardModifier.ControlModifier,
    )
    search_bar.keyPressEvent(key_event)

    # Not intercepted as URLs; allowed to paste normally into the line edit
    assert len(pasted) == 0
    assert search_bar.text() == "search bookmarks"


def test_url_empty_state_widget_paste_and_focus():
    _app()
    widget = URLEmptyStateWidget()
    pasted = []
    widget.urls_pasted.connect(pasted.extend)

    clipboard = QApplication.clipboard()
    assert clipboard is not None
    clipboard.setText("Check out https://github.com/RazorBackRoar/Nexus")

    # Key press ⌘V
    key_event = QKeyEvent(
        QKeyEvent.Type.KeyPress,
        Qt.Key.Key_V,
        Qt.KeyboardModifier.MetaModifier,
    )
    widget.keyPressEvent(key_event)

    assert pasted == ["https://github.com/RazorBackRoar/Nexus"]


def test_main_window_global_paste_routing():
    _app()
    window = MainWindow()
    assert window.url_table.rowCount() == 0

    clipboard = QApplication.clipboard()
    assert clipboard is not None
    clipboard.setText("https://nexus.local\nhttps://safari.local")

    window._handle_global_paste()

    assert window.url_table.rowCount() == 2
    assert window.url_table.get_all_urls() == [
        "https://nexus.local",
        "https://safari.local",
    ]


def test_url_table_repeated_paste_adds_rows_without_editor_hijack():
    _app()
    window = MainWindow()
    clipboard = QApplication.clipboard()
    assert clipboard is not None

    # First paste
    clipboard.setText("https://first.com")
    window.keyPressEvent(
        QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_V,
            Qt.KeyboardModifier.ControlModifier,
        )
    )
    assert window.url_table.rowCount() == 1
    assert window.url_table.get_all_urls() == ["https://first.com"]

    # Second paste directly on url_table
    clipboard.setText("https://second.com")
    window.url_table.keyPressEvent(
        QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_V,
            Qt.KeyboardModifier.ControlModifier,
        )
    )
    assert window.url_table.rowCount() == 2
    assert window.url_table.get_all_urls() == [
        "https://first.com",
        "https://second.com",
    ]

    # Third paste via global paste handler
    clipboard.setText("https://third.com")
    window.paste_action.trigger()
    assert window.url_table.rowCount() == 3
    assert window.url_table.get_all_urls() == [
        "https://first.com",
        "https://second.com",
        "https://third.com",
    ]


def test_url_table_mouse_press_does_not_open_inline_editor():
    from PySide6.QtTest import QTest

    _app()
    window = MainWindow()
    window._handle_pasted_urls(["https://apple.com"])
    item = window.url_table.item(0, 1)
    assert item is not None

    rect = window.url_table.visualItemRect(item)
    QTest.mouseClick(
        window.url_table.viewport(),
        Qt.MouseButton.LeftButton,
        pos=rect.center(),
    )

    # In-place editor should not be active
    assert window.url_table.state() != window.url_table.State.EditingState


def test_extract_urls_from_mime_data_html_and_urls():
    from nexus.utils.url_processor import URLProcessor

    processor = URLProcessor()

    # Direct URLs
    mime_urls = QMimeData()
    mime_urls.setUrls([QUrl("https://github.com/one"), QUrl("https://github.com/two")])
    assert extract_urls_from_mime_data(mime_urls, processor) == [
        "https://github.com/one",
        "https://github.com/two",
    ]

    # Rich HTML content
    mime_html = QMimeData()
    mime_html.setHtml(
        '<a href="https://apple.com">Apple</a> and <a href="https://webkit.org">WebKit</a>'
    )
    assert extract_urls_from_mime_data(mime_html, processor) == [
        "https://apple.com",
        "https://webkit.org",
    ]


def test_main_window_menu_bar_has_edit_menu_with_shortcuts():
    _app()
    window = MainWindow()
    menu_bar = window.menuBar()
    actions = {act.text(): act for act in menu_bar.actions()}
    assert "Edit" in actions
    edit_menu = cast(QMenu, actions["Edit"].menu())

    edit_actions = {act.text(): act for act in edit_menu.actions()}
    assert "Paste" in edit_actions
    assert edit_actions["Paste"].shortcut() == QKeySequence(
        QKeySequence.StandardKey.Paste
    )
    assert "Copy" in edit_actions
    assert edit_actions["Copy"].shortcut() == QKeySequence(
        QKeySequence.StandardKey.Copy
    )
    assert "Undo" in edit_actions
    assert edit_actions["Undo"].shortcut() == QKeySequence(
        QKeySequence.StandardKey.Undo
    )


def test_url_processor_domain_with_port_support():
    from nexus.utils.url_processor import URLProcessor

    processor = URLProcessor()
    assert processor.extract_urls("https://example.com:8443/api/v1") == [
        "https://example.com:8443/api/v1"
    ]
