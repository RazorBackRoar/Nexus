"""Custom UI widgets for the Nexus application."""

import asyncio
import re

from PySide6.QtCore import (
    QEasingCurve,
    QMimeData,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from nexus.core.config import Config, logger
from nexus.utils.url_processor import URLProcessor


try:
    from razorcore.threading import BaseWorker
except Exception:
    # Fallback for standalone Nexus environments where razorcore is unavailable.
    class BaseWorker(QThread):
        finished = Signal(dict)
        error = Signal(str)

        def do_work(self):
            raise NotImplementedError

        def run(self):
            try:
                result = self.do_work() or {}
                self.finished.emit(result)
            except Exception as e:
                logger.error("Fallback worker error: %s", e, exc_info=True)
                self.error.emit(str(e))
                self.finished.emit({"error": str(e)})


class AsyncWorker(BaseWorker):  # ty: ignore[unsupported-base]
    """Generic worker for running asynchronous tasks off the main UI thread."""

    result_ready = Signal(object)

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__()
        self.coro_func = coro_func
        self.args = args
        self.kwargs = kwargs

    def do_work(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.coro_func(*self.args, **self.kwargs))
            self.result_ready.emit(result)
            return {"result": result}
        finally:
            if loop:
                asyncio.set_event_loop(None)
                if not loop.is_closed():
                    loop.close()


class CosmicFrame(QWidget):
    """A painted shell widget that provides the nebula-like frame from the UI reference."""

    _STAR_FIELD = (
        (0.06, 0.10, 2.2, 140),
        (0.14, 0.18, 1.6, 120),
        (0.22, 0.08, 1.8, 150),
        (0.34, 0.16, 1.4, 110),
        (0.48, 0.06, 2.0, 150),
        (0.58, 0.14, 1.3, 115),
        (0.72, 0.08, 1.8, 135),
        (0.84, 0.18, 1.6, 125),
        (0.92, 0.07, 2.1, 150),
        (0.10, 0.34, 1.7, 115),
        (0.28, 0.28, 1.4, 100),
        (0.42, 0.35, 1.9, 125),
        (0.60, 0.30, 1.5, 105),
        (0.78, 0.34, 1.8, 120),
        (0.88, 0.28, 1.3, 95),
        (0.08, 0.62, 1.6, 110),
        (0.18, 0.76, 2.0, 130),
        (0.32, 0.68, 1.2, 95),
        (0.52, 0.82, 1.8, 125),
        (0.66, 0.72, 1.4, 105),
        (0.82, 0.84, 1.6, 115),
        (0.94, 0.64, 2.0, 130),
    )

    _NEBULAE = (
        (0.10, 0.08, 0.36, "#4D1FA4", 92),
        (0.28, 0.42, 0.22, "#FF3E96", 34),
        (0.74, 0.08, 0.28, "#4EA3FF", 72),
        (0.66, 0.66, 0.30, "#2F7EFF", 58),
        (0.08, 0.92, 0.30, "#42168F", 88),
        (0.95, 0.42, 0.24, "#7C33FF", 68),
        (0.56, 0.84, 0.18, "#00DFFF", 24),
    )

    _GALAXY_SWIRLS = (
        (
            (0.00, 0.18),
            (0.18, 0.08),
            (0.46, 0.06),
            (0.96, 0.06),
            "#7B67FF",
            18,
            58.0,
        ),
        (
            (0.02, 0.84),
            (0.24, 0.88),
            (0.50, 0.78),
            (0.86, 0.60),
            "#5A46E8",
            16,
            42.0,
        ),
        (
            (0.16, 0.62),
            (0.28, 0.38),
            (0.58, 0.20),
            (0.92, 0.14),
            "#00CFFF",
            12,
            28.0,
        ),
        (
            (0.10, 0.74),
            (0.32, 0.58),
            (0.54, 0.42),
            (0.82, 0.34),
            "#FF4AA9",
            10,
            22.0,
        ),
    )

    def _scaled_point(self, rect: QRectF, rel_x: float, rel_y: float) -> tuple[float, float]:
        return (
            rect.left() + rect.width() * rel_x,
            rect.top() + rect.height() * rel_y,
        )

    def _paint_galaxy_swirl(
        self,
        painter: QPainter,
        rect: QRectF,
        start: tuple[float, float],
        ctrl1: tuple[float, float],
        ctrl2: tuple[float, float],
        end: tuple[float, float],
        color_hex: str,
        alpha: int,
        width: float,
    ) -> None:
        start_x, start_y = self._scaled_point(rect, *start)
        ctrl1_x, ctrl1_y = self._scaled_point(rect, *ctrl1)
        ctrl2_x, ctrl2_y = self._scaled_point(rect, *ctrl2)
        end_x, end_y = self._scaled_point(rect, *end)

        path = QPainterPath()
        path.moveTo(start_x, start_y)
        path.cubicTo(ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, end_x, end_y)

        glow_color = QColor(color_hex)
        glow_color.setAlpha(alpha)
        painter.setPen(QPen(glow_color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)

        crisp_color = QColor(color_hex)
        crisp_color.setAlpha(min(255, alpha + 34))
        painter.setPen(
            QPen(
                crisp_color,
                max(2.0, width * 0.12),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        painter.drawPath(path)

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1)
        rounded_rect = QPainterPath()
        rounded_rect.addRoundedRect(rect, 28, 28)

        base_gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base_gradient.setColorAt(0.0, QColor("#06030E"))
        base_gradient.setColorAt(0.20, QColor("#050712"))
        base_gradient.setColorAt(0.58, QColor("#030913"))
        base_gradient.setColorAt(1.0, QColor("#01040B"))
        painter.fillPath(rounded_rect, QBrush(base_gradient))

        depth_wash = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        depth_wash.setColorAt(0.0, QColor(92, 56, 190, 34))
        depth_wash.setColorAt(0.24, QColor(28, 18, 72, 18))
        depth_wash.setColorAt(0.68, QColor(9, 18, 42, 0))
        depth_wash.setColorAt(1.0, QColor(4, 8, 18, 0))
        painter.fillPath(rounded_rect, QBrush(depth_wash))

        painter.setClipPath(rounded_rect)

        galaxy_core = QRadialGradient(
            rect.left() + rect.width() * 0.66,
            rect.top() + rect.height() * 0.62,
            min(rect.width(), rect.height()) * 0.44,
        )
        galaxy_core.setColorAt(0.0, QColor(42, 122, 255, 58))
        galaxy_core.setColorAt(0.24, QColor(31, 82, 205, 22))
        galaxy_core.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(galaxy_core))
        painter.drawEllipse(
            QRectF(
                rect.left() + rect.width() * 0.22,
                rect.top() + rect.height() * 0.22,
                rect.width() * 0.76,
                rect.height() * 0.76,
            )
        )

        for rel_x, rel_y, radius_factor, color_hex, alpha in self._NEBULAE:
            center_x = rect.left() + rect.width() * rel_x
            center_y = rect.top() + rect.height() * rel_y
            radius = min(rect.width(), rect.height()) * radius_factor

            glow = QRadialGradient(center_x, center_y, radius)
            glow_color = QColor(color_hex)
            glow_color.setAlpha(alpha)
            edge_color = QColor(color_hex)
            edge_color.setAlpha(0)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(1.0, edge_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(
                QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            )

        for start, ctrl1, ctrl2, end, color_hex, alpha, width in self._GALAXY_SWIRLS:
            self._paint_galaxy_swirl(
                painter,
                QRectF(rect),
                start,
                ctrl1,
                ctrl2,
                end,
                color_hex,
                alpha,
                width,
            )

        for rel_x, rel_y, radius, alpha in self._STAR_FIELD:
            star_color = QColor("#F8FAFF")
            star_color.setAlpha(alpha)
            painter.setBrush(star_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(
                    rect.left() + rect.width() * rel_x,
                    rect.top() + rect.height() * rel_y,
                    radius,
                    radius,
                )
            )

        for idx in range(58):
            rel_x = 0.03 + (((idx * 29) + (idx // 6) * 7) % 92) / 100
            rel_y = 0.04 + (((idx * 17) + (idx // 5) * 11) % 88) / 100
            radius = 0.8 + (idx % 3) * 0.35
            alpha = 34 + (idx % 7) * 14
            tint = QColor("#EEF4FF" if idx % 4 else "#8ED7FF")
            tint.setAlpha(alpha)
            painter.setBrush(tint)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(
                    rect.left() + rect.width() * rel_x,
                    rect.top() + rect.height() * rel_y,
                    radius,
                    radius,
                )
            )

        for rel_x, rel_y, radius_factor, color_hex, alpha in (
            (0.24, 0.18, 0.10, "#FFFFFF", 18),
            (0.82, 0.16, 0.12, "#7CCFFF", 16),
            (0.60, 0.58, 0.16, "#6D7DFF", 14),
        ):
            center_x = rect.left() + rect.width() * rel_x
            center_y = rect.top() + rect.height() * rel_y
            radius = min(rect.width(), rect.height()) * radius_factor
            haze = QRadialGradient(center_x, center_y, radius)
            glow = QColor(color_hex)
            glow.setAlpha(alpha)
            edge = QColor(color_hex)
            edge.setAlpha(0)
            haze.setColorAt(0.0, glow)
            haze.setColorAt(1.0, edge)
            painter.setBrush(QBrush(haze))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
            )

        sheen = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.18, QColor(255, 255, 255, 18))
        sheen.setColorAt(0.38, QColor(145, 182, 255, 12))
        sheen.setColorAt(0.72, QColor(255, 125, 198, 10))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(QPen(QBrush(sheen), 1.4))
        painter.drawLine(rect.left() + 18, rect.top() + 16, rect.right() - 18, rect.top() + 16)

        painter.setClipping(False)

        outer_border = QLinearGradient(rect.topLeft(), rect.bottomRight())
        outer_border.setColorAt(0.0, QColor(127, 113, 255, 148))
        outer_border.setColorAt(0.35, QColor(78, 93, 212, 90))
        outer_border.setColorAt(0.75, QColor(42, 170, 255, 82))
        outer_border.setColorAt(1.0, QColor(132, 176, 255, 126))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(outer_border), 2.2))
        painter.drawRoundedRect(rect, 28, 28)

        inner_rect = rect.adjusted(6, 6, -6, -6)
        painter.setPen(QPen(QColor(115, 149, 255, 16), 1.0))
        painter.drawRoundedRect(inner_rect, 24, 24)

        super().paintEvent(event)


class TrafficLightButton(QPushButton):
    """Mac-style traffic light control with glossy finish."""

    def __init__(self, tone: str, symbol: str, parent=None):
        super().__init__(parent)
        self._tone = QColor(tone)
        self._symbol = symbol
        self._core_inset = 1
        if self._tone.lightness() > 150:
            self._core_inset = 0
        self.setFixedSize(16, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        core_rect = rect.adjusted(
            self._core_inset,
            self._core_inset,
            -self._core_inset,
            -self._core_inset,
        )
        glow = QColor(self._tone)
        glow.setAlpha(58 if self.underMouse() else 34)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(rect.adjusted(-1, -1, 1, 1))

        fill = QRadialGradient(
            core_rect.center().x(),
            core_rect.center().y(),
            core_rect.width() * 0.82,
        )
        fill.setColorAt(0.0, self._tone.lighter(124))
        fill.setColorAt(0.55, self._tone)
        fill.setColorAt(1.0, self._tone.darker(130))
        painter.setBrush(QBrush(fill))
        painter.drawEllipse(core_rect)

        gloss_rect = QRectF(
            core_rect.left() + 1,
            core_rect.top() + 1,
            core_rect.width() - 2,
            core_rect.height() * 0.50,
        )
        gloss = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
        gloss.setColorAt(0.0, QColor(255, 255, 255, 152))
        gloss.setColorAt(0.5, QColor(255, 255, 255, 38))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(gloss))
        painter.drawEllipse(gloss_rect)

        painter.setPen(QPen(QColor(255, 255, 255, 88), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(core_rect)

        rim = QColor(self._tone.darker(138))
        rim.setAlpha(110)
        painter.setPen(QPen(rim, 1.0))
        painter.drawEllipse(core_rect.adjusted(0, 0, -1, -1))

        if self.underMouse():
            font = painter.font()
            font.setPointSize(8)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(48, 32, 32, 176))
            painter.drawText(core_rect, Qt.AlignmentFlag.AlignCenter, self._symbol)


class WindowTitleBar(QWidget):
    """Custom glossy title bar so the window reads as a single shell."""

    def __init__(self, target_window: QWidget, title: str = "Nexus", parent=None):
        super().__init__(parent)
        self._target_window = target_window
        self._drag_offset: QPoint | None = None
        self.setFixedHeight(42)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 4)
        layout.setSpacing(0)

        controls = QWidget(self)
        controls.setStyleSheet("background: transparent;")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(9)

        self.close_button = TrafficLightButton("#F46B73", "×", controls)
        self.minimize_button = TrafficLightButton("#FFBD2E", "−", controls)
        self.zoom_button = TrafficLightButton("#28C840", "+", controls)

        controls_layout.addWidget(self.close_button)
        controls_layout.addWidget(self.minimize_button)
        controls_layout.addWidget(self.zoom_button)
        controls.setFixedWidth(102)

        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: rgba(242, 247, 255, 0.92);
                font-family: "Avenir Next";
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 0.4px;
                background: transparent;
            }
        """)
        self.title_label.hide()

        layout.addWidget(controls, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()

        self.close_button.clicked.connect(self._target_window.close)
        self.minimize_button.clicked.connect(self._target_window.showMinimized)
        self.zoom_button.clicked.connect(self._toggle_zoom)

    def _toggle_zoom(self):
        if self._target_window.isMaximized():
            self._target_window.showNormal()
        else:
            self._target_window.showMaximized()

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        band_rect = QRectF(rect.left(), rect.top(), rect.width(), rect.height() + 16)
        band = QLinearGradient(band_rect.topLeft(), band_rect.bottomLeft())
        band.setColorAt(0.0, QColor(42, 22, 104, 72))
        band.setColorAt(0.28, QColor(12, 16, 40, 42))
        band.setColorAt(0.76, QColor(4, 8, 20, 16))
        band.setColorAt(1.0, QColor(3, 6, 16, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(band))
        painter.drawRoundedRect(band_rect, 20, 20)

        sheen = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.top())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.12, QColor(255, 255, 255, 22))
        sheen.setColorAt(0.48, QColor(148, 173, 255, 12))
        sheen.setColorAt(0.84, QColor(101, 186, 255, 14))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(QPen(QBrush(sheen), 1.0))
        painter.drawLine(rect.left() + 10, rect.top() + 2, rect.right() - 10, rect.top() + 2)

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_zoom()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        child = self.childAt(event.position().toPoint())
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not isinstance(child, TrafficLightButton)
        ):
            self._drag_offset = (
                event.globalPosition().toPoint()
                - self._target_window.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and not self._target_window.isMaximized()
        ):
            self._target_window.move(
                event.globalPosition().toPoint() - self._drag_offset
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt override
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class BookmarkTreeDelegate(QStyledItemDelegate):
    """Custom bookmark tree renderer that paints the colored folder pills."""

    def paint(self, painter, option, index):  # noqa: ANN001
        data = index.data(Qt.ItemDataRole.UserRole) or {}
        is_folder = data.get("type") == "folder"

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(14, 6, -14, -6)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        if is_folder:
            style = index.data(Qt.ItemDataRole.UserRole + 1) or {}
            start = QColor(style.get("start", "#4556D8"))
            end = QColor(style.get("end", "#243B91"))
            border = QColor(style.get("border", "#8AA7FF"))
            start = start.darker(112)
            end = end.darker(110)

            if selected or hovered:
                start = start.lighter(108)
                end = end.lighter(104)
                border = border.lighter(112)

            pill_rect = rect.adjusted(1, 3, -1, -3)
            background = QLinearGradient(pill_rect.topLeft(), pill_rect.bottomRight())
            background.setColorAt(0.0, start.lighter(102))
            background.setColorAt(0.42, start)
            background.setColorAt(1.0, end)

            glow_rect = pill_rect.adjusted(-1, -1, 1, 1)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(border.red(), border.green(), border.blue(), 24))
            painter.drawRoundedRect(glow_rect, 14, 14)
            painter.setBrush(QBrush(background))
            painter.drawRoundedRect(pill_rect, 14, 14)
            gloss_rect = QRectF(
                pill_rect.left() + 2,
                pill_rect.top() + 2,
                pill_rect.width() - 4,
                pill_rect.height() * 0.46,
            )
            gloss = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
            gloss.setColorAt(0.0, QColor(255, 255, 255, 72))
            gloss.setColorAt(0.55, QColor(255, 255, 255, 16))
            gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(gloss))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(gloss_rect, 12, 12)
            painter.setPen(QPen(QColor(255, 255, 255, 26), 1.0))
            painter.drawRoundedRect(pill_rect.adjusted(1, 1, -1, -1), 13, 13)
            painter.setPen(QPen(border, 1.2))
            painter.drawRoundedRect(pill_rect, 14, 14)

            text_rect = pill_rect.adjusted(18, 0, -18, 0)
            font = option.font
            font.setPointSize(17)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor("#F7FAFF"))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignCenter,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )
        else:
            text_rect = rect.adjusted(18, 0, -10, 0)
            if hovered or selected:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, 18 if hovered else 26))
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)
            font = option.font
            font.setPointSize(12)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            painter.setPen(QColor("#C8D4FF"))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )

        painter.restore()

    def sizeHint(self, option, index):  # noqa: ANN001
        data = index.data(Qt.ItemDataRole.UserRole) or {}
        return QSize(
            option.rect.width(),
            72 if data.get("type") == "folder" else 34,
        )

    def _draw_folder_icon(self, painter: QPainter, rect, icon_color: QColor):
        painter.save()

        tab_path = QPainterPath()
        tab_path.addRoundedRect(rect.adjusted(3, 1, -18, -16), 5, 5)
        body_path = QPainterPath()
        body_path.addRoundedRect(rect.adjusted(1, 12, -2, -1), 8, 8)

        top_gradient = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
        top_gradient.setColorAt(0.0, icon_color.lighter(135))
        top_gradient.setColorAt(1.0, icon_color)

        body_gradient = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        body_gradient.setColorAt(0.0, icon_color.lighter(120))
        body_gradient.setColorAt(1.0, icon_color.darker(118))

        painter.setPen(QPen(QColor(255, 255, 255, 90), 1.0))
        painter.fillPath(tab_path, QBrush(top_gradient))
        painter.drawPath(tab_path)

        painter.fillPath(body_path, QBrush(body_gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1.15))
        painter.drawPath(body_path)

        painter.restore()


class NeonURLItemDelegate(QStyledItemDelegate):
    """Paints the URL rows as inset neon capsules with status dots."""

    STATE_COLORS = {
        "ready": QColor("#9BE98D"),
        "opening": QColor("#F8D66A"),
        "opened": QColor("#7EE7A8"),
        "failed": QColor("#FF7E8A"),
    }

    def paint(self, painter, option, index):  # noqa: ANN001
        if index.column() == 0:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cell_rect = option.rect.adjusted(4, 6, -4, -6)
        capsule_rect = (
            cell_rect.adjusted(0, 0, 10, 0)
            if index.column() == 1
            else cell_rect.adjusted(-10, 0, 0, 0)
        )

        base = QLinearGradient(capsule_rect.topLeft(), capsule_rect.bottomLeft())
        base.setColorAt(0.0, QColor("#141B40"))
        base.setColorAt(0.50, QColor("#0B112F"))
        base.setColorAt(1.0, QColor("#090D21"))

        border_color = QColor("#315BCE")
        if option.state & QStyle.StateFlag.State_Selected:
            border_color = QColor("#55D8FF")
        elif option.state & QStyle.StateFlag.State_MouseOver:
            border_color = QColor("#8D71FF")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(88, 122, 255, 22))
        painter.drawRoundedRect(capsule_rect.adjusted(0, 0, 0, 1), 13, 13)
        painter.setBrush(QBrush(base))
        painter.drawRoundedRect(capsule_rect, 13, 13)
        gloss_rect = QRectF(
            capsule_rect.left() + 2,
            capsule_rect.top() + 2,
            capsule_rect.width() - 4,
            capsule_rect.height() * 0.46,
        )
        gloss = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
        gloss.setColorAt(0.0, QColor(255, 255, 255, 66))
        gloss.setColorAt(0.42, QColor(255, 255, 255, 16))
        gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gloss))
        painter.drawRoundedRect(gloss_rect, 12, 12)
        spectrum = QLinearGradient(
            capsule_rect.left(),
            capsule_rect.center().y(),
            capsule_rect.right(),
            capsule_rect.center().y(),
        )
        spectrum.setColorAt(0.0, QColor(255, 255, 255, 0))
        spectrum.setColorAt(0.22, QColor(43, 230, 255, 24))
        spectrum.setColorAt(0.52, QColor(244, 69, 168, 26))
        spectrum.setColorAt(0.78, QColor(130, 83, 255, 18))
        spectrum.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(spectrum))
        painter.drawRoundedRect(capsule_rect.adjusted(6, 8, -6, -8), 10, 10)
        bloom = QRadialGradient(
            capsule_rect.center().x(),
            capsule_rect.center().y(),
            capsule_rect.width() * 0.26,
        )
        bloom.setColorAt(0.0, QColor(115, 152, 255, 24))
        bloom.setColorAt(1.0, QColor(115, 152, 255, 0))
        painter.setBrush(QBrush(bloom))
        painter.drawRoundedRect(capsule_rect, 13, 13)
        painter.setPen(QPen(border_color, 1.1))
        painter.drawRoundedRect(capsule_rect, 13, 13)
        painter.setPen(QPen(QColor(255, 255, 255, 24), 1.0))
        painter.drawLine(
            capsule_rect.left() + 14,
            capsule_rect.top() + 2,
            capsule_rect.right() - 14,
            capsule_rect.top() + 2,
        )

        if index.column() == 1:
            font = option.font
            font.setPointSize(15)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor("#F8FAFF"))
            painter.drawText(
                capsule_rect.adjusted(24, 0, -14, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )
        else:
            status_state = index.data(Qt.ItemDataRole.UserRole) or "ready"
            status_label = str(index.data(Qt.ItemDataRole.DisplayRole))
            status_color = self.STATE_COLORS.get(status_state, QColor("#9BE98D"))

            font = option.font
            font.setPointSize(13)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            text_width = painter.fontMetrics().horizontalAdvance(status_label)
            group_width = 14 + 10 + text_width
            group_left = capsule_rect.left() + max(
                18,
                int((capsule_rect.width() - group_width) / 2),
            )

            glow_center_x = group_left + 7
            glow_center_y = capsule_rect.center().y()
            painter.setBrush(QColor(status_color.red(), status_color.green(), status_color.blue(), 68))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(glow_center_x - 7, glow_center_y - 7, 14, 14)
            painter.setBrush(status_color)
            painter.drawEllipse(glow_center_x - 4, glow_center_y - 4, 8, 8)

            painter.setPen(QColor("#F4F8FF"))
            painter.drawText(
                capsule_rect.adjusted(group_left + 18 - capsule_rect.left(), 0, -10, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                status_label,
            )

        painter.restore()

    def sizeHint(self, option, index):  # noqa: ANN001
        if index.column() == 0:
            return QSize(0, 52)
        return QSize(option.rect.width(), 52)


class URLTableWidget(QTableWidget):
    """A custom table widget for displaying URLs with numbering and status tracking."""

    url_activated = Signal(int, str)
    urls_changed = Signal(list)

    STATUS_LABELS = {
        "ready": "Ready",
        "opening": "Opening",
        "opened": "Opened",
        "failed": "Failed",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url_processor = URLProcessor()
        self.href_pattern = re.compile(
            r'href=["\'](https?://[^"\']+)["\']', re.IGNORECASE
        )
        self.url_counter = 0
        self._suspend_url_events = False

        # Setup table structure
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["#", "URL", "Status"])

        # Configure table appearance and behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)
        self.setItemDelegate(NeonURLItemDelegate(self))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Number column
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # URL column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Status column
        self.setColumnWidth(0, 0)  # Hide number column
        self.setColumnWidth(2, 168)  # Status column width
        self.setColumnHidden(0, True)

        # Enable drag and drop
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        # Enable text cursor (blinking caret) for better UX
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.AllEditTriggers
        )  # Enable editing to show cursor
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.itemChanged.connect(self._on_item_changed)
        self.itemDoubleClicked.connect(self._activate_item_url)

    def add_urls(self, urls: list[str]):
        """Add URLs to the table with automatic numbering."""
        if not urls:
            return
        self._suspend_url_events = True
        for url in urls:
            self.url_counter += 1
            row = self.rowCount()
            self.insertRow(row)
            self.setRowHeight(row, 52)

            # Number column
            number_item = QTableWidgetItem(str(self.url_counter))
            number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            number_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Read-only
            self.setItem(row, 0, number_item)

            # URL column - make editable to show cursor
            url_item = QTableWidgetItem(url)
            url_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            self.setItem(row, 1, url_item)

            # Status column
            status_item = QTableWidgetItem()
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Read-only
            self.setItem(row, 2, status_item)
            self.set_status_state(row, "ready")
        self._suspend_url_events = False
        self._emit_urls_changed()

    def update_status(self, row: int, success: bool):
        """Update the status of a URL row."""
        self.set_status_state(row, "opened" if success else "failed")

    def set_status_state(self, row: int, state: str):
        """Set the visual status for a row."""
        if 0 <= row < self.rowCount():
            status_item = self.item(row, 2)
            if status_item:
                status_item.setText(self.STATUS_LABELS.get(state, "Ready"))
                status_item.setData(Qt.ItemDataRole.UserRole, state)

    def get_all_urls(self) -> list[str]:
        """Get all URLs from the table."""
        urls = []
        for row in range(self.rowCount()):
            url_item = self.item(row, 1)
            if url_item:
                urls.append(url_item.text())
        return urls

    def clear_table(self):
        """Clear all URLs and reset counter."""
        self._suspend_url_events = True
        self.setRowCount(0)
        self.url_counter = 0
        self._suspend_url_events = False
        self._emit_urls_changed()

    def replace_urls(self, urls: list[str]):
        """Replace the table contents with a fresh URL list."""
        self._suspend_url_events = True
        self.setRowCount(0)
        self.url_counter = 0
        for url in urls:
            self.url_counter += 1
            row = self.rowCount()
            self.insertRow(row)
            self.setRowHeight(row, 52)

            number_item = QTableWidgetItem(str(self.url_counter))
            number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            number_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.setItem(row, 0, number_item)

            url_item = QTableWidgetItem(url)
            url_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
            self.setItem(row, 1, url_item)

            status_item = QTableWidgetItem()
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.setItem(row, 2, status_item)
            self.set_status_state(row, "ready")
        self._suspend_url_events = False
        self._emit_urls_changed()

    def dragEnterEvent(self, event):  # noqa: N802 - Qt override
        """Accept drag events with URLs or text."""
        if (
            event.mimeData().hasUrls()
            or event.mimeData().hasText()
            or event.mimeData().hasHtml()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802 - Qt override
        """Handle dropped content."""
        mime_data = event.mimeData()
        self._process_mime_data(mime_data)
        event.acceptProposedAction()

    def keyPressEvent(self, event):  # noqa: N802 - Qt override
        """Handle keyboard events for pasting."""
        paste_modifiers = (
            Qt.KeyboardModifier.ControlModifier,
            Qt.KeyboardModifier.MetaModifier,
        )
        if (
            event.key() == Qt.Key.Key_V
            and event.modifiers() in paste_modifiers
        ):
            # Handle Ctrl+V paste
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            self._process_mime_data(mime_data)
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._activate_current_row()
        else:
            super().keyPressEvent(event)

    def _process_mime_data(self, mime_data: QMimeData):
        """Process mime data to extract URLs."""
        urls_to_add = []

        # Priority 1: Direct URLs
        if mime_data.hasUrls():
            urls_to_add.extend([url.toString() for url in mime_data.urls()])

        # Priority 2: HTML content with links
        elif mime_data.hasHtml():
            html = mime_data.html()
            found_urls = self.href_pattern.findall(html)
            if found_urls:
                urls_to_add.extend(found_urls)
            else:
                # Extract from plain text if no HTML links
                text = mime_data.text()
                urls_to_add.extend(self.url_processor.extract_urls(text))

        # Priority 3: Plain text
        elif mime_data.hasText():
            text = mime_data.text()
            urls_to_add.extend(self.url_processor.extract_urls(text))

        # Add extracted URLs to table
        if urls_to_add:
            self.add_urls(urls_to_add)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        """Handle mouse press events to show cursor in URL cells."""
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if item and item.column() == 1:  # URL column
            self.editItem(item)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        """Show a pointing cursor over activatable URL rows."""
        item = self.itemAt(event.pos())
        if item and item.column() in (1, 2):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        """Restore the regular cursor when the pointer leaves the table."""
        self.unsetCursor()
        super().leaveEvent(event)

    def _activate_current_row(self):
        current_row = self.currentRow()
        if current_row < 0:
            return
        url_item = self.item(current_row, 1)
        if url_item and url_item.text().strip():
            self.url_activated.emit(current_row, url_item.text().strip())

    def _activate_item_url(self, item: QTableWidgetItem):
        if item.column() not in (1, 2):
            return
        url_item = self.item(item.row(), 1)
        if url_item and url_item.text().strip():
            self.url_activated.emit(item.row(), url_item.text().strip())

    def _normalize_url_text(self, text: str) -> str:
        normalized = self.url_processor._normalize_url(text.strip())
        return normalized or text.strip()

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._suspend_url_events or item.column() != 1:
            return
        normalized = self._normalize_url_text(item.text())
        if normalized != item.text():
            self._suspend_url_events = True
            item.setText(normalized)
            self._suspend_url_events = False
        self._emit_urls_changed()

    def _emit_urls_changed(self):
        if self._suspend_url_events:
            return
        self.urls_changed.emit(self.get_all_urls())


class NeonButton(QPushButton):
    """A custom button with a neon glow effect on hover."""

    def __init__(
        self, text: str = "", color: str = "#00f5ff"
    ):  # Default to a neon blue
        super().__init__(text)
        self.color = color
        self._setup_shadow_effect()
        self.update_style(color)  # Use update_style for initial setup
        self._setup_animations()

    def _setup_shadow_effect(self):
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)  # Offset 0,0 for central glow
        self.setGraphicsEffect(self.shadow)

    def update_style(self, new_color: str):
        """Updates the button's color and stylesheet."""
        self.color = new_color
        self.shadow.setColor(QColor(self.color))

        # Create a darker version for the gradient stop and pressed state
        darker_color = QColor(self.color).darker(150).name()  # Darker by 50%

        self.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.color}, stop:1 {darker_color});
                color: #d0d0d0;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
                text-shadow: -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
            }}
            QPushButton:hover {{ /* Glow effect handled by QGraphicsDropShadowEffect */ }}
            QPushButton:pressed {{ background: {darker_color}; }}
            QPushButton:disabled {{ background: rgba(100,100,100,0.5); color: rgba(255,255,255,0.5); }}
        """
        )

    def _setup_animations(self):
        self.glow_in_anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_in_anim.setDuration(Config.ANIMATION_DURATION)
        self.glow_in_anim.setEndValue(Config.GLOW_RADIUS)
        self.glow_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.glow_out_anim = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_out_anim.setDuration(Config.ANIMATION_DURATION)
        self.glow_out_anim.setEndValue(0)
        self.glow_out_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):  # noqa: N802 - Qt override
        self.glow_out_anim.stop()
        self.glow_in_anim.setStartValue(self.shadow.blurRadius())
        self.glow_in_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        self.glow_in_anim.stop()
        self.glow_out_anim.setStartValue(self.shadow.blurRadius())
        self.glow_out_anim.start()
        super().leaveEvent(event)


class GlassButton(QPushButton):
    """A modern glass-styled button with animated glow effects for the Glass Noir theme."""

    def __init__(self, text: str = "", variant: str = "primary"):
        """Initialize GlassButton.

        Args:
            text: Button text
            variant: 'primary', 'secondary', 'tertiary', 'quaternary', or 'danger'
        """
        super().__init__(text)
        self.variant = variant
        self._variant_palette: dict[str, str] = {}
        self._setup_glow_effect()
        self._apply_variant_style()
        self._setup_animations()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setMinimumHeight(50)
        if text != "+":
            self.setMinimumWidth(176)

    def _setup_glow_effect(self):
        """Setup the drop shadow effect for glow."""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

    def _get_glow_color(self) -> str:
        """Get the glow color based on variant."""
        colors = {
            "primary": "#67AFFF",
            "secondary": "#FF6CAA",
            "tertiary": "#6EEDC3",
            "quaternary": "#C078FF",
            "danger": "#FF6A79",
        }
        return colors.get(self.variant, "#3b82f6")

    def _disabled_tint(self, color_hex: str, lift: int = 112, alpha: int = 234) -> QColor:
        """Keep disabled controls colorful instead of flattening them to gray."""
        color = QColor(color_hex).lighter(lift)
        color.setAlpha(alpha)
        return color

    def _setup_animations(self):
        """Setup hover glow animations."""
        glow_color = self._get_glow_color()
        self.shadow.setColor(QColor(glow_color))

        self.glow_in = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_in.setDuration(200)
        self.glow_in.setEndValue(20)
        self.glow_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.glow_out = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_out.setDuration(300)
        self.glow_out.setEndValue(0)
        self.glow_out.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):  # noqa: N802 - Qt override
        """Animate glow in on hover."""
        self.glow_out.stop()
        self.glow_in.setStartValue(self.shadow.blurRadius())
        self.glow_in.start()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        """Animate glow out on leave."""
        self.glow_in.stop()
        self.glow_out.setStartValue(self.shadow.blurRadius())
        self.glow_out.start()
        super().leaveEvent(event)

    def _apply_variant_style(self):
        """Store the neon palette used by the custom glossy button paint."""
        palettes = {
            "primary": {
                "start": "#2D66E8",
                "end": "#183FAD",
                "hover_start": "#59A0FF",
                "hover_end": "#2E67D9",
                "border": "#A7CEFF",
                "gloss": "#F3F8FF",
                "flare": "#6BC6FF",
                "text": "#FFFFFF",
            },
            "secondary": {
                "start": "#DE467D",
                "end": "#911F57",
                "hover_start": "#FF73A8",
                "hover_end": "#C03272",
                "border": "#FFB8D2",
                "gloss": "#FFF1F7",
                "flare": "#FF74B8",
                "text": "#FFFFFF",
            },
            "tertiary": {
                "start": "#3CB68D",
                "end": "#1C6B5B",
                "hover_start": "#63DAB0",
                "hover_end": "#2B8B75",
                "border": "#B8F7E3",
                "gloss": "#F2FFF9",
                "flare": "#76FFD3",
                "text": "#FFFFFF",
            },
            "quaternary": {
                "start": "#8346E4",
                "end": "#5627A7",
                "hover_start": "#B173FF",
                "hover_end": "#733DE0",
                "border": "#DFC0FF",
                "gloss": "#FBF3FF",
                "flare": "#D48BFF",
                "text": "#FFFFFF",
            },
            "danger": {
                "start": "#C43753",
                "end": "#7C1836",
                "hover_start": "#F05F7A",
                "hover_end": "#A7264C",
                "border": "#FFB0C3",
                "gloss": "#FFF0F4",
                "flare": "#FF7896",
                "text": "#FFFFFF",
            },
        }
        self._variant_palette = palettes.get(self.variant, palettes["primary"])
        self.update()

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        pressed = self.isDown()
        hovered = self.underMouse()
        palette = self._variant_palette
        enabled = self.isEnabled()
        start = QColor(
            palette["hover_start"] if hovered or self.isChecked() else palette["start"]
        )
        end = QColor(
            palette["hover_end"] if hovered or self.isChecked() else palette["end"]
        )
        if pressed:
            start = start.darker(120)
            end = end.darker(120)
        if not enabled:
            start = self._disabled_tint(palette["start"], lift=114, alpha=236)
            end = self._disabled_tint(palette["end"], lift=108, alpha=230)

        fill = QLinearGradient(rect.topLeft(), rect.bottomRight())
        fill.setColorAt(0.0, start)
        fill.setColorAt(1.0, end)

        painter.setPen(Qt.PenStyle.NoPen)
        flare_alpha = 48 if enabled else 30
        painter.setBrush(QColor(QColor(palette["flare"]).red(), QColor(palette["flare"]).green(), QColor(palette["flare"]).blue(), flare_alpha))
        painter.drawRoundedRect(rect.adjusted(-1, -1, 1, 1), 17, 17)
        painter.setBrush(QBrush(fill))
        painter.drawRoundedRect(rect, 17, 17)

        flare = QRadialGradient(
            rect.left() + rect.width() * 0.24,
            rect.center().y(),
            rect.width() * 0.38,
        )
        flare_color = QColor(palette["flare"])
        flare_color.setAlpha(84 if enabled and (hovered or self.isChecked()) else 58 if enabled else 30)
        flare.setColorAt(0.0, flare_color)
        flare.setColorAt(1.0, QColor(palette["flare"]).darker(150))
        edge = QColor(palette["flare"])
        edge.setAlpha(0)
        flare.setColorAt(1.0, edge)
        painter.setBrush(QBrush(flare))
        painter.drawRoundedRect(rect, 17, 17)
        sheen = QLinearGradient(rect.left(), rect.center().y(), rect.right(), rect.center().y())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
        sheen.setColorAt(0.18, QColor(QColor(palette["flare"]).red(), QColor(palette["flare"]).green(), QColor(palette["flare"]).blue(), 28 if enabled else 18))
        sheen.setColorAt(0.48, QColor(255, 255, 255, 24 if enabled else 14))
        sheen.setColorAt(0.82, QColor(QColor(palette["border"]).red(), QColor(palette["border"]).green(), QColor(palette["border"]).blue(), 30 if enabled else 20))
        sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(sheen))
        painter.drawRoundedRect(rect.adjusted(10, 10, -10, -10), 11, 11)

        gloss_rect = QRectF(rect.left() + 2, rect.top() + 2, rect.width() - 4, rect.height() * 0.48)
        gloss = QLinearGradient(gloss_rect.topLeft(), gloss_rect.bottomLeft())
        gloss_top_alpha = 150 if enabled else 76
        gloss_mid_alpha = 42 if enabled else 20
        gloss.setColorAt(0.0, QColor(QColor(palette["gloss"]).red(), QColor(palette["gloss"]).green(), QColor(palette["gloss"]).blue(), gloss_top_alpha))
        gloss.setColorAt(0.35, QColor(QColor(palette["gloss"]).red(), QColor(palette["gloss"]).green(), QColor(palette["gloss"]).blue(), gloss_mid_alpha))
        gloss.setColorAt(1.0, QColor(QColor(palette["gloss"]).red(), QColor(palette["gloss"]).green(), QColor(palette["gloss"]).blue(), 0))
        painter.setBrush(QBrush(gloss))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(gloss_rect, 14, 14)

        border_color = QColor(palette["border"]) if enabled else QColor(QColor(palette["border"]).red(), QColor(palette["border"]).green(), QColor(palette["border"]).blue(), 148)
        painter.setPen(QPen(border_color, 1.45))
        painter.drawRoundedRect(rect, 17, 17)
        inner_border = QColor(255, 255, 255, 56 if enabled else 34)
        painter.setPen(QPen(inner_border, 1.0))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 16, 16)

        font = self.font()
        font.setPointSize(17)
        font.setWeight(QFont.Weight.ExtraBold)
        painter.setFont(font)
        painter.setPen(QColor(palette["text"]) if enabled else QColor(244, 247, 255, 208))
        if pressed:
            text_rect = rect.adjusted(0, 1, 0, 1)
        else:
            text_rect = rect
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())

        if enabled and self.hasFocus():
            painter.setPen(QPen(QColor(255, 255, 255, 150), 1.1))
            painter.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 13, 13)


class OutlinedLabel(QLabel):
    """A QLabel with outlined text for better visibility."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.outline_color = QColor(0, 0, 0)  # Black outline
        self.outline_width = 2

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override        """Custom paint event to draw outlined text."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Get the text and font
        text = self.text()
        font = self.font()
        painter.setFont(font)

        # Create a path for the text
        path = QPainterPath()
        path.addText(0, font.pointSize(), font, text)

        # Get the bounding rect and center the text
        rect = self.rect()
        text_rect = painter.fontMetrics().boundingRect(text)

        # Calculate position based on alignment
        if self.alignment() & Qt.AlignmentFlag.AlignHCenter:
            x = (rect.width() - text_rect.width()) / 2
        elif self.alignment() & Qt.AlignmentFlag.AlignRight:
            x = rect.width() - text_rect.width()
        else:
            x = 0

        if self.alignment() & Qt.AlignmentFlag.AlignVCenter:
            y = (rect.height() + text_rect.height()) / 2
        elif self.alignment() & Qt.AlignmentFlag.AlignBottom:
            y = rect.height()
        else:
            y = text_rect.height()

        # Translate to the correct position
        painter.translate(x, y)

        # Draw the outline
        pen = QPen(
            self.outline_color,
            self.outline_width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.strokePath(path, pen)

        # Draw the fill
        painter.fillPath(path, self.palette().color(self.foregroundRole()))


class GlassPanel(QWidget):
    """A semi-transparent panel with a colored border, used as a tab background."""

    def __init__(self):  # Removed default border_color, will be set by update_style
        super().__init__()
        self.setObjectName("GlassPanel")
        # Initial style, will be updated by _apply_theme
        self.setStyleSheet(
            """
            #GlassPanel {
                background-color: transparent; /* Allow main window background to show */
                border: 2px solid #444; /* Default subtle border */
                border-radius: 12px;
            }
        """
        )

    def update_style(self, color: str):
        """Updates the panel's border color."""
        self.setStyleSheet(
            f"""
            #GlassPanel {{
                background-color: transparent;
                border: 2px solid {color};
                border-radius: 12px;
            }}
        """
        )
