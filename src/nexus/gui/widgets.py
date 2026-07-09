"""Custom UI widgets for the Nexus application."""

import re

from PySide6.QtCore import (
    QEasingCurve,
    QMimeData,
    QPoint,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
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
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from nexus.core.config import Config
from nexus.utils.url_processor import URLProcessor
from razorcore.threading import AsyncTaskWorker


class AsyncWorker(AsyncTaskWorker):
    """Nexus async worker on razorcore.AsyncTaskWorker with result_ready alias."""

    result_ready = Signal(object)

    def __init__(self, coro_func, *args, **kwargs):
        super().__init__(coro_func, *args, **kwargs)
        # Preserve the historical Nexus signal name used by MainWindow.
        self.finished.connect(self.result_ready.emit)


class CosmicFrame(QWidget):
    """Rounded dark shell for the frameless macOS window."""

    def paintEvent(self, event: QPaintEvent):  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(0, 0, -1, -1)
        rounded_rect = QPainterPath()
        rounded_rect.addRoundedRect(rect, 16, 16)

        base = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        base.setColorAt(0.0, QColor("#141820"))
        base.setColorAt(0.45, QColor("#10141C"))
        base.setColorAt(1.0, QColor("#0C1016"))
        painter.fillPath(rounded_rect, QBrush(base))

        painter.setClipPath(rounded_rect)
        # Soft RGB corner washes — blue top-left, green bottom-left, red top-right
        blue_wash = QLinearGradient(rect.topLeft(), rect.center())
        blue_wash.setColorAt(0.0, QColor(45, 120, 220, 28))
        blue_wash.setColorAt(1.0, QColor(45, 120, 220, 0))
        painter.fillPath(rounded_rect, QBrush(blue_wash))

        green_wash = QLinearGradient(
            rect.left(),
            rect.bottom(),
            rect.left() + rect.width() * 0.45,
            rect.center().y(),
        )
        green_wash.setColorAt(0.0, QColor(40, 170, 110, 22))
        green_wash.setColorAt(1.0, QColor(40, 170, 110, 0))
        painter.fillPath(rounded_rect, QBrush(green_wash))

        red_wash = QLinearGradient(rect.topRight(), rect.center())
        red_wash.setColorAt(0.0, QColor(210, 70, 80, 20))
        red_wash.setColorAt(1.0, QColor(210, 70, 80, 0))
        painter.fillPath(rounded_rect, QBrush(red_wash))
        painter.setClipping(False)

        border = QLinearGradient(rect.topLeft(), rect.topRight())
        border.setColorAt(0.0, QColor(70, 140, 230, 90))
        border.setColorAt(0.5, QColor(60, 180, 120, 70))
        border.setColorAt(1.0, QColor(220, 80, 90, 80))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QBrush(border), 1.4))
        painter.drawRoundedRect(rect, 16, 16)

        super().paintEvent(event)


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


class WindowTitleBar(QWidget):
    """Custom title bar for the frameless window shell."""

    def __init__(self, target_window: QWidget, title: str = "Nexus", parent=None):
        super().__init__(parent)
        self._target_window = target_window
        self._drag_offset: QPoint | None = None
        self.setFixedHeight(36)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 4)
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
        self.title_label.setStyleSheet("""
            QLabel {
                color: rgba(232, 236, 244, 0.88);
                font-family: "Helvetica Neue", sans-serif;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
            }
        """)
        self.title_label.hide()

        layout.addWidget(
            controls, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
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

    def mouseDoubleClickEvent(self, event):  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_zoom()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):  # noqa: N802 - Qt override
        child = self.childAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and not isinstance(
            child, TrafficLightButton
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
    """Custom bookmark tree renderer for folder rows and links."""

    def paint(self, painter, option, index):  # noqa: ANN001
        data = index.data(Qt.ItemDataRole.UserRole) or {}
        is_folder = data.get("type") == "folder"

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect.adjusted(10, 4, -10, -4)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        if is_folder:
            style = index.data(Qt.ItemDataRole.UserRole + 1) or {}
            accent = QColor(style.get("start", "#5B8DEF"))
            fill = QColor("#1C1F27")
            border = QColor(255, 255, 255, 18)

            if selected or hovered:
                fill = QColor("#232733")
                border = QColor(accent.red(), accent.green(), accent.blue(), 90)

            pill_rect = rect.adjusted(0, 2, 0, -2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(pill_rect, 10, 10)
            painter.setPen(QPen(border, 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(pill_rect, 10, 10)

            # Accent bar on the left
            bar = QRectF(
                pill_rect.left() + 8, pill_rect.top() + 10, 3, pill_rect.height() - 20
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(bar, 1.5, 1.5)

            text_rect = pill_rect.adjusted(22, 0, -14, 0)
            font = option.font
            font.setPointSize(14)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.setPen(QColor("#E8ECF4"))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )
        else:
            text_rect = rect.adjusted(22, 0, -10, 0)
            if hovered or selected:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, 12 if hovered else 18))
                painter.drawRoundedRect(rect.adjusted(2, 1, -2, -1), 8, 8)
            font = option.font
            font.setPointSize(13)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor("#A8B0C0"))
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
            52 if data.get("type") == "folder" else 34,
        )

    def _draw_folder_icon(self, painter: QPainter, rect, icon_color: QColor):
        painter.save()

        tab_path = QPainterPath()
        tab_path.addRoundedRect(rect.adjusted(3, 1, -18, -16), 5, 5)
        body_path = QPainterPath()
        body_path.addRoundedRect(rect.adjusted(1, 12, -2, -1), 8, 8)

        top_gradient = QLinearGradient(
            rect.left(), rect.top(), rect.left(), rect.bottom()
        )
        top_gradient.setColorAt(0.0, icon_color.lighter(135))
        top_gradient.setColorAt(1.0, icon_color)

        body_gradient = QLinearGradient(
            rect.left(), rect.top(), rect.right(), rect.bottom()
        )
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
    """Paints URL rows as clean list items with status indicators."""

    STATE_COLORS = {
        "ready": QColor("#6BCB8B"),
        "opening": QColor("#E0B84A"),
        "opened": QColor("#5BBF8A"),
        "failed": QColor("#E57373"),
    }

    def paint(self, painter, option, index):  # noqa: ANN001
        if index.column() == 0:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cell_rect = option.rect.adjusted(6, 4, -6, -4)
        row_rect = (
            cell_rect.adjusted(0, 0, 8, 0)
            if index.column() == 1
            else cell_rect.adjusted(-8, 0, 0, 0)
        )

        fill = QColor("#181B22")
        border = QColor(255, 255, 255, 14)
        if option.state & QStyle.StateFlag.State_Selected:
            fill = QColor("#1E2430")
            border = QColor(91, 141, 239, 70)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            fill = QColor("#1C2029")
            border = QColor(255, 255, 255, 22)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(row_rect, 10, 10)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(row_rect, 10, 10)

        if index.column() == 1:
            font = option.font
            font.setPointSize(14)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            painter.setPen(QColor("#E8ECF4"))
            painter.drawText(
                row_rect.adjusted(16, 0, -12, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                str(index.data(Qt.ItemDataRole.DisplayRole)),
            )
        else:
            status_state = index.data(Qt.ItemDataRole.UserRole) or "ready"
            status_label = str(index.data(Qt.ItemDataRole.DisplayRole))
            status_color = self.STATE_COLORS.get(status_state, QColor("#6BCB8B"))

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
            painter.setBrush(status_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(dot_x - 3, int(dot_y) - 3, 6, 6)

            painter.setPen(QColor("#C8CEDA"))
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
        self.setColumnWidth(2, 140)  # Status column width
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
            self.setRowHeight(row, 44)

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
            self.setRowHeight(row, 44)

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
        if event.key() == Qt.Key.Key_V and event.modifiers() in paste_modifiers:
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
    """A custom button with a subtle hover glow."""

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
        """Updates the button's color and stylesheet."""
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
        self.glow_in_anim.setEndValue(12)
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
    """A clean solid button with subtle hover feedback."""

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
        self.setMinimumHeight(46)
        if text != "+":
            self.setMinimumWidth(140)

    def _setup_glow_effect(self):
        """Setup the drop shadow effect for glow."""
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(0)
        self.shadow.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow)

    def _get_glow_color(self) -> str:
        """Get the glow color based on variant."""
        colors = {
            "primary": "#4A90E8",
            "secondary": "#3DB88A",
            "tertiary": "#5B8DEF",
            "quaternary": "#E05A5A",
            "danger": "#E05A5A",
        }
        return colors.get(self.variant, "#4A90E8")

    def _disabled_tint(
        self, color_hex: str, lift: int = 112, alpha: int = 160
    ) -> QColor:
        """Keep disabled controls readable without going flat gray."""
        color = QColor(color_hex).lighter(lift)
        color.setAlpha(alpha)
        return color

    def _setup_animations(self):
        """Setup hover glow animations."""
        glow_color = self._get_glow_color()
        self.shadow.setColor(QColor(glow_color))

        self.glow_in = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_in.setDuration(160)
        self.glow_in.setEndValue(12)
        self.glow_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.glow_out = QPropertyAnimation(self.shadow, b"blurRadius")
        self.glow_out.setDuration(200)
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
        """Store the palette used by the custom button paint."""
        palettes = {
            "primary": {
                "start": "#3B7AD4",
                "end": "#2D63B5",
                "hover_start": "#4A90E8",
                "hover_end": "#3B7AD4",
                "border": "#6BA4F0",
                "text": "#FFFFFF",
            },
            "secondary": {
                "start": "#2FA876",
                "end": "#248A60",
                "hover_start": "#3DB88A",
                "hover_end": "#2FA876",
                "border": "#55D0A0",
                "text": "#FFFFFF",
            },
            "tertiary": {
                "start": "#2A3A55",
                "end": "#223048",
                "hover_start": "#354A68",
                "hover_end": "#2A3A55",
                "border": "#4A6A9A",
                "text": "#D6E4FF",
            },
            "quaternary": {
                "start": "#C94A4A",
                "end": "#A83A3A",
                "hover_start": "#E05A5A",
                "hover_end": "#C94A4A",
                "border": "#F08080",
                "text": "#FFFFFF",
            },
            "danger": {
                "start": "#C94A4A",
                "end": "#A83A3A",
                "hover_start": "#E05A5A",
                "hover_end": "#C94A4A",
                "border": "#F08080",
                "text": "#FFFFFF",
            },
        }
        self._variant_palette = palettes.get(self.variant, palettes["primary"])
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
            palette["hover_start"] if hovered or self.isChecked() else palette["start"]
        )
        end = QColor(
            palette["hover_end"] if hovered or self.isChecked() else palette["end"]
        )
        if pressed:
            start = start.darker(112)
            end = end.darker(112)
        if not enabled:
            start = self._disabled_tint(palette["start"], lift=108, alpha=140)
            end = self._disabled_tint(palette["end"], lift=104, alpha=130)

        fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        fill.setColorAt(0.0, start)
        fill.setColorAt(1.0, end)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(fill))
        painter.drawRoundedRect(rect, 10, 10)

        border = QColor(palette["border"])
        if not enabled:
            border.setAlpha(90)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)

        font = self.font()
        font.setPointSize(14)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(
            QColor(palette["text"]) if enabled else QColor(200, 206, 218, 140)
        )
        text_rect = rect.adjusted(0, 1, 0, 1) if pressed else rect
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text())

        if enabled and self.hasFocus():
            painter.setPen(QPen(QColor(74, 144, 232, 130), 1.0))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)


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
