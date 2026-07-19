"""Quick Save panel — chronological bookmark blocks under the Quick Save tab."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def _parse_created_at(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_quick_save_date(created_at: str) -> tuple[str, str]:
    """Return (date_line, time_line) like ('Jan 01 26', '10:23 PM')."""
    dt = _parse_created_at(created_at)
    if dt is None:
        return ("—", "—")
    local = dt.astimezone() if dt.tzinfo is not None else dt
    return (local.strftime("%b %d %y"), local.strftime("%I:%M %p").lstrip("0"))


class QuickSaveBlock(QFrame):
    """One rectangular Quick Save row: Date & Time | Bookmarks | Notes."""

    delete_requested = Signal(str)
    copy_urls_requested = Signal(str)
    load_urls_requested = Signal(str)
    notes_changed = Signal(str, str)

    def __init__(self, entry: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.entry_id = str(entry.get("id") or "")
        self._urls = [str(u) for u in entry.get("urls") or [] if str(u).strip()]
        self.setObjectName("quickSaveBlock")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.setStyleSheet("""
            QFrame#quickSaveBlock {
                background: rgba(18, 22, 32, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 10px;
            }
            QFrame#quickSaveBlock:hover {
                border: 1px solid rgba(255, 255, 255, 0.18);
            }
            QLabel {
                background: transparent;
                color: #E8ECF4;
            }
            QTextEdit {
                background: transparent;
                border: none;
                color: #A8B4C8;
                font-size: 13px;
                padding: 2px;
            }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        date_line, time_line = format_quick_save_date(str(entry.get("created_at") or ""))

        date_col = QWidget()
        date_col.setFixedWidth(108)
        date_layout = QVBoxLayout(date_col)
        date_layout.setContentsMargins(14, 12, 12, 12)
        date_layout.setSpacing(2)
        date_label = QLabel(date_line)
        date_label.setStyleSheet(
            "color: #E8ECF4; font-size: 13px; font-weight: 600;"
        )
        time_label = QLabel(time_line)
        time_label.setStyleSheet("color: #8A95A8; font-size: 12px;")
        date_layout.addWidget(date_label)
        date_layout.addWidget(time_label)
        date_layout.addStretch()
        root.addWidget(date_col)

        root.addWidget(self._vertical_divider())

        bookmarks_col = QWidget()
        bookmarks_layout = QVBoxLayout(bookmarks_col)
        bookmarks_layout.setContentsMargins(14, 12, 12, 12)
        bookmarks_layout.setSpacing(4)
        if self._urls:
            for url in self._urls:
                url_label = QLabel(url)
                url_label.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
                url_label.setWordWrap(True)
                url_label.setStyleSheet(
                    "color: #C8D2E4; font-size: 13px; font-family: Menlo, monospace;"
                )
                bookmarks_layout.addWidget(url_label)
        else:
            empty = QLabel("(no bookmarks)")
            empty.setStyleSheet("color: #6A7890; font-size: 13px;")
            bookmarks_layout.addWidget(empty)
        bookmarks_layout.addStretch()
        root.addWidget(bookmarks_col, 1)

        root.addWidget(self._vertical_divider())

        notes_col = QWidget()
        notes_col.setMinimumWidth(140)
        notes_col.setMaximumWidth(220)
        notes_layout = QVBoxLayout(notes_col)
        notes_layout.setContentsMargins(10, 8, 10, 8)
        notes_layout.setSpacing(0)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add a note…")
        self.notes_edit.setPlainText(str(entry.get("notes") or ""))
        self.notes_edit.setAcceptRichText(False)
        self.notes_edit.setFixedHeight(64)
        self.notes_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        notes_layout.addWidget(self.notes_edit)
        notes_layout.addStretch()
        root.addWidget(notes_col)

        self.setMinimumHeight(78)

    @staticmethod
    def _vertical_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("background: rgba(255, 255, 255, 0.12); border: none;")
        return line

    def _on_notes_changed(self) -> None:
        self.notes_changed.emit(self.entry_id, self.notes_edit.toPlainText())

    def _show_context_menu(self, position) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1C1F27;
                color: #E8ECF4;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(46, 196, 160, 0.28);
                color: #E8ECF4;
            }
        """)
        copy_action = menu.addAction("Copy Bookmarks")
        paste_out_action = menu.addAction("Paste Bookmarks to URL Table")
        menu.addSeparator()
        delete_action = menu.addAction("Delete Block")

        chosen = menu.exec(self.mapToGlobal(position))
        if chosen is copy_action:
            self.copy_urls_requested.emit(self.entry_id)
        elif chosen is paste_out_action:
            self.load_urls_requested.emit(self.entry_id)
        elif chosen is delete_action:
            self.delete_requested.emit(self.entry_id)


class QuickSavePanel(QWidget):
    """Scrollable Quick Save database view with column headers."""

    delete_requested = Signal(str)
    copy_urls_requested = Signal(str)
    load_urls_requested = Signal(str)
    notes_changed = Signal(str, str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("quickSaveHeader")
        header.setStyleSheet("""
            QFrame#quickSaveHeader {
                background: rgba(12, 16, 24, 0.55);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QLabel {
                color: #8A95A8;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.4px;
                background: transparent;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        date_h = QLabel("Date & Time")
        date_h.setFixedWidth(108)
        date_h.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        date_h.setContentsMargins(14, 10, 12, 10)
        header_layout.addWidget(date_h)

        header_layout.addWidget(self._header_divider())

        bookmarks_h = QLabel("Bookmarks")
        bookmarks_h.setContentsMargins(14, 10, 12, 10)
        header_layout.addWidget(bookmarks_h, 1)

        header_layout.addWidget(self._header_divider())

        notes_h = QLabel("Notes")
        notes_h.setMinimumWidth(140)
        notes_h.setMaximumWidth(220)
        notes_h.setContentsMargins(14, 10, 12, 10)
        header_layout.addWidget(notes_h)

        layout.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.16);
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.list_host = QWidget()
        self.list_host.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 2, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        self.scroll_area.setWidget(self.list_host)
        layout.addWidget(self.scroll_area, 1)

        self._empty_label = QLabel(
            "No Quick Saves yet.\nUse Quick Save to capture the current URL list."
        )
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            "color: #6A7890; font-size: 14px; padding: 40px;"
        )
        self._empty_label.setWordWrap(True)
        self.list_layout.insertWidget(0, self._empty_label)

        self._blocks: dict[str, QuickSaveBlock] = {}

    @staticmethod
    def _header_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("background: rgba(255, 255, 255, 0.10); border: none;")
        return line

    def set_entries(self, entries: list[dict[str, Any]]) -> None:
        """Replace all blocks. Entries should already be newest-first."""
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None and widget is not self._empty_label:
                widget.deleteLater()
        self._blocks.clear()

        if not entries:
            self._empty_label.show()
            return

        self._empty_label.hide()
        for entry in entries:
            entry_id = str(entry.get("id") or "")
            if not entry_id:
                continue
            block = QuickSaveBlock(entry)
            block.delete_requested.connect(self.delete_requested.emit)
            block.copy_urls_requested.connect(self.copy_urls_requested.emit)
            block.load_urls_requested.connect(self.load_urls_requested.emit)
            block.notes_changed.connect(self.notes_changed.emit)
            self._blocks[entry_id] = block
            # Insert above the trailing stretch (and empty label if present)
            self.list_layout.insertWidget(self.list_layout.count() - 1, block)

    def copy_entry_urls_to_clipboard(self, entry_id: str) -> list[str]:
        block = self._blocks.get(entry_id)
        if block is None:
            return []
        urls = list(block._urls)
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None and urls:
            clipboard.setText("\n".join(urls))
        return urls
