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
