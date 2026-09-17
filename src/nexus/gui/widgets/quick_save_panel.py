"""Quick Save panel — chronological bookmark blocks under the Quick Save tab with Light and Dark styling."""

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

from nexus.gui.theme import get_theme_manager


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


class ClickableURLLabel(QLabel):
    """Clickable URL label for Quick Save blocks that opens the link on click."""

    url_clicked = Signal(str)

    def __init__(self, url: str, parent: QWidget | None = None) -> None:
        super().__init__(url, parent)
        self.url_text = url
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setWordWrap(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._apply_style()
        get_theme_manager().theme_changed.connect(lambda _: self._apply_style())

    def _apply_style(self):
        is_dark = get_theme_manager().is_dark
        color = "#60A5FA" if is_dark else "#0284C7"
        hover_color = "#93C5FD" if is_dark else "#0369A1"
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                font-family: Menlo, monospace;
            }}
            QLabel:hover {{
                color: {hover_color};
                text-decoration: underline;
            }}
        """)

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.url_clicked.emit(self.url_text)
        super().mousePressEvent(event)


class QuickSaveBlock(QFrame):
    """One rectangular Quick Save row: Date & Time | Bookmarks | Notes & URLs."""

    delete_requested = Signal(str)
    copy_urls_requested = Signal(str)
    load_urls_requested = Signal(str)
    notes_changed = Signal(str, str)
    single_url_activated = Signal(str)
    block_selected = Signal(str)

    def __init__(self, entry: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.entry_id = str(entry.get("id") or "")
        raw_urls = [str(u) for u in entry.get("urls") or [] if str(u).strip()]
        self._urls = sorted(raw_urls, key=lambda s: s.lower())
        self._is_selected = False
        self.setObjectName("quickSaveBlock")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        date_line, time_line = format_quick_save_date(
            str(entry.get("created_at") or "")
        )

        date_col = QWidget()
        date_col.setFixedWidth(108)
        date_layout = QVBoxLayout(date_col)
        date_layout.setContentsMargins(14, 12, 12, 12)
        date_layout.setSpacing(2)
        self.date_label = QLabel(date_line)
        self.time_label = QLabel(time_line)
        date_layout.addWidget(self.date_label)
        date_layout.addWidget(self.time_label)
        date_layout.addStretch()
        root.addWidget(date_col)

        self.divider1 = self._vertical_divider()
        root.addWidget(self.divider1)

        bookmarks_col = QWidget()
        bookmarks_layout = QVBoxLayout(bookmarks_col)
        bookmarks_layout.setContentsMargins(14, 12, 12, 12)
        bookmarks_layout.setSpacing(4)
        if self._urls:
            for url in self._urls:
                url_label = ClickableURLLabel(url)
                url_label.url_clicked.connect(self.single_url_activated.emit)
                bookmarks_layout.addWidget(url_label)
        else:
            self.empty_label = QLabel("(no bookmarks)")
            bookmarks_layout.addWidget(self.empty_label)
        bookmarks_layout.addStretch()
        root.addWidget(bookmarks_col, 1)

        self.divider2 = self._vertical_divider()
        root.addWidget(self.divider2)

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
        self.notes_edit.setFixedHeight(54)
        self.notes_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        notes_layout.addWidget(self.notes_edit)

        url_count = len(self._urls)
        count_str = f"{url_count} URL{'s' if url_count != 1 else ''}"
        self.url_count_badge = QLabel(count_str)
        notes_layout.addWidget(self.url_count_badge)
        notes_layout.addStretch()
        root.addWidget(notes_col)

        self.setMinimumHeight(78)
        self._apply_style()
        get_theme_manager().theme_changed.connect(lambda _: self._apply_style())

    def set_selected(self, selected: bool) -> None:
        if self._is_selected == selected:
            return
        self._is_selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        tm = get_theme_manager()
        is_dark = tm.is_dark

        if self._is_selected:
            if is_dark:
                block_bg = "rgba(46, 196, 160, 0.16)"
                block_border = "2px solid #2EC4A0"
            else:
                block_bg = "rgba(16, 185, 129, 0.14)"
                block_border = "2px solid #059669"
        else:
            if is_dark:
                block_bg = "rgba(18, 22, 32, 0.76)"
                block_border = "1px solid rgba(255, 255, 255, 0.12)"
            else:
                block_bg = "rgba(255, 255, 255, 0.92)"
                block_border = "1px solid rgba(186, 230, 253, 0.85)"

        hover_border = (
            "rgba(56, 189, 248, 0.50)" if is_dark else "rgba(14, 165, 233, 0.85)"
        )
        text_primary = "#F8FAFC" if is_dark else "#032B56"
        text_secondary = "#94A3B8" if is_dark else "#1E5B8E"
        text_badge = "#34D399" if is_dark else "#0284C7"
        divider_color = (
            "rgba(255, 255, 255, 0.12)" if is_dark else "rgba(186, 230, 253, 0.75)"
        )

        self.setStyleSheet(f"""
            QFrame#quickSaveBlock {{
                background: {block_bg};
                border: {block_border};
                border-radius: 10px;
            }}
            QFrame#quickSaveBlock:hover {{
                border: 1px solid {hover_border};
            }}
            QLabel {{
                background: transparent;
                color: {text_primary};
            }}
            QTextEdit {{
                background: transparent;
                border: none;
                color: {text_secondary};
                font-size: 13px;
                padding: 2px;
            }}
        """)

        self.date_label.setStyleSheet(
            f"color: {text_primary}; font-size: 13px; font-weight: 600;"
        )
        self.time_label.setStyleSheet(f"color: {text_secondary}; font-size: 12px;")
        self.url_count_badge.setStyleSheet(
            f"color: {text_badge}; font-size: 12px; font-weight: 600; padding-top: 4px;"
        )
        self.divider1.setStyleSheet(f"background: {divider_color}; border: none;")
        self.divider2.setStyleSheet(f"background: {divider_color}; border: none;")

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton:
            self.block_selected.emit(self.entry_id)
        super().mousePressEvent(event)

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
        is_dark = get_theme_manager().is_dark
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {"#1C1F27" if is_dark else "#FFFFFF"};
                color: {"#E8ECF4" if is_dark else "#0F172A"};
                border: 1px solid {"rgba(255, 255, 255, 0.12)" if is_dark else "rgba(203, 213, 225, 0.85)"};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {"rgba(46, 196, 160, 0.28)" if is_dark else "rgba(16, 185, 129, 0.18)"};
                color: {"#E8ECF4" if is_dark else "#0F172A"};
            }}
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
    """Scrollable Quick Save database view with column headers and smooth performance."""

    delete_requested = Signal(str)
    copy_urls_requested = Signal(str)
    load_urls_requested = Signal(str)
    notes_changed = Signal(str, str)
    single_url_activated = Signal(str)
    selection_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.selected_block_id: str | None = None
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.header = QFrame()
        self.header.setObjectName("quickSaveHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        date_h = QLabel("Date & Time")
        date_h.setFixedWidth(108)
        date_h.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        date_h.setContentsMargins(14, 10, 12, 10)
        header_layout.addWidget(date_h)

        self.hdr_div1 = self._header_divider()
        header_layout.addWidget(self.hdr_div1)

        bookmarks_h = QLabel("Bookmarks")
        bookmarks_h.setContentsMargins(14, 10, 12, 10)
        header_layout.addWidget(bookmarks_h, 1)

        self.hdr_div2 = self._header_divider()
        header_layout.addWidget(self.hdr_div2)

        notes_h = QLabel("Notes • URLs")
        notes_h.setMinimumWidth(140)
        notes_h.setMaximumWidth(220)
        notes_h.setContentsMargins(14, 10, 12, 10)
        header_layout.addWidget(notes_h)

        layout.addWidget(self.header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

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
        self._empty_label.setWordWrap(True)
        self.list_layout.insertWidget(0, self._empty_label)

        self._blocks: dict[str, QuickSaveBlock] = {}
        self._apply_theme()
        get_theme_manager().theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        is_dark = get_theme_manager().is_dark
        tokens = get_theme_manager().tokens
        hdr_bg = "rgba(12, 16, 24, 0.55)" if is_dark else "rgba(241, 245, 249, 0.85)"
        hdr_border = (
            "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(203, 213, 225, 0.65)"
        )
        hdr_text = "#8A95A8" if is_dark else "#475569"
        div_color = (
            "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(203, 213, 225, 0.60)"
        )

        self.header.setStyleSheet(f"""
            QFrame#quickSaveHeader {{
                background: {hdr_bg};
                border: 1px solid {hdr_border};
                border-radius: 8px;
            }}
            QLabel {{
                color: {hdr_text};
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.4px;
                background: transparent;
            }}
        """)
        self.hdr_div1.setStyleSheet(f"background: {div_color}; border: none;")
        self.hdr_div2.setStyleSheet(f"background: {div_color}; border: none;")

        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {tokens.scrollbar_handle};
                border-radius: 3px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {tokens.scrollbar_handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self._empty_label.setStyleSheet(
            f"color: {tokens.text_dim}; font-size: 14px; padding: 40px;"
        )

    @staticmethod
    def _header_divider() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("background: rgba(255, 255, 255, 0.10); border: none;")
        return line

    def select_block(self, entry_id: str) -> None:
        self.selected_block_id = entry_id
        for eid, block in self._blocks.items():
            block.set_selected(eid == entry_id)
        self.selection_changed.emit(entry_id)

    def get_selected_urls(self) -> list[str]:
        if self.selected_block_id and self.selected_block_id in self._blocks:
            return list(self._blocks[self.selected_block_id]._urls)
        return []

    def set_entries(self, entries: list[dict[str, Any]]) -> None:
        """Replace all blocks with batched updates to prevent UI stutter."""
        self.setUpdatesEnabled(False)
        try:
            while self.list_layout.count() > 1:
                item = self.list_layout.takeAt(0)
                if item is None:
                    continue
                widget = item.widget()
                if widget is not None and widget is not self._empty_label:
                    widget.deleteLater()
            self._blocks.clear()
            self.selected_block_id = None

            if not entries:
                self._empty_label.show()
                return

            self._empty_label.hide()
            for entry in entries:
                entry_id = str(entry.get("id") or "")
                if not entry_id:
                    continue
                block = QuickSaveBlock(entry)
                block.block_selected.connect(self.select_block)
                block.delete_requested.connect(self.delete_requested.emit)
                block.copy_urls_requested.connect(self.copy_urls_requested.emit)
                block.load_urls_requested.connect(self.load_urls_requested.emit)
                block.notes_changed.connect(self.notes_changed.emit)
                block.single_url_activated.connect(self.single_url_activated.emit)
                self._blocks[entry_id] = block
                self.list_layout.insertWidget(self.list_layout.count() - 1, block)
        finally:
            self.setUpdatesEnabled(True)

    def copy_entry_urls_to_clipboard(self, entry_id: str) -> list[str]:
        block = self._blocks.get(entry_id)
        if block is None:
            return []
        urls = list(block._urls)
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None and urls:
            clipboard.setText("\n".join(urls))
        return urls
