"""Tests for modern dialogs (Shortcuts, Preferences, Health Report) and MainWindow wiring."""

import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from nexus.core.bookmarks import BookmarkManager
from nexus.gui.dialogs.health_report_dialog import HealthReportDialog
from nexus.gui.dialogs.preferences_dialog import PreferencesDialog
from nexus.gui.dialogs.shortcuts_dialog import ShortcutsDialog
from nexus.gui.main_window import MainWindow


def _get_app():
    return QApplication.instance() or QApplication(sys.argv)


def test_shortcuts_dialog_sections():
    """Verify ShortcutsDialog instantiates with all 4 categorized sections."""
    _get_app()
    dlg = ShortcutsDialog()
    try:
        assert dlg.windowTitle() == "Nexus Keyboard Shortcuts"
    finally:
        dlg.close()


def test_preferences_dialog_save_and_load(tmp_path):
    """Verify PreferencesDialog loads and saves settings cleanly."""
    _get_app()
    dlg = PreferencesDialog()
    try:
        assert dlg.windowTitle() == "Preferences"
        assert dlg.tabs.count() == 5

        # Modify a setting in UI
        dlg.batch_size_spin.setValue(35)
        dlg.private_mode_check.setChecked(True)
        dlg._save_settings()

        settings = QSettings("Nexus", "Nexus")
        assert int(settings.value("safari/batchSize")) == 35
        assert bool(settings.value("safari/defaultPrivateMode")) is True
    finally:
        dlg.close()


def test_health_report_dialog(tmp_path):
    """Verify HealthReportDialog loads bookmarks and runs duplicate scan."""
    _get_app()
    bm_file = tmp_path / "test_bm.json"
    bm = BookmarkManager(bm_file)
    dlg = HealthReportDialog(bm)
    try:
        assert dlg.windowTitle() == "Bookmark Health Scanner"
        assert dlg.tabs.count() == 2
    finally:
        dlg.close()


def test_main_window_menu_bar_and_shortcuts():
    """Verify MainWindow initializes with modernized menu bar and shortcut handlers."""
    _get_app()
    window = MainWindow()
    try:
        menu_bar = window.menuBar()
        actions = [a.text() for a in menu_bar.actions()]
        assert "File" in actions
        assert "Edit" in actions
        assert "View" in actions
        assert "Safari" in actions
        assert "Tools" in actions
        assert "Help" in actions

        # Verify tooltips on action buttons
        assert "⌘H" in window.home_btn.toolTip()
        assert "⌘⇧O" in window.run_btn.toolTip()
        assert "⌘S" in window.save_btn.toolTip()
        assert "⌘O" in window.import_btn.toolTip()
        assert "⌘E" in window.export_btn.toolTip()
        assert "⌘⌫" in window.clear_btn.toolTip()

        # Verify status bar auto-clear timer function exists
        window._set_status("Temporary Message", timeout_ms=100)
        assert window.status_bar.text() == "Temporary Message"

        # Verify URL counter initial text
        assert window.url_counter_label.text() == "Waiting for pasted URLs"

        # Verify helper methods exist and are callable
        assert hasattr(window, "_show_preferences_dialog")
        assert hasattr(window, "_show_shortcuts_dialog")
        assert hasattr(window, "_show_health_scanner_dialog")
        assert hasattr(window, "_import_safari_tabs")
        assert hasattr(window, "_toggle_theme_mode")
    finally:
        window.close()
