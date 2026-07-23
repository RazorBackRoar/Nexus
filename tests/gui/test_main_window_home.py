"""Tests for Home navigation via Home button and Nexus title click."""

import os
import sys

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from nexus.gui.main_window import MainWindow


def test_home_button_returns_to_url_table_view():
    _app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    try:
        window._show_quick_save_view()
        assert window.url_stack.currentWidget() == window.quick_save_panel

        window.home_btn.click()
        assert window.url_stack.currentWidget() in (window.url_empty_state, window.url_table)
    finally:
        window.close()


def test_title_label_left_click_returns_home():
    _app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    try:
        window._show_quick_save_view()
        assert window.url_stack.currentWidget() == window.quick_save_panel

        event = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            window.title_label.rect().center(),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        handled = window.eventFilter(window.title_label, event)
        assert handled is True
        assert window.url_stack.currentWidget() in (window.url_empty_state, window.url_table)
    finally:
        window.close()
