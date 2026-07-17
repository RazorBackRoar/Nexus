"""GroupRowDelegate paints without crashing and exposes a sane sizeHint."""

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QAbstractListModel, QModelIndex, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem

from nexus.gui.widgets.group_row_delegate import GroupRowDelegate


@pytest.fixture
def app():
    a = QApplication.instance() or QApplication([])
    yield a


def _empty_model():
    class _Model(QAbstractListModel):
        def rowCount(self, parent=QModelIndex()):
            return 0

    return _Model()


def _make_option(width: int = 240) -> QStyleOptionViewItem:
    opt = QStyleOptionViewItem()
    opt.rect = opt.rect.__class__(0, 0, width, 36)
    return opt


def test_paint_does_not_crash(app):
    delegate = GroupRowDelegate()
    delegate.paint(None, _make_option(), _empty_model().index(0, 0))


def test_size_hint_is_at_least_30px_tall(app):
    delegate = GroupRowDelegate()
    size = delegate.sizeHint(_make_option(), _empty_model().index(0, 0))
    assert size.height() >= 30
    assert isinstance(size, QSize)


def test_accent_setter_round_trips(app):
    delegate = GroupRowDelegate()
    delegate.set_accent(QColor("#5B8DEF"))
    assert delegate.accent().name().lower() == "#5b8def"


def test_child_count_setter_round_trips(app):
    delegate = GroupRowDelegate()
    delegate.set_child_count(7)
    assert delegate._child_count == 7
    delegate.set_child_count(None)
    assert delegate._child_count is None
