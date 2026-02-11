"""Custom UI widgets for the Nexus application."""

import asyncio
import re

from PySide6.QtCore import (
    QEasingCurve,
    QMimeData,
    QPropertyAnimation,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QGraphicsDropShadowEffect,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from nexus.core.config import Config, logger
from nexus.utils.url_processor import URLProcessor


class AsyncWorker(QThread):
    """Generic QThread worker for running asynchronous tasks off the main UI thread."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__()
        self.coro_func = coro_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.coro_func(*self.args, **self.kwargs))
            self.finished.emit(result)
        except (RuntimeError, asyncio.CancelledError) as e:
            logger.error("Async worker error: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            if loop and not loop.is_closed():
                loop.close()


class URLTableWidget(QTableWidget):
    """A custom table widget for displaying URLs with numbering and status tracking."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url_processor = URLProcessor()
        self.href_pattern = re.compile(
            r'href=["\'](https?://[^"\']+)["\']', re.IGNORECASE
        )
        self.url_counter = 0

        # Setup table structure
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["#", "URL", "Status"])

        # Configure table appearance and behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        # Set column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Number column
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # URL column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Status column
        self.setColumnWidth(0, 50)  # Number column width
        self.setColumnWidth(2, 80)  # Status column width

        # Enable drag and drop
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        # Enable text cursor (blinking caret) for better UX
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.AllEditTriggers
        )  # Enable editing to show cursor
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def add_urls(self, urls: list[str]):
        """Add URLs to the table with automatic numbering."""
        for url in urls:
            self.url_counter += 1
            row = self.rowCount()
            self.insertRow(row)

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
            status_item = QTableWidgetItem("⏳")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Read-only
            self.setItem(row, 2, status_item)

    def update_status(self, row: int, success: bool):
        """Update the status of a URL row."""
        if 0 <= row < self.rowCount():
            status_item = self.item(row, 2)
            if status_item:
                status_item.setText("✅" if success else "❌")

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
        self.setRowCount(0)
        self.url_counter = 0

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
        if (
            event.key() == Qt.Key.Key_V
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            # Handle Ctrl+V paste
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            self._process_mime_data(mime_data)
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
            variant: 'primary', 'secondary', 'tertiary', or 'danger'
        """
        super().__init__(text)
        self.variant = variant
        self._setup_glow_effect()
        self._apply_variant_style()
        self._setup_animations()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_glow_effect(self):
        """Setup the drop shadow effect for glow."""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

    def _get_glow_color(self) -> str:
        """Get the glow color based on variant."""
        colors = {
            "primary": "#3b82f6",  # Blue glow
            "secondary": "#ff2d92",  # Pink glow
            "tertiary": "#22c55e",  # Green glow
            "danger": "#ef4444",  # Red glow
        }
        return colors.get(self.variant, "#3b82f6")

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
        """Apply styling based on variant - using icon colors (cyan, magenta, green)."""
        if self.variant == "primary":
            # Primary: Darker Blue with white text
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(30, 80, 150, 0.9), stop:1 rgba(20, 60, 120, 0.9));
                    color: #ffffff;
                    border: 1px solid rgba(50, 100, 180, 0.6);
                    border-radius: 12px;
                    padding: 12px 24px;
                    min-width: 120px;
                    font-weight: 700;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(50, 120, 200, 0.95), stop:1 rgba(40, 100, 170, 0.95));
                    border: 1px solid rgba(80, 150, 230, 0.9);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(20, 60, 120, 0.95), stop:1 rgba(15, 50, 100, 0.95));
                }
            """)
        elif self.variant == "secondary":
            # Secondary: Magenta/Pink with white text
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 45, 146, 0.85), stop:1 rgba(204, 0, 102, 0.85));
                    color: #ffffff;
                    border: 1px solid rgba(255, 45, 146, 0.5);
                    border-radius: 12px;
                    padding: 12px 24px;
                    min-width: 120px;
                    font-weight: 700;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 100, 180, 0.95), stop:1 rgba(240, 30, 140, 0.95));
                    border: 1px solid rgba(255, 120, 200, 0.9);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(204, 36, 117, 0.9), stop:1 rgba(153, 0, 82, 0.9));
                }
            """)
        elif self.variant == "tertiary":
            # Tertiary: Neon Green with WHITE text
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(0, 180, 0, 0.85), stop:1 rgba(0, 140, 0, 0.85));
                    color: #ffffff;
                    border: 1px solid rgba(57, 255, 20, 0.5);
                    border-radius: 12px;
                    padding: 12px 24px;
                    min-width: 120px;
                    font-weight: 700;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(50, 220, 50, 0.95), stop:1 rgba(40, 180, 40, 0.95));
                    border: 1px solid rgba(80, 255, 50, 0.9);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(0, 150, 0, 0.9), stop:1 rgba(0, 120, 0, 0.9));
                }
            """)
        else:  # danger/delete style - RED
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 59, 48, 0.4), stop:1 rgba(200, 40, 40, 0.4));
                    color: #ffffff;
                    border: 1px solid rgba(255, 59, 48, 0.5);
                    border-radius: 12px;
                    padding: 12px 24px;
                    min-width: 120px;
                    font-weight: 700;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(255, 80, 70, 0.7), stop:1 rgba(220, 60, 60, 0.7));
                    border: 1px solid rgba(255, 100, 90, 0.9);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(200, 40, 40, 0.5), stop:1 rgba(150, 30, 30, 0.5));
                }
            """)


class OutlinedLabel(QLabel):
    """A QLabel with outlined text for better visibility."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.outline_color = QColor(0, 0, 0)  # Black outline
        self.outline_width = 2

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override  # ty: ignore[invalid-method-override]
        """Custom paint event to draw outlined text."""
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
