"""SaveGroupDialog collects a name and a target folder."""

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QDialogButtonBox

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
    button_box = dlg.findChild(QDialogButtonBox)
    ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
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


def test_preselect_picks_the_named_folder(app):
    dlg = SaveGroupDialog(folders=["Favorites", "Work", "Tech"], preselect="Tech")
    assert dlg.target_folder == "Tech"
