"""Tests for Quick Save block selection, Open All, and Export functionality."""

import os
import sys

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication, QFileDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from nexus.gui.main_window import MainWindow
from nexus.gui.widgets.quick_save_panel import QuickSavePanel


def test_quick_save_block_selection_no_default():
    _app = QApplication.instance() or QApplication(sys.argv)
    panel = QuickSavePanel()
    entries = [
        {
            "id": "qs_1",
            "urls": ["https://alpha.com", "https://beta.com"],
            "notes": "First",
        },
        {"id": "qs_2", "urls": ["https://gamma.com"], "notes": "Second"},
    ]
    panel.set_entries(entries)

    # No block is selected by default
    assert panel.selected_block_id is None
    assert panel.get_selected_urls() == []

    # Select second block explicitly
    panel.select_block("qs_2")
    assert panel.selected_block_id == "qs_2"
    assert panel.get_selected_urls() == ["https://gamma.com"]


def test_export_urls_to_file(tmp_path, monkeypatch):
    _app = QApplication.instance() or QApplication(sys.argv)
    monkeypatch.setattr(QStandardPaths, "writableLocation", lambda *_: str(tmp_path))
    window = MainWindow()
    try:
        entries = [
            {
                "id": "qs_1",
                "urls": ["https://apple.com", "https://google.com"],
                "notes": "Test Export",
            },
        ]
        window.quick_save_panel.set_entries(entries)
        window.url_stack.setCurrentWidget(window.quick_save_panel)

        # Select block first
        window.quick_save_panel.select_block("qs_1")

        target_file = tmp_path / "exported_urls.txt"
        monkeypatch.setattr(
            QFileDialog,
            "getSaveFileName",
            lambda *args, **kwargs: (str(target_file), "Text Files (*.txt)"),
        )
        # Offscreen QMessageBox.exec() never returns — stub the success toast.
        monkeypatch.setattr(window, "_show_message", lambda *args, **kwargs: None)

        window._export_urls()
        assert target_file.exists()
        lines = target_file.read_text(encoding="utf-8").strip().splitlines()
        assert "https://apple.com" in lines
        assert "https://google.com" in lines
    finally:
        window.close()
