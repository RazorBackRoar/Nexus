"""Keyboard shortcuts reference dialog for Nexus."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from nexus.gui.theme import get_theme_manager


SHORTCUT_SECTIONS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "General",
        [
            ("⌘,", "Preferences"),
            ("⌘/", "Keyboard Shortcuts Sheet"),
            ("⌘D", "Toggle Dark / Light Theme"),
            ("⌘Q", "Quit Nexus"),
        ],
    ),
    (
        "Navigation & Search",
        [
            ("⌘H", "Return to Home (URL Table)"),
            ("⌘F", "Focus Bookmark Search Bar"),
            ("Esc", "Clear Search / Close Dialogs"),
            ("⌘1", "URL Workspace"),
            ("⌘2", "Quick Save View"),
        ],
    ),
    (
        "URL & Safari Operations",
        [
            ("⌘⇧O", "Open All URLs in Safari"),
            ("⌘⇧I", "Import Safari Tabs"),
            ("⌘⇧S", "Quick Save Current URLs"),
            ("⌘⇧C", "Copy Rich Links"),
            ("⌘O", "Import URLs from File"),
            ("⌘E", "Export URLs to File"),
            ("⌘⌫", "Clear URL Table"),
        ],
    ),
    (
        "Bookmarks",
        [
            ("⌘N", "New Bookmark Folder"),
            ("⌘S", "Save Current URLs as Group"),
            ("Delete / ⌫", "Delete Selected Bookmark / Group"),
            ("Return", "Open Selected Item in Safari"),
        ],
    ),
]


class ShortcutsDialog(QDialog):
    """Semi-transparent modal listing keyboard shortcuts grouped by domain."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nexus Keyboard Shortcuts")
        self.setModal(True)
        self.resize(540, 580)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Close on Esc
        esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        esc_shortcut.activated.connect(self.close)

        self._build_ui()
        self._apply_theme()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Title
        header_layout = QHBoxLayout()
        title_label = QLabel("Keyboard Shortcuts")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        close_btn = QPushButton("Done")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        header_layout.addWidget(close_btn)
        main_layout.addLayout(header_layout)

        # Scroll area for sections
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 0)
        container_layout.setSpacing(18)

        for section_title, shortcuts in SHORTCUT_SECTIONS:
            sec_label = QLabel(section_title.upper())
            sec_font = QFont()
            sec_font.setPointSize(11)
            sec_font.setWeight(QFont.Weight.DemiBold)
            sec_label.setFont(sec_font)
            sec_label.setObjectName("sectionHeader")
            container_layout.addWidget(sec_label)

            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(8)
            grid.setContentsMargins(8, 0, 8, 8)

            for row_idx, (key, desc) in enumerate(shortcuts):
                key_badge = QLabel(key)
                key_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                key_badge.setObjectName("keyBadge")
                key_badge.setFixedHeight(26)
                key_badge.setMinimumWidth(80)

                desc_label = QLabel(desc)
                desc_label.setObjectName("descLabel")

                grid.addWidget(key_badge, row_idx, 0)
                grid.addWidget(desc_label, row_idx, 1)

            container_layout.addLayout(grid)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

    def _apply_theme(self) -> None:
        tm = get_theme_manager()
        t = tm.tokens

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {t.frame_bg_start};
                color: {t.text_primary};
            }}
            QLabel {{
                color: {t.text_primary};
            }}
            QLabel#sectionHeader {{
                color: {t.text_accent};
                letter-spacing: 1px;
                padding-top: 4px;
            }}
            QLabel#descLabel {{
                color: {t.text_secondary};
                font-size: 13px;
            }}
            QLabel#keyBadge {{
                background-color: {t.card_bg};
                color: {t.text_primary};
                border: 1px solid {t.card_border};
                border-radius: 6px;
                font-family: -apple-system, BlinkMacSystemFont, "Menlo", monospace;
                font-size: 12px;
                font-weight: bold;
                padding: 2px 8px;
            }}
            QPushButton {{
                background-color: {t.card_bg};
                color: {t.text_primary};
                border: 1px solid {t.card_border};
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {t.card_hover_border};
                background-color: {t.card_selected_bg};
            }}
            QScrollArea {{
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {t.scrollbar_handle};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t.scrollbar_handle_hover};
            }}
            """
        )
