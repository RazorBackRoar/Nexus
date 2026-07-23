"""Unit tests for BookmarkSearchBar, URLEmptyStateWidget, and paste routing."""

import os
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from nexus.gui.main_window import MainWindow
from nexus.gui.widgets import BookmarkSearchBar, URLEmptyStateWidget


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
