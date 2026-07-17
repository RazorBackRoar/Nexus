"""Paint delegate for the indented group rows in the sidebar."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem


class GroupRowDelegate(QStyledItemDelegate):
    """Renders a group row: small accent dot, name, child count badge."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._accent = QColor("#6B9AF5")
        self._child_count: int | None = None

    def set_accent(self, color: QColor) -> None:
        self._accent = QColor(color)

    def accent(self) -> QColor:
        return self._accent

    def set_child_count(self, count: int | None) -> None:
        self._child_count = count

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # noqa: ANN001
        return QSize(option.rect.width(), 36)

    def paint(self, painter, option, index):  # noqa: ANN001
        if painter is None:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(22, 4, -10, -4)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        if hovered or selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 14 if hovered else 22))
            painter.drawRoundedRect(rect, 8, 8)

        # Accent dot
        dot_size = max(8, rect.height() - 12)
        dot = rect.adjusted(2, 6, 0, 0)
        dot.setWidth(dot_size)
        dot.setHeight(dot_size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._accent)
        painter.drawEllipse(dot)

        # Group name
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        font: QFont = option.font
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#D0DAEA"))
        text_rect = rect.adjusted(rect.height() + 6, 0, -52, 0)
        metrics = painter.fontMetrics()
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            elided,
        )

        # Child count badge
        if self._child_count is not None and self._child_count > 0:
            badge_text = f"({self._child_count})"
            painter.setPen(QColor("#8EA0BC"))
            badge_rect = rect.adjusted(rect.width() - 44, 0, -4, 0)
            painter.drawText(
                badge_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                badge_text,
            )

        painter.restore()
