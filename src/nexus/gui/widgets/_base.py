"""Custom UI widgets for the Nexus application with premium Dark and Light theme support."""

from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from typing import cast

from PySide6.QtCore import (
    QEasingCurve,
    QMimeData,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
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
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexus.core.config import Config
from nexus.gui.theme import get_theme_manager
from nexus.utils.url_processor import URLProcessor
from razorcore.threading import AsyncTaskWorker


class AsyncWorker(AsyncTaskWorker):
    """Nexus async worker on razorcore.AsyncTaskWorker with result_ready alias."""

    result_ready = Signal(object)

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__(coro_func, *args, **kwargs)
        # Preserve the historical Nexus signal name used by MainWindow.
        self.finished.connect(self.result_ready.emit)


@dataclass
class ShootingStar:
    x: float
    y: float
    vx: float
    vy: float
    length: float
    thickness: float
    opacity: float
    life: int
    max_life: int
    tail_color: tuple[int, int, int]


class CosmicFrame(QWidget):
    """Rounded floating glass shell with dynamic shooting stars and iOS 27 glossy refraction."""

    # Deterministic starfield: (x%, y%, radius, alpha)
    _STARS = [
        (0.08, 0.12, 1.0, 150),
        (0.16, 0.68, 1.4, 110),
        (0.22, 0.30, 0.8, 90),
        (0.29, 0.85, 1.1, 130),
        (0.34, 0.15, 1.6, 170),
        (0.41, 0.52, 0.9, 100),
        (0.47, 0.78, 1.2, 120),
        (0.53, 0.22, 1.0, 140),
        (0.58, 0.62, 1.5, 100),
        (0.64, 0.40, 0.8, 90),
        (0.71, 0.90, 1.3, 150),
        (0.76, 0.18, 1.0, 120),
        (0.82, 0.55, 1.7, 160),
        (0.88, 0.34, 0.9, 100),
        (0.93, 0.74, 1.2, 130),
        (0.12, 0.44, 0.7, 80),
        (0.38, 0.94, 1.0, 110),
        (0.67, 0.08, 1.1, 140),
        (0.86, 0.92, 0.8, 90),
        (0.05, 0.86, 1.3, 120),
        (0.19, 0.56, 2.0, 185),
        (0.61, 0.28, 2.2, 200),
        (0.44, 0.71, 1.8, 175),
    ]

    _GLINTS = [
        (0.08, 0.10, 5),
        (0.92, 0.12, 5),
        (0.06, 0.90, 4),
        (0.94, 0.88, 4),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._meteors: list[ShootingStar] = []
        self._tick: int = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(33)  # ~30 FPS
        self._anim_timer.timeout.connect(self._advance_animation)
        self._anim_timer.start()
        # Seed 5 shooting stars with staggered start
        for i in range(5):
            self._meteors.append(self._create_meteor(1000, 700, stagger=i * 18))
        get_theme_manager().theme_changed.connect(lambda _: self.update())

    def _create_meteor(self, w: int, h: int, stagger: int = 0) -> ShootingStar:
        speed = random.uniform(8.0, 14.0)
        angle = math.radians(random.uniform(28.0, 42.0))
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        length = random.uniform(70.0, 150.0)
        thickness = random.uniform(1.4, 2.5)
        max_life = random.randint(45, 95)
        if random.random() < 0.70:
            x = random.uniform(-40.0, max(200.0, w * 0.75))
            y = random.uniform(-40.0, 20.0)
        else:
            x = random.uniform(-60.0, -10.0)
            y = random.uniform(0.0, max(100.0, h * 0.45))

        tm = get_theme_manager()
        if tm.is_dark:
            colors = [
                (56, 189, 248),  # Electric Cyan
                (147, 197, 253),  # Sky Light Blue
                (192, 132, 252),  # Purple
                (255, 255, 255),  # Pure White
                (45, 212, 191),  # Teal
            ]
        else:
            # Light Blue Mode: Sparkling celestial sky meteors
            colors = [
                (2, 132, 199),  # Azure Blue
                (14, 165, 233),  # Vivid Sky Blue
                (56, 189, 248),  # Bright Cyan
                (255, 255, 255),  # Brilliant White
                (99, 102, 241),  # Indigo
            ]
        color = random.choice(colors)
        return ShootingStar(
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            length=length,
            thickness=thickness,
            opacity=0.0,
            life=-stagger,
            max_life=max_life,
            tail_color=color,
        )

    def _advance_animation(self) -> None:
        self._tick += 1
        w = max(400, self.width())
        h = max(300, self.height())
        alive: list[ShootingStar] = []
        for m in self._meteors:
            m.life += 1
            if m.life <= 0:
                alive.append(m)
                continue
            m.x += m.vx
            m.y += m.vy
            progress = m.life / max(1, m.max_life)
            if progress < 0.15:
                m.opacity = progress / 0.15
            elif progress > 0.60:
                m.opacity = max(0.0, (1.0 - progress) / 0.40)
            else:
                m.opacity = 1.0

            if m.life < m.max_life and m.x < w + 150 and m.y < h + 150:
                alive.append(m)
            else:
                alive.append(self._create_meteor(w, h))

        self._meteors = alive
        self.update()

    def _draw_glint(
        self, painter: QPainter, rect, sx: float, sy: float, size: float, color: QColor
    ) -> None:
        cx = rect.left() + rect.width() * sx
        cy = rect.top() + rect.height() * sy
        half = size / 2
        painter.setPen(QPen(color, 1.2))
        painter.drawLine(int(cx - half), int(cy), int(cx + half), int(cy))
        painter.drawLine(int(cx), int(cy - half), int(cx), int(cy + half))

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        tm = get_theme_manager()
        tokens = tm.tokens
        rect = self.rect().adjusted(1, 1, -2, -2)
        rounded_rect = QPainterPath()
        rounded_rect.addRoundedRect(rect, 18, 18)

        # Base Gradient
        base = QLinearGradient(rect.topLeft(), rect.bottomRight())
        base.setColorAt(0.0, QColor(tokens.frame_bg_start))
        base.setColorAt(0.45, QColor(tokens.frame_bg_mid))
        base.setColorAt(1.0, QColor(tokens.frame_bg_end))
        painter.fillPath(rounded_rect, QBrush(base))

        painter.setClipPath(rounded_rect)

        if tm.is_dark:
            # Dark: Deep galactic swirl + purple nebula wash
            swirl = QLinearGradient(rect.topRight(), rect.center())
            swirl.setColorAt(0.0, QColor(50, 90, 200, 48))
            swirl.setColorAt(1.0, QColor(50, 90, 200, 0))
            painter.fillPath(rounded_rect, QBrush(swirl))

            nebula = QLinearGradient(
                rect.left(),
                rect.top() + rect.height() * 0.35,
                rect.right(),
                rect.top() + rect.height() * 0.65,
            )
            nebula.setColorAt(0.0, QColor(90, 60, 150, 0))
            nebula.setColorAt(0.35, QColor(120, 70, 210, 52))
            nebula.setColorAt(0.55, QColor(60, 110, 230, 44))
            nebula.setColorAt(0.75, QColor(110, 70, 190, 46))
            nebula.setColorAt(1.0, QColor(90, 60, 150, 0))
            painter.fillPath(rounded_rect, QBrush(nebula))
        else:
            # Light Blue: Luminous sky-blue and cyan nebula wash
            swirl = QLinearGradient(rect.topRight(), rect.center())
            swirl.setColorAt(0.0, QColor(56, 189, 248, 60))
            swirl.setColorAt(1.0, QColor(14, 165, 233, 0))
            painter.fillPath(rounded_rect, QBrush(swirl))

            nebula = QLinearGradient(
                rect.left(),
                rect.top() + rect.height() * 0.30,
                rect.right(),
                rect.top() + rect.height() * 0.70,
            )
            nebula.setColorAt(0.0, QColor(186, 230, 253, 0))
            nebula.setColorAt(0.40, QColor(125, 211, 252, 70))
            nebula.setColorAt(0.70, QColor(56, 189, 248, 60))
            nebula.setColorAt(1.0, QColor(186, 230, 253, 0))
            painter.fillPath(rounded_rect, QBrush(nebula))

        # Twinkling Starfield
        painter.setPen(Qt.PenStyle.NoPen)
        for idx, (sx, sy, radius, alpha) in enumerate(self._STARS):
            twinkle = 0.65 + 0.35 * math.sin(self._tick * 0.07 + idx * 1.3)
            star_alpha = int(alpha * twinkle)
            star_color = (
                QColor(226, 234, 248, star_alpha)
                if tm.is_dark
                else QColor(2, 132, 199, int(star_alpha * 0.70))
            )
            painter.setBrush(star_color)
            painter.drawEllipse(
                QRectF(
                    rect.left() + rect.width() * sx,
                    rect.top() + rect.height() * sy,
                    radius * 2,
                    radius * 2,
                )
            )

        if tm.is_dark:
            for sx, sy, size in self._GLINTS:
                self._draw_glint(
                    painter, rect, sx, sy, size, QColor(236, 242, 252, 210)
                )
        else:
            for sx, sy, size in self._GLINTS:
                self._draw_glint(
                    painter, rect, sx, sy, size, QColor(255, 255, 255, 230)
                )

        # Dynamic Shooting Stars (Meteors)
        for m in self._meteors:
            if m.life <= 0 or m.opacity <= 0.01:
                continue
            head_x = rect.left() + m.x
            head_y = rect.top() + m.y
            angle = math.atan2(m.vy, m.vx)
            tail_x = head_x - math.cos(angle) * m.length
            tail_y = head_y - math.sin(angle) * m.length

            r, g, b = m.tail_color
            tail_grad = QLinearGradient(
                QPointF(head_x, head_y), QPointF(tail_x, tail_y)
            )
            tail_grad.setColorAt(0.0, QColor(255, 255, 255, int(250 * m.opacity)))
            tail_grad.setColorAt(0.18, QColor(r, g, b, int(210 * m.opacity)))
            tail_grad.setColorAt(0.55, QColor(r, g, b, int(80 * m.opacity)))
            tail_grad.setColorAt(1.0, QColor(r, g, b, 0))

            pen = QPen(QBrush(tail_grad), m.thickness)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(tail_x, tail_y), QPointF(head_x, head_y))

            spark_col = (
                QColor(255, 255, 255, int(255 * m.opacity))
                if tm.is_dark
                else QColor(240, 249, 255, int(255 * m.opacity))
            )
            painter.setBrush(spark_col)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                QPointF(head_x, head_y), m.thickness * 1.3, m.thickness * 1.3
            )

        # iOS 27 Liquid Glass Curved Specular Dome (across upper 28%)
        dome = QLinearGradient(
            rect.left(), rect.top(), rect.left(), rect.top() + rect.height() * 0.28
        )
        if tm.is_dark:
            dome.setColorAt(0.0, QColor(255, 255, 255, 80))
            dome.setColorAt(0.35, QColor(255, 255, 255, 22))
            dome.setColorAt(1.0, QColor(255, 255, 255, 0))
        else:
            dome.setColorAt(0.0, QColor(255, 255, 255, 180))
            dome.setColorAt(0.40, QColor(255, 255, 255, 60))
            dome.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.fillPath(rounded_rect, QBrush(dome))

        painter.setClipping(False)

        # Brushed metallic / crystalline outer border
        border = QLinearGradient(rect.topLeft(), rect.bottomRight())
        border.setColorAt(0.0, QColor(tokens.frame_border_start))
        border.setColorAt(0.25, QColor(tokens.frame_border_mid))
        border.setColorAt(0.5, QColor(tokens.frame_border_end))
        border.setColorAt(0.75, QColor(tokens.frame_border_mid))
        border.setColorAt(1.0, QColor(tokens.frame_border_start))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(border), 2.2))
        painter.drawRoundedRect(rect, 18, 18)

        # Machined inner depth line
        inner = rect.adjusted(3, 3, -3, -3)
        painter.setPen(QPen(QColor(tokens.frame_inner_border), 1.0))
        painter.drawRoundedRect(inner, 15, 15)

        super().paintEvent(event)


class MetallicLabel(QLabel):
    """Refined metallic label with gradient lettering that adapts to light and dark themes."""

    _DARK_VARIANTS = {
        "hero": {
            "size": 48,
            "weight": QFont.Weight.Bold,
            "spacing": 7.0,
            "top": "#FFFFFF",
            "mid": "#D4E2F6",
            "bottom": "#9AB0D2",
            "shadow": QColor(0, 0, 0, 130),
        },
        "body": {
            "size": 15,
            "weight": QFont.Weight.DemiBold,
            "spacing": 0.4,
            "top": "#F8FAFC",
            "mid": "#D0DAEA",
            "bottom": "#A8B8D0",
            "shadow": QColor(0, 0, 0, 80),
        },
        "section": {
            "size": 20,
            "weight": QFont.Weight.DemiBold,
            "spacing": 0.3,
            "top": "#FFFFFF",
            "mid": "#D8E4F4",
            "bottom": "#A8BCD8",
            "shadow": QColor(0, 0, 0, 90),
        },
        "accent": {
            "size": 16,
            "weight": QFont.Weight.DemiBold,
            "spacing": 0.3,
            "top": "#93C5FD",
            "mid": "#60A5FA",
            "bottom": "#3B82F6",
            "shadow": QColor(0, 0, 0, 90),
        },
        "dim": {
            "size": 15,
            "weight": QFont.Weight.Normal,
            "spacing": 0.2,
            "top": "#CBD5E1",
            "mid": "#94A3B8",
            "bottom": "#64748B",
            "shadow": QColor(0, 0, 0, 70),
        },
    }

    _LIGHT_VARIANTS = {
        "hero": {
            "size": 48,
            "weight": QFont.Weight.Bold,
            "spacing": 7.0,
            "top": "#032B56",
            "mid": "#0284C7",
            "bottom": "#0369A1",
            "shadow": QColor(255, 255, 255, 220),
        },
        "body": {
            "size": 15,
            "weight": QFont.Weight.DemiBold,
            "spacing": 0.4,
            "top": "#032B56",
            "mid": "#0C4A6E",
            "bottom": "#1E3A8A",
            "shadow": QColor(255, 255, 255, 180),
        },
        "section": {
            "size": 20,
            "weight": QFont.Weight.DemiBold,
            "spacing": 0.3,
            "top": "#032B56",
            "mid": "#0284C7",
            "bottom": "#0369A1",
            "shadow": QColor(255, 255, 255, 190),
        },
        "accent": {
            "size": 16,
            "weight": QFont.Weight.DemiBold,
            "spacing": 0.3,
            "top": "#0284C7",
            "mid": "#0369A1",
            "bottom": "#075985",
            "shadow": QColor(255, 255, 255, 190),
        },
        "dim": {
            "size": 15,
            "weight": QFont.Weight.Normal,
            "spacing": 0.2,
            "top": "#1E5B8E",
            "mid": "#3B82F6",
            "bottom": "#0284C7",
            "shadow": QColor(255, 255, 255, 150),
        },
    }

    def __init__(self, text: str = "", variant: str = "body", parent=None):
        super().__init__(text, parent)
        self._variant = variant
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._apply_variant()
        get_theme_manager().theme_changed.connect(lambda _: self.update())

    def set_variant(self, variant: str) -> None:
        self._variant = variant
        self._apply_variant()
        self.update()

    def _apply_variant(self) -> None:
        table = (
            self._DARK_VARIANTS if get_theme_manager().is_dark else self._LIGHT_VARIANTS
        )
        spec = table.get(self._variant, table["body"])
        font = self.font()
        font.setFamily("Helvetica Neue")
        font.setPointSize(cast(int, spec["size"]))
        font.setWeight(cast(QFont.Weight, spec["weight"]))
        font.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing, cast(float, spec["spacing"])
        )
        self.setFont(font)

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        del event
        table = (
            self._DARK_VARIANTS if get_theme_manager().is_dark else self._LIGHT_VARIANTS
        )
        spec = table.get(self._variant, table["body"])
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        text = self.text()
        font = self.font()
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        text_height = metrics.height()

        if self.alignment() & Qt.AlignmentFlag.AlignHCenter:
            x = (self.width() - text_width) / 2
        elif self.alignment() & Qt.AlignmentFlag.AlignRight:
            x = self.width() - text_width
        else:
            x = 4.0

        if self.alignment() & Qt.AlignmentFlag.AlignVCenter:
            y = (self.height() + metrics.ascent() - metrics.descent()) / 2
        else:
            y = metrics.ascent() + 2

        path = QPainterPath()
        path.addText(x, y, font, text)

        shadow = spec["shadow"]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow)
        painter.translate(0, 1.2)
        painter.drawPath(path)
        painter.translate(0, -1.2)

        gradient = QLinearGradient(x, y - text_height, x, y + 4)
        gradient.setColorAt(0.0, QColor(spec["top"]))
        gradient.setColorAt(0.45, QColor(spec["mid"]))
        gradient.setColorAt(1.0, QColor(spec["bottom"]))
        painter.setBrush(QBrush(gradient))
        painter.drawPath(path)


class TrafficLightButton(QPushButton):
    """Mac-style traffic light control."""

    def __init__(self, tone: str, symbol: str, parent=None):
        super().__init__(parent)
        self._tone = QColor(tone)
        self._symbol = symbol
        self.setFixedSize(14, 14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        fill = QColor(self._tone)
        if self.underMouse():
            fill = fill.lighter(112)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawEllipse(rect)

        if self.underMouse():
            font = painter.font()
            font.setPointSize(7)
            font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QColor(40, 28, 28, 180))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._symbol)


class ThemeToggleButton(QPushButton):
    """Glossy iOS 27 glass capsule toggle button positioned in top right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip("Toggle Light (Sky Blue) / Dark (Cosmic) Mode")
        self.clicked.connect(self._toggle)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 1)
        self.setGraphicsEffect(self.shadow)
        get_theme_manager().theme_changed.connect(lambda _: self._on_theme_changed())
        self._on_theme_changed()

    def _on_theme_changed(self):
        tm = get_theme_manager()
        glow = QColor(56, 189, 248, 120) if tm.is_dark else QColor(2, 132, 199, 100)
        self.shadow.setColor(glow)
        self.update()

    def _toggle(self):
        get_theme_manager().toggle_theme()

    def enterEvent(self, event):  # noqa: N802 - Qt override
        self.shadow.setBlurRadius(12)
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        self.shadow.setBlurRadius(0)
        super().leaveEvent(event)

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        tm = get_theme_manager()
        is_dark = tm.is_dark
        under_mouse = self.underMouse()

        # 1. Capsule Base
        capsule_path = QPainterPath()
        capsule_path.addRoundedRect(rect, 12, 12)

        bg_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        if is_dark:
            bg_grad.setColorAt(0.0, QColor(18, 26, 44, 210 if under_mouse else 170))
            bg_grad.setColorAt(1.0, QColor(8, 12, 22, 230 if under_mouse else 190))
        else:
            bg_grad.setColorAt(0.0, QColor(255, 255, 255, 240 if under_mouse else 200))
            bg_grad.setColorAt(1.0, QColor(224, 242, 254, 240 if under_mouse else 200))

        painter.fillPath(capsule_path, QBrush(bg_grad))

        # 2. Top Specular Shine
        sheen = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        sheen.setColorAt(0.0, QColor(255, 255, 255, 140 if not is_dark else 70))
        sheen.setColorAt(0.48, QColor(255, 255, 255, 20 if not is_dark else 10))
        sheen.setColorAt(0.50, QColor(255, 255, 255, 0))
        painter.fillPath(capsule_path, QBrush(sheen))

        # 3. Outer Glossy Border
        border_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        if is_dark:
            border_grad.setColorAt(0.0, QColor(255, 255, 255, 140))
            border_grad.setColorAt(0.5, QColor(56, 189, 248, 120))
            border_grad.setColorAt(1.0, QColor(147, 197, 253, 60))
        else:
            border_grad.setColorAt(0.0, QColor(255, 255, 255, 240))
            border_grad.setColorAt(0.5, QColor(56, 189, 248, 160))
            border_grad.setColorAt(1.0, QColor(2, 132, 199, 120))

        painter.setPen(QPen(QBrush(border_grad), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 12, 12)

        # 4. Sliding Glowing Jewel Indicator
        thumb_w = 23.0
        thumb_h = 20.0
        thumb_y = rect.top() + (rect.height() - thumb_h) / 2.0
        thumb_x = rect.right() - thumb_w - 2.0 if is_dark else rect.left() + 2.0
        thumb_rect = QRectF(thumb_x, thumb_y, thumb_w, thumb_h)
        thumb_path = QPainterPath()
        thumb_path.addRoundedRect(thumb_rect, 10, 10)

        thumb_fill = QLinearGradient(thumb_rect.topLeft(), thumb_rect.bottomLeft())
        if is_dark:
            thumb_fill.setColorAt(0.0, QColor(96, 165, 250, 240))
            thumb_fill.setColorAt(1.0, QColor(37, 99, 235, 240))
        else:
            thumb_fill.setColorAt(0.0, QColor(253, 224, 71, 245))
            thumb_fill.setColorAt(1.0, QColor(245, 158, 11, 245))

        painter.fillPath(thumb_path, QBrush(thumb_fill))

        # Top shine on thumb
        thumb_sheen = QLinearGradient(thumb_rect.topLeft(), thumb_rect.bottomLeft())
        thumb_sheen.setColorAt(0.0, QColor(255, 255, 255, 180))
        thumb_sheen.setColorAt(0.5, QColor(255, 255, 255, 0))
        painter.fillPath(thumb_path, QBrush(thumb_sheen))

        # 5. Icons: ☀️ and 🌙
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        sun_rect = QRectF(rect.left() + 3, rect.top(), 22, rect.height())
        moon_rect = QRectF(rect.right() - 25, rect.top(), 22, rect.height())

        painter.setPen(
            QColor(15, 23, 42) if not is_dark else QColor(148, 163, 184, 160)
        )
        painter.drawText(sun_rect, Qt.AlignmentFlag.AlignCenter, "☀️")

        painter.setPen(QColor(255, 255, 255) if is_dark else QColor(71, 85, 105, 160))
        painter.drawText(moon_rect, Qt.AlignmentFlag.AlignCenter, "🌙")


class WindowTitleBar(QWidget):
    """Custom title bar for the frameless window shell with traffic lights and theme toggle at top right."""

    def __init__(self, target_window: QWidget, title: str = "Nexus", parent=None):
        super().__init__(parent)
        self._target_window = target_window
        self._drag_offset: QPoint | None = None
        self.setFixedHeight(38)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 8, 4)
        layout.setSpacing(0)

        controls = QWidget(self)
        controls.setStyleSheet("background: transparent;")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self.close_button = TrafficLightButton("#FF5F57", "×", controls)
        self.minimize_button = TrafficLightButton("#FEBC2E", "−", controls)
        self.zoom_button = TrafficLightButton("#28C840", "+", controls)

        controls_layout.addWidget(self.close_button)
        controls_layout.addWidget(self.minimize_button)
        controls_layout.addWidget(self.zoom_button)
        controls.setFixedWidth(72)

        self.title_label = QLabel("", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.hide()

        self.theme_toggle = ThemeToggleButton(self)

        layout.addWidget(
            controls, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addStretch(1)
        layout.addWidget(
            self.theme_toggle,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self.close_button.clicked.connect(self._target_window.close)
        self.minimize_button.clicked.connect(self._target_window.showMinimized)
        self.zoom_button.clicked.connect(self._toggle_zoom)

    def _toggle_zoom(self):
        if self._target_window.isMaximized():
            self._target_window.showNormal()
        else:
            self._target_window.showMaximized()

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_zoom()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        child = self.childAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and not isinstance(
            child, (TrafficLightButton, ThemeToggleButton)
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
    """Custom bookmark tree renderer for folder pills, groups, and links in Light & Dark modes."""

    def paint(self, painter, option, index):  # noqa: ANN001
        data = index.data(Qt.ItemDataRole.UserRole) or {}
        is_folder = data.get("type") == "folder"
        tm = get_theme_manager()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(10, 4, -10, -4)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        if is_folder:
            style = index.data(Qt.ItemDataRole.UserRole + 1) or {}
            accent = QColor(style.get("start", "#5B8DEF"))

            if tm.is_dark:
                fill = QColor("#0E1828") if (selected or hovered) else QColor("#08101C")
                border = QColor(
                    accent.red(),
                    accent.green(),
                    accent.blue(),
                    160 if (selected or hovered) else 75,
                )
                text_color = QColor("#F8FAFC")
            else:
                fill = (
                    QColor(255, 255, 255, 245)
                    if (selected or hovered)
                    else QColor(255, 255, 255, 180)
                )
                border = QColor(
                    accent.red(),
                    accent.green(),
                    accent.blue(),
                    180 if (selected or hovered) else 90,
                )
                text_color = QColor("#0F172A")

            pill_rect = rect.adjusted(0, 2, 0, -2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(pill_rect, 10, 10)
            painter.setPen(QPen(border, 1.2 if (selected or hovered) else 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(pill_rect, 10, 10)

            # Vibrant accent bar on the left
            bar = QRectF(
                pill_rect.left() + 8, pill_rect.top() + 9, 3.5, pill_rect.height() - 18
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(bar, 1.75, 1.75)

            text_rect = pill_rect.adjusted(22, 0, -14, 0)
            font = option.font
            font.setPointSize(14)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(text_color)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )
        elif data.get("type") == "group":
            style = index.data(Qt.ItemDataRole.UserRole + 1) or {}
            accent = QColor(style.get("start", "#5B8DEF"))
            text_rect = rect.adjusted(22, 0, -10, 0)

            if hovered or selected:
                painter.setPen(Qt.PenStyle.NoPen)
                bg_alpha = 24 if selected else 14
                painter.setBrush(
                    QColor(255, 255, 255, bg_alpha)
                    if tm.is_dark
                    else QColor(15, 23, 42, bg_alpha)
                )
                painter.drawRoundedRect(rect.adjusted(2, 1, -2, -1), 8, 8)

            dot_rect = text_rect.adjusted(0, 0, 0, 0)
            dot_rect.setWidth(8)
            dot_rect.moveTop(text_rect.top() + (text_rect.height() - 8) // 2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawEllipse(dot_rect)
            text_rect.adjust(14, 0, 0, 0)

            font = option.font
            font.setPointSize(13)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor("#CBD5E1") if tm.is_dark else QColor("#334155"))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )

            count = data.get("count")
            if count:
                badge_text = f"({count})"
                painter.setPen(QColor("#8EA0BC") if tm.is_dark else QColor("#64748B"))
                badge_rect = rect.adjusted(rect.width() - 44, 0, -4, 0)
                painter.drawText(
                    badge_rect,
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight,
                    badge_text,
                )
        else:
            # Per-bookmark accent
            bookmark_data = index.data(Qt.ItemDataRole.UserRole) or {}
            accent_hex = bookmark_data.get("accent")
            if not accent_hex and index.parent().isValid():
                folder_style = index.parent().data(Qt.ItemDataRole.UserRole + 1) or {}
                accent_hex = folder_style.get("start")

            text_rect = rect.adjusted(22, 0, -10, 0)
            if hovered or selected:
                painter.setPen(Qt.PenStyle.NoPen)
                bg_alpha = 24 if selected else 14
                painter.setBrush(
                    QColor(255, 255, 255, bg_alpha)
                    if tm.is_dark
                    else QColor(15, 23, 42, bg_alpha)
                )
                painter.drawRoundedRect(rect.adjusted(2, 1, -2, -1), 8, 8)

            if accent_hex:
                dot_rect = text_rect.adjusted(0, 0, 0, 0)
                dot_rect.setWidth(8)
                dot_rect.moveTop(text_rect.top() + (text_rect.height() - 8) // 2)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(accent_hex))
                painter.drawEllipse(dot_rect)
                text_rect.adjust(14, 0, 0, 0)

            font = option.font
            font.setPointSize(13)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor("#CBD5E1") if tm.is_dark else QColor("#334155"))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )

        painter.restore()

    def sizeHint(self, option, index):  # noqa: ANN001
        data = index.data(Qt.ItemDataRole.UserRole) or {}
        if data.get("type") == "folder":
            height = 52
        elif data.get("type") == "group":
            height = 34
        else:
            height = 34
        return QSize(option.rect.width(), height)


class NeonURLItemDelegate(QStyledItemDelegate):
    """Paints URL rows as clean list items with luminous status indicator dots."""

    def paint(self, painter, option, index):  # noqa: ANN001
        if index.column() == 0:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        tm = get_theme_manager()
        tokens = tm.tokens

        cell_rect = option.rect.adjusted(8, 2, -8, -2)
        row_rect = cell_rect

        if option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                QColor(59, 130, 246, 40) if tm.is_dark else QColor(59, 130, 246, 30)
            )
            painter.drawRoundedRect(row_rect, 6, 6)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(
                QColor(255, 255, 255, 14) if tm.is_dark else QColor(15, 23, 42, 10)
            )
            painter.drawRoundedRect(row_rect, 6, 6)

        if index.column() == 1:
            font = option.font
            font.setPointSize(14)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            painter.setPen(QColor(tokens.text_primary))
            painter.drawText(
                row_rect.adjusted(12, 0, -8, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )
        else:
            status_state = index.data(Qt.ItemDataRole.UserRole) or "ready"
            status_label = str(index.data(Qt.ItemDataRole.DisplayRole))

            state_colors = {
                "ready": QColor(tokens.status_ready),
                "opening": QColor(tokens.status_opening),
                "opened": QColor(tokens.status_opened),
                "failed": QColor(tokens.status_failed),
            }
            status_color = state_colors.get(status_state, QColor(tokens.status_ready))

            font = option.font
            font.setPointSize(13)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            text_width = painter.fontMetrics().horizontalAdvance(status_label)
            group_width = 10 + 8 + text_width
            group_left = row_rect.left() + max(
                14,
                int((row_rect.width() - group_width) / 2),
            )

            dot_x = group_left + 4
            dot_y = row_rect.center().y()

            # Outer subtle glow ring
            painter.setBrush(
                QColor(
                    status_color.red(), status_color.green(), status_color.blue(), 50
                )
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot_x - 5, int(dot_y) - 5, 10, 10)

            # Inner bright dot
            painter.setBrush(status_color)
            painter.drawEllipse(dot_x - 3, int(dot_y) - 3, 6, 6)

            painter.setPen(QColor(tokens.text_secondary))
            painter.drawText(
                row_rect.adjusted(group_left + 14 - row_rect.left(), 0, -10, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                status_label,
            )

        painter.restore()

    def sizeHint(self, option, index):  # noqa: ANN001
        if index.column() == 0:
            return QSize(0, 44)
        return QSize(option.rect.width(), 44)


HREF_PATTERN = re.compile(r'href=["\'](https?://[^"\']+)["\']', re.IGNORECASE)


def extract_urls_from_mime_data(
    mime_data: QMimeData | None,
    url_processor: URLProcessor,
) -> list[str]:
    """Extract URLs from QMimeData across URLs, HTML links, and plain text."""
    if mime_data is None:
        return []

    urls: list[str] = []

    # Priority 1: Direct URLs (e.g. copied or dragged links from browsers)
    if mime_data.hasUrls():
        for qurl in mime_data.urls():
            if qurl.isValid():
                s = qurl.toString()
                if s.startswith(("http://", "https://")):
                    urls.append(s)

    # Priority 2: HTML content with links
    if mime_data.hasHtml():
        html = mime_data.html()
        found_urls = HREF_PATTERN.findall(html)
        if found_urls:
            urls.extend(found_urls)
        elif mime_data.hasText():
            text = mime_data.text()
            if text:
                urls.extend(url_processor.extract_urls(text))

    # Priority 3: Plain text
    elif mime_data.hasText():
        text = mime_data.text()
        if text:
            urls.extend(url_processor.extract_urls(text))

    return url_processor.filter_openable_urls(urls)


class URLTableWidget(QTableWidget):
    """Table widget with batched updates and high performance."""

    url_activated = Signal(int, str)
    urls_changed = Signal(list)
    urls_pasted = Signal(list)
    file_dropped = Signal(str)

    STATUS_LABELS = {
        "ready": "Ready",
        "opening": "Opening",
        "opened": "Opened",
        "failed": "Failed",
    }

    _FILE_DROP_EXTENSIONS = {".txt", ".csv", ".md"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url_processor = URLProcessor()
        self.href_pattern = HREF_PATTERN
        self.url_counter = 0
        self._suspend_url_events = False

        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["#", "URL", "Status"])

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMouseTracking(True)
        self.setItemDelegate(NeonURLItemDelegate(self))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 0)
        self.setColumnWidth(2, 140)
        self.setColumnHidden(0, True)

        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.itemChanged.connect(self._on_item_changed)
        self.itemDoubleClicked.connect(self._activate_item_url)

    def add_urls(self, urls: list[str]):
        """Add URLs with batched sorting and UI update suspension."""
        cleaned = self.url_processor.filter_openable_urls(urls)
        if not cleaned:
            return
        existing = self.get_all_urls()
        combined = sorted(existing + cleaned, key=lambda s: s.lower())
        self.replace_urls(combined)

    def update_status(self, row: int, success: bool):
        self.set_status_state(row, "opened" if success else "failed")

    def set_status_state(self, row: int, state: str):
        if 0 <= row < self.rowCount():
            status_item = self.item(row, 2)
            if status_item:
                status_item.setText(self.STATUS_LABELS.get(state, "Ready"))
                status_item.setData(Qt.ItemDataRole.UserRole, state)

    def get_all_urls(self) -> list[str]:
        urls = []
        for row in range(self.rowCount()):
            url_item = self.item(row, 1)
            if url_item:
                urls.append(url_item.text())
        return urls

    def clear_table(self):
        self._suspend_url_events = True
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(0)
            self.url_counter = 0
        finally:
            self.setUpdatesEnabled(True)
            self._suspend_url_events = False
        self._emit_urls_changed()

    def replace_urls(self, urls: list[str]):
        """Batched row replacement avoiding per-row paint recalculations."""
        self._suspend_url_events = True
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(0)
            self.url_counter = 0
            sorted_urls = sorted(
                self.url_processor.filter_openable_urls(urls), key=lambda s: s.lower()
            )
            for url in sorted_urls:
                self.url_counter += 1
                row = self.rowCount()
                self.insertRow(row)
                self.setRowHeight(row, 44)

                number_item = QTableWidgetItem(str(self.url_counter))
                number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                number_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.setItem(row, 0, number_item)

                url_item = QTableWidgetItem(url)
                url_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                )
                self.setItem(row, 1, url_item)

                status_item = QTableWidgetItem()
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.setItem(row, 2, status_item)
                self.set_status_state(row, "ready")
        finally:
            self.setUpdatesEnabled(True)
            self._suspend_url_events = False
        self._emit_urls_changed()

    def dragEnterEvent(self, event):  # noqa: N802 - Qt override
        if (
            event.mimeData().hasUrls()
            or event.mimeData().hasText()
            or event.mimeData().hasHtml()
        ):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):  # noqa: N802 - Qt override
        event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802 - Qt override
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
                    if f".{suffix}" in self._FILE_DROP_EXTENSIONS:
                        self.file_dropped.emit(path)
                        event.acceptProposedAction()
                        return
        self._process_mime_data(mime_data)
        event.acceptProposedAction()

    def keyPressEvent(self, event):  # noqa: N802 - Qt override
        paste_modifiers = (
            Qt.KeyboardModifier.ControlModifier,
            Qt.KeyboardModifier.MetaModifier,
        )
        if event.key() == Qt.Key.Key_V and event.modifiers() in paste_modifiers:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                self._process_mime_data(clipboard.mimeData())
            event.accept()
            return
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._activate_current_row()
        else:
            super().keyPressEvent(event)

    def _process_mime_data(self, mime_data: QMimeData):
        urls_to_add = extract_urls_from_mime_data(mime_data, self.url_processor)
        if urls_to_add:
            self.add_urls(urls_to_add)
            self.urls_pasted.emit(urls_to_add)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt override
        item = self.itemAt(event.pos())
        if item and item.column() in (1, 2):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
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
        stripped = text.strip()
        normalized = self.url_processor._normalize_url(stripped)
        if normalized and self.url_processor.is_allowed_open_url(normalized):
            return normalized
        parsed_scheme = stripped.split("://", 1)[0].lower() if "://" in stripped else ""
        if parsed_scheme and parsed_scheme not in {"http", "https"}:
            return ""
        return stripped

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
    """Legacy neon button with hover glow animation."""

    def __init__(self, text: str = "", color: str = "#5B8DEF"):
        super().__init__(text)
        self.color = color
        self._setup_shadow_effect()
        self.update_style(color)
        self._setup_animations()

    def _setup_shadow_effect(self):
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

    def update_style(self, new_color: str):
        self.color = new_color
        self.shadow.setColor(QColor(self.color))
        darker_color = QColor(self.color).darker(150).name()
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.color}, stop:1 {darker_color});
                color: #E8ECF4;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
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
    """iOS 27 ultra-glossy tactile glass button with 3D gel dome optics and distinct vibrant colors."""

    def __init__(self, text: str = "", variant: str = "primary"):
        super().__init__(text)
        self.variant = variant
        self._variant_palette: dict[str, str] = {}
        self._setup_glow_effect()
        self._apply_variant_style()
        self._setup_animations()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setMinimumHeight(46)
        if text != "+":
            self.setMinimumWidth(116)
        get_theme_manager().theme_changed.connect(lambda _: self._on_theme_changed())

    def _on_theme_changed(self):
        self._apply_variant_style()
        self.update()

    def _setup_glow_effect(self):
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 2)
        self.setGraphicsEffect(self.shadow)

    def _get_glow_color(self) -> str:
        colors = {
            "primary": "#0284C7",
            "home": "#0284C7",
            "open": "#059669",
            "secondary": "#10B981",
            "save": "#0891B2",
            "import": "#4F46E5",
            "export": "#9333EA",
            "quick": "#06B6D4",
            "rich": "#8B5CF6",
            "tertiary": "#D97706",
            "undo": "#D97706",
            "amber": "#D97706",
            "load_file": "#D97706",
            "teal": "#0D9488",
            "quaternary": "#E11D48",
            "clear": "#E11D48",
            "danger": "#DC2626",
        }
        return colors.get(self.variant, "#0284C7")

    def _setup_animations(self):
        glow_color = self._get_glow_color()
        self.shadow.setColor(QColor(glow_color))

        self.glow_in = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_in.setDuration(160)
        self.glow_in.setEndValue(Config.GLOW_RADIUS)
        self.glow_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.glow_out = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_out.setDuration(200)
        self.glow_out.setEndValue(0)
        self.glow_out.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):  # noqa: N802 - Qt override
        self.glow_out.stop()
        self.glow_in.setStartValue(self.shadow.blurRadius())
        self.glow_in.start()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802 - Qt override
        self.glow_in.stop()
        self.glow_out.setStartValue(self.shadow.blurRadius())
        self.glow_out.start()
        super().leaveEvent(event)

    def _apply_variant_style(self):
        tm = get_theme_manager()
        if tm.is_dark:
            palettes = {
                # Home: Electric Sapphire
                "primary": {
                    "start": "#2563EB",
                    "end": "#1D4ED8",
                    "hover_start": "#3B82F6",
                    "hover_end": "#2563EB",
                    "border": "#93C5FD",
                    "text": "#FFFFFF",
                },
                "home": {
                    "start": "#2563EB",
                    "end": "#1D4ED8",
                    "hover_start": "#3B82F6",
                    "hover_end": "#2563EB",
                    "border": "#93C5FD",
                    "text": "#FFFFFF",
                },
                # Open All: Vivid Emerald Mint
                "open": {
                    "start": "#059669",
                    "end": "#047857",
                    "hover_start": "#10B981",
                    "hover_end": "#059669",
                    "border": "#6EE7B7",
                    "text": "#FFFFFF",
                },
                "secondary": {
                    "start": "#059669",
                    "end": "#047857",
                    "hover_start": "#10B981",
                    "hover_end": "#059669",
                    "border": "#6EE7B7",
                    "text": "#FFFFFF",
                },
                # Save: Radiant Neon Cyan
                "save": {
                    "start": "#0891B2",
                    "end": "#0E7490",
                    "hover_start": "#06B6D4",
                    "hover_end": "#0891B2",
                    "border": "#67E8F9",
                    "text": "#FFFFFF",
                },
                "quick": {
                    "start": "#0891B2",
                    "end": "#0E7490",
                    "hover_start": "#06B6D4",
                    "hover_end": "#0891B2",
                    "border": "#67E8F9",
                    "text": "#FFFFFF",
                },
                # Import: Royal Electric Indigo
                "import": {
                    "start": "#4F46E5",
                    "end": "#4338CA",
                    "hover_start": "#6366F1",
                    "hover_end": "#4F46E5",
                    "border": "#A5B4FC",
                    "text": "#FFFFFF",
                },
                # Export: Luminous Magenta Violet
                "export": {
                    "start": "#9333EA",
                    "end": "#7E22CE",
                    "hover_start": "#A855F7",
                    "hover_end": "#9333EA",
                    "border": "#C084FC",
                    "text": "#FFFFFF",
                },
                "rich": {
                    "start": "#9333EA",
                    "end": "#7E22CE",
                    "hover_start": "#A855F7",
                    "hover_end": "#9333EA",
                    "border": "#C084FC",
                    "text": "#FFFFFF",
                },
                # Clear: Fiery Coral Crimson
                "clear": {
                    "start": "#E11D48",
                    "end": "#BE123C",
                    "hover_start": "#F43F5E",
                    "hover_end": "#E11D48",
                    "border": "#FB7185",
                    "text": "#FFFFFF",
                },
                "danger": {
                    "start": "#DC2626",
                    "end": "#B91C1C",
                    "hover_start": "#EF4444",
                    "hover_end": "#DC2626",
                    "border": "#FCA5A5",
                    "text": "#FFFFFF",
                },
                # Amber Gold Glass
                "amber": {
                    "start": "#D97706",
                    "end": "#B45309",
                    "hover_start": "#F59E0B",
                    "hover_end": "#D97706",
                    "border": "#FCD34D",
                    "text": "#FFFFFF",
                },
                "undo": {
                    "start": "#D97706",
                    "end": "#B45309",
                    "hover_start": "#F59E0B",
                    "hover_end": "#D97706",
                    "border": "#FCD34D",
                    "text": "#FFFFFF",
                },
            }
        else:
            # Light Mode Palettes (Tailored for Light Blue aesthetic)
            palettes = {
                # Home: Electric Ocean Azure
                "primary": {
                    "start": "#0284C7",
                    "end": "#0369A1",
                    "hover_start": "#38BDF8",
                    "hover_end": "#0284C7",
                    "border": "#7DD3FC",
                    "text": "#FFFFFF",
                },
                "home": {
                    "start": "#0284C7",
                    "end": "#0369A1",
                    "hover_start": "#38BDF8",
                    "hover_end": "#0284C7",
                    "border": "#7DD3FC",
                    "text": "#FFFFFF",
                },
                # Open All: Vivid Emerald Mint
                "open": {
                    "start": "#10B981",
                    "end": "#059669",
                    "hover_start": "#34D399",
                    "hover_end": "#10B981",
                    "border": "#A7F3D0",
                    "text": "#FFFFFF",
                },
                "secondary": {
                    "start": "#10B981",
                    "end": "#059669",
                    "hover_start": "#34D399",
                    "hover_end": "#10B981",
                    "border": "#A7F3D0",
                    "text": "#FFFFFF",
                },
                # Save: Radiant Electric Cyan
                "save": {
                    "start": "#06B6D4",
                    "end": "#0891B2",
                    "hover_start": "#22D3EE",
                    "hover_end": "#06B6D4",
                    "border": "#A5F3FC",
                    "text": "#FFFFFF",
                },
                "quick": {
                    "start": "#06B6D4",
                    "end": "#0891B2",
                    "hover_start": "#22D3EE",
                    "hover_end": "#06B6D4",
                    "border": "#A5F3FC",
                    "text": "#FFFFFF",
                },
                # Import: Royal Electric Indigo
                "import": {
                    "start": "#6366F1",
                    "end": "#4F46E5",
                    "hover_start": "#818CF8",
                    "hover_end": "#6366F1",
                    "border": "#C7D2FE",
                    "text": "#FFFFFF",
                },
                # Export: Luminous Magenta Violet
                "export": {
                    "start": "#8B5CF6",
                    "end": "#7C3AED",
                    "hover_start": "#A78BFA",
                    "hover_end": "#8B5CF6",
                    "border": "#DDD6FE",
                    "text": "#FFFFFF",
                },
                "rich": {
                    "start": "#8B5CF6",
                    "end": "#7C3AED",
                    "hover_start": "#A78BFA",
                    "hover_end": "#8B5CF6",
                    "border": "#DDD6FE",
                    "text": "#FFFFFF",
                },
                # Clear: Fiery Coral Crimson
                "clear": {
                    "start": "#F43F5E",
                    "end": "#E11D48",
                    "hover_start": "#FB7185",
                    "hover_end": "#F43F5E",
                    "border": "#FECDD3",
                    "text": "#FFFFFF",
                },
                "danger": {
                    "start": "#EF4444",
                    "end": "#DC2626",
                    "hover_start": "#F87171",
                    "hover_end": "#EF4444",
                    "border": "#FECACA",
                    "text": "#FFFFFF",
                },
                # Amber Gold Glass
                "amber": {
                    "start": "#F59E0B",
                    "end": "#D97706",
                    "hover_start": "#FBBF24",
                    "hover_end": "#F59E0B",
                    "border": "#FDE68A",
                    "text": "#FFFFFF",
                },
                "undo": {
                    "start": "#F59E0B",
                    "end": "#D97706",
                    "hover_start": "#FBBF24",
                    "hover_end": "#F59E0B",
                    "border": "#FDE68A",
                    "text": "#FFFFFF",
                },
            }
        self._variant_palette = palettes.get(self.variant, palettes["primary"])
        glow_color = self._get_glow_color()
        self.shadow.setColor(QColor(glow_color))
        self.update()

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        pressed = self.isDown()
        hovered = self.underMouse()
        palette = self._variant_palette
        enabled = self.isEnabled()

        start = QColor(
            palette["hover_start"]
            if (hovered or self.isChecked())
            else palette["start"]
        )
        end = QColor(
            palette["hover_end"] if (hovered or self.isChecked()) else palette["end"]
        )

        if pressed:
            start = start.darker(118)
            end = end.darker(118)

        if not enabled:
            start.setAlpha(120)
            end.setAlpha(110)

        rounded_rect = QPainterPath()
        rounded_rect.addRoundedRect(rect, 12, 12)

        # 1. Base Glass Fill Gradient
        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        fill.setColorAt(0.0, start)
        fill.setColorAt(1.0, end)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(fill))
        painter.drawRoundedRect(rect, 12, 12)

        # 2. iOS 27 Curved Gel Dome Specular Reflection (top 50%)
        shine_rect = QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.50)
        shine_path = QPainterPath()
        shine_path.addRoundedRect(shine_rect, 12, 12)
        shine = QLinearGradient(shine_rect.topLeft(), shine_rect.bottomLeft())
        shine.setColorAt(0.0, QColor(255, 255, 255, 130 if enabled else 40))
        shine.setColorAt(0.50, QColor(255, 255, 255, 35 if enabled else 15))
        shine.setColorAt(1.0, QColor(255, 255, 255, 0))

        painter.save()
        painter.setClipPath(rounded_rect)
        painter.fillPath(shine_path, QBrush(shine))

        # 3. Top Specular Edge Line
        top_edge = QLinearGradient(rect.topLeft(), rect.topRight())
        top_edge.setColorAt(0.0, QColor(255, 255, 255, 40))
        top_edge.setColorAt(0.5, QColor(255, 255, 255, 230 if enabled else 70))
        top_edge.setColorAt(1.0, QColor(255, 255, 255, 40))
        painter.setPen(QPen(QBrush(top_edge), 1.2))
        painter.drawLine(
            QPointF(rect.left() + 10, rect.top() + 1.2),
            QPointF(rect.right() - 10, rect.top() + 1.2),
        )

        # 4. Bottom Ambient Bevel Shadow
        bottom_shadow = QLinearGradient(
            rect.left(), rect.bottom() - 6, rect.left(), rect.bottom()
        )
        bottom_shadow.setColorAt(0.0, QColor(0, 0, 0, 0))
        bottom_shadow.setColorAt(1.0, QColor(0, 0, 0, 45))
        painter.fillPath(rounded_rect, QBrush(bottom_shadow))
        painter.restore()

        # 5. Multi-Stop Glossy Outer Border
        border_col = QColor(palette["border"])
        if not enabled:
            border_col.setAlpha(70)
        border_grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        border_grad.setColorAt(0.0, QColor(255, 255, 255, 180 if enabled else 70))
        border_grad.setColorAt(0.40, border_col)
        border_grad.setColorAt(1.0, border_col.darker(125))

        painter.setPen(QPen(QBrush(border_grad), 1.3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 12, 12)

        # 6. Typography with 3D physical text drop shadow
        font = self.font()
        font.setFamily("Helvetica Neue")
        font.setPointSize(14)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)

        text_rect = rect.adjusted(0, 1, 0, 1) if pressed else rect

        # Text shadow
        painter.setPen(QColor(0, 0, 0, 110 if enabled else 40))
        painter.drawText(
            text_rect.adjusted(0, 1, 0, 1),
            Qt.AlignmentFlag.AlignCenter,
            self.text(),
        )

        # Text foreground
        painter.setPen(
            QColor(palette["text"]) if enabled else QColor(160, 170, 185, 140)
        )
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())

        if enabled and self.hasFocus():
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.0))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)


class OutlinedLabel(QLabel):
    """A QLabel with outlined text for better visibility."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.outline_color = QColor(0, 0, 0)
        self.outline_width = 2

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        text = self.text()
        font = self.font()
        painter.setFont(font)

        path = QPainterPath()
        path.addText(0, font.pointSize(), font, text)

        rect = self.rect()
        text_rect = painter.fontMetrics().boundingRect(text)

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

        painter.translate(x, y)
        pen = QPen(
            self.outline_color,
            self.outline_width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.strokePath(path, pen)
        painter.fillPath(path, self.palette().color(self.foregroundRole()))


class GlassPanel(QWidget):
    """A semi-transparent panel with a colored border, used as a tab background."""

    def __init__(self):
        super().__init__()
        self.setObjectName("GlassPanel")
        self.setStyleSheet(
            """
            #GlassPanel {
                background-color: transparent;
                border: 2px solid #444;
                border-radius: 12px;
            }
        """
        )

    def update_style(self, color: str):
        self.setStyleSheet(
            f"""
            #GlassPanel {{
                background-color: transparent;
                border: 2px solid {color};
                border-radius: 12px;
            }}
        """
        )


class BookmarkSearchBar(QLineEdit):
    """Search bar with 60ms debounce for instantaneous typing without thread blocking."""

    urls_pasted = Signal(list)
    debounced_text_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.url_processor = URLProcessor()
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(60)
        self._debounce_timer.timeout.connect(self._on_debounce_timeout)
        self.textChanged.connect(self._restart_timer)
        get_theme_manager().theme_changed.connect(lambda _: self._apply_theme_style())
        self._apply_theme_style()

    def _apply_theme_style(self):
        tm = get_theme_manager()
        tokens = tm.tokens
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {tokens.input_bg};
                border: 1px solid {tokens.input_border};
                border-radius: 9px;
                color: {tokens.input_text};
                padding: 9px 14px;
                font-size: 14px;
                font-family: "Helvetica Neue", sans-serif;
                selection-background-color: rgba(59, 130, 246, 0.50);
            }}
            QLineEdit:focus {{
                border: 1px solid {tokens.input_focus_border};
            }}
            QLineEdit::placeholder {{
                color: {tokens.input_placeholder};
            }}
        """)

    def _restart_timer(self, text: str) -> None:
        self._last_text = text
        self._debounce_timer.start()

    def _on_debounce_timeout(self) -> None:
        self.debounced_text_changed.emit(self.text())

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        paste_modifiers = (
            Qt.KeyboardModifier.ControlModifier,
            Qt.KeyboardModifier.MetaModifier,
        )
        if event.key() == Qt.Key.Key_V and event.modifiers() in paste_modifiers:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                urls = extract_urls_from_mime_data(
                    clipboard.mimeData(), self.url_processor
                )
                if urls:
                    self.urls_pasted.emit(urls)
                    event.accept()
                    return
        super().keyPressEvent(event)


class URLEmptyStateWidget(QWidget):
    """Interactive, visually refined empty state panel."""

    urls_pasted = Signal(list)
    file_dropped = Signal(str)

    _FILE_DROP_EXTENSIONS = {".txt", ".csv", ".md"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.url_processor = URLProcessor()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self.setStyleSheet("background: transparent;")

        empty_layout = QVBoxLayout(self)
        empty_layout.setContentsMargins(28, 28, 28, 28)
        empty_layout.setSpacing(12)
        empty_layout.addStretch()

        self.url_empty_title = MetallicLabel(
            "Paste URLs to get started", variant="section"
        )
        self.url_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.url_empty_title)

        self.url_empty_note = MetallicLabel(
            "Copied links appear here automatically. Drag text or drop .txt / .csv files anytime.",
            variant="dim",
        )
        self.url_empty_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.url_empty_note.setWordWrap(True)
        empty_layout.addWidget(self.url_empty_note)
        empty_layout.addStretch()

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        self.setFocus()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        paste_modifiers = (
            Qt.KeyboardModifier.ControlModifier,
            Qt.KeyboardModifier.MetaModifier,
        )
        if event.key() == Qt.Key.Key_V and event.modifiers() in paste_modifiers:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                urls = extract_urls_from_mime_data(
                    clipboard.mimeData(), self.url_processor
                )
                if urls:
                    self.urls_pasted.emit(urls)
                    event.accept()
                    return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt override
        mime_data = event.mimeData()
        if mime_data.hasUrls() or mime_data.hasText() or mime_data.hasHtml():
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802 - Qt override
        event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 - Qt override
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
                    if f".{suffix}" in self._FILE_DROP_EXTENSIONS:
                        self.file_dropped.emit(path)
                        event.acceptProposedAction()
                        return
        text = mime_data.text() if mime_data.hasText() else ""
        urls = self.url_processor.extract_urls(text) if text else []
        if urls:
            self.urls_pasted.emit(urls)
        event.acceptProposedAction()
