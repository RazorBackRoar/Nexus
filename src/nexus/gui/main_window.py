"""Main Application Window for Nexus."""

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import (
    QByteArray,
    QEvent,
    QSettings,
    QStandardPaths,
    Qt,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexus.core.bookmarks import DEFAULT_BOOKMARK_FOLDER_NAMES, BookmarkManager
from nexus.core.config import Config, cleanup_logs, logger, privacy_fingerprint
from nexus.core.models import Bookmark, BookmarkFolder, BookmarkNode
from nexus.core.safari import SafariController
from nexus.gui.widgets import (
    AsyncWorker,
    BookmarkTreeDelegate,
    CosmicFrame,
    GlassButton,
    URLTableWidget,
    WindowTitleBar,
)
from nexus.utils.url_processor import URLProcessor
from razorcore.appinfo import AboutDialog
from razorcore.updates import check_for_updates


class MainWindow(QMainWindow):
    """The main application window with hierarchical bookmark support."""

    APP_NAME = Config.APP_NAME

    def __init__(self):
        """Initialize with default theme."""
        super().__init__()
        self._setup_themes()  # Define themes
        self.settings = QSettings()
        self.restored_window_geometry = False
        self._load_settings()  # Load saved theme or default
        self.private_mode_enabled = Config.DEFAULT_PRIVATE_MODE
        self._url_history: list[list[str]] = []
        self._current_url_snapshot: list[str] = []
        self._restoring_url_history = False

        self.url_processor = URLProcessor()
        self.safari_controller = SafariController()

        app_data_dir = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        self.bookmark_manager = BookmarkManager(app_data_dir / Config.BOOKMARKS_FILE)

        self._setup_window()
        self._load_window_state()  # Load window geometry/state
        self._setup_ui()  # Setup UI components
        self.load_bookmarks()  # Load bookmarks into the tree
        self._apply_theme()  # Apply theme after all UI is set up

        logger.info(
            "MainWindow initialized successfully with hierarchical bookmark support."
        )

    def _setup_themes(self):
        """Defines muted dark color themes (3 accents per main tab)."""
        self.themes = {
            "Midnight Blue": {
                "safari": {
                    "primary": "#4A8FC0",
                    "secondary": "#3A6F98",
                    "accent": "#C45A5A",
                },
                "bookmarks": {
                    "primary": "#6B5B95",
                    "secondary": "#534670",
                    "accent": "#5BA86A",
                },
                "theme_settings": {
                    "primary": "#4A8FC0",
                    "secondary": "#6B5B95",
                    "accent": "#C4A84A",
                },
            },
            "Rose": {
                "safari": {
                    "primary": "#C45A8A",
                    "secondary": "#9A456C",
                    "accent": "#5BA86A",
                },
                "bookmarks": {
                    "primary": "#7A6BB0",
                    "secondary": "#5C5085",
                    "accent": "#C4A84A",
                },
                "theme_settings": {
                    "primary": "#C45A8A",
                    "secondary": "#7A6BB0",
                    "accent": "#5BA86A",
                },
            },
            "Forest": {
                "safari": {
                    "primary": "#5BA86A",
                    "secondary": "#458054",
                    "accent": "#C4711A",
                },
                "bookmarks": {
                    "primary": "#C4A84A",
                    "secondary": "#9A8238",
                    "accent": "#C45A8A",
                },
                "theme_settings": {
                    "primary": "#5BA86A",
                    "secondary": "#C4A84A",
                    "accent": "#4A8FC0",
                },
            },
            "Violet": {
                "safari": {
                    "primary": "#7A6BB0",
                    "secondary": "#5C5085",
                    "accent": "#C4A84A",
                },
                "bookmarks": {
                    "primary": "#4A8FC0",
                    "secondary": "#3A6F98",
                    "accent": "#C45A5A",
                },
                "theme_settings": {
                    "primary": "#7A6BB0",
                    "secondary": "#C45A8A",
                    "accent": "#5BA86A",
                },
            },
            "Ember": {
                "safari": {
                    "primary": "#C4711A",
                    "secondary": "#9A5814",
                    "accent": "#4A8FC0",
                },
                "bookmarks": {
                    "primary": "#C45A8A",
                    "secondary": "#9A456C",
                    "accent": "#5BA86A",
                },
                "theme_settings": {
                    "primary": "#C4711A",
                    "secondary": "#C45A8A",
                    "accent": "#7A6BB0",
                },
            },
        }

    def _load_settings(self):
        """Loads theme settings from QSettings."""
        default_theme_name = "Midnight Blue"
        default_theme_colors = self.themes[default_theme_name]

        saved_name = self.settings.value("theme/name", default_theme_name)
        # Migrate legacy neon theme names to muted equivalents
        legacy_theme_map = {
            "Neon Blue": "Midnight Blue",
            "Hot Pink": "Rose",
            "Cyber Green": "Forest",
            "Electric Purple": "Violet",
            "Sunset Orange": "Ember",
        }
        self.current_theme_name = legacy_theme_map.get(saved_name, saved_name)
        if self.current_theme_name not in self.themes:
            self.current_theme_name = default_theme_name
        if saved_name != self.current_theme_name:
            self.settings.setValue("theme/name", self.current_theme_name)

        # Initialize current_theme with default structure
        self.current_theme = {
            "safari": {
                "primary": "#4A8FC0",
                "secondary": "#3A6F98",
                "accent": "#C45A5A",
            },
            "bookmarks": {
                "primary": "#6B5B95",
                "secondary": "#534670",
                "accent": "#5BA86A",
            },
            "theme_settings": {
                "primary": "#4A8FC0",
                "secondary": "#6B5B95",
                "accent": "#C4A84A",
            },
        }

        if self.current_theme_name == "Custom":
            for tab_key in ["safari", "bookmarks", "theme_settings"]:
                for color_key in ["primary", "secondary", "accent"]:
                    default_val = default_theme_colors.get(tab_key, {}).get(
                        color_key, "#ffffff"
                    )
                    self.current_theme[tab_key][color_key] = str(
                        self.settings.value(
                            f"theme/custom_{tab_key}_{color_key}", default_val
                        )
                    )
        else:
            # Load preset colors and save them as custom for editing
            theme_name = str(self.current_theme_name)
            preset_colors_raw = self.themes.get(theme_name, default_theme_colors)
            preset_colors: dict[str, Any] = (
                preset_colors_raw
                if isinstance(preset_colors_raw, dict)
                else default_theme_colors
            )
            for tab_key in ["safari", "bookmarks", "theme_settings"]:
                for color_key in ["primary", "secondary", "accent"]:
                    tab_colors = preset_colors.get(tab_key, {})
                    color_val = (
                        tab_colors.get(color_key, "#ffffff")
                        if isinstance(tab_colors, dict)
                        else "#ffffff"
                    )
                    self.current_theme[tab_key][color_key] = color_val
                    self.settings.setValue(
                        f"theme/custom_{tab_key}_{color_key}", color_val
                    )

    def _setup_window(self):
        """Sets up the main window properties for the cosmic glass shell."""
        self.setWindowTitle("Nexus")  # Set title for Dock
        self.setMinimumSize(1220, 760)
        self.resize(1240, 780)
        if sys.platform == "darwin":
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
                border: none;
            }
        """)

    def _setup_ui(self):
        """Sets up the single-frame Nexus UI inspired by the provided reference."""
        central_widget = QWidget()
        central_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        central_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.chrome_frame = CosmicFrame()
        root_layout.addWidget(self.chrome_frame)

        main_layout = QVBoxLayout(self.chrome_frame)
        main_layout.setContentsMargins(22, 6, 22, 16)
        main_layout.setSpacing(10)

        if sys.platform == "darwin":
            self.window_titlebar = WindowTitleBar(self, "Nexus")
            main_layout.addWidget(self.window_titlebar)

        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 4, 0, 0)
        header_layout.setSpacing(6)

        self.title_label = QLabel("Nexus")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setToolTip("Double-click for About · Right-click for updates")
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.title_label.customContextMenuRequested.connect(
            self._show_title_context_menu
        )
        self.title_label.installEventFilter(self)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #F0F4FA;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 42px;
                font-weight: 700;
                letter-spacing: 1.2px;
                padding-bottom: 0px;
            }
        """)
        header_layout.addWidget(self.title_label)

        self.summary_label = QLabel(
            "Safari bookmark manager and batch URL opener — paste links, organize folders, open everything at once."
        )
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("""
            QLabel {
                color: #9AA8BC;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 15px;
                font-weight: 400;
                letter-spacing: 0.2px;
                padding-left: 48px;
                padding-right: 48px;
                padding-bottom: 4px;
            }
        """)
        header_layout.addWidget(self.summary_label)
        main_layout.addWidget(header_widget)

        header_rule = QFrame()
        header_rule.setFixedHeight(2)
        header_rule.setStyleSheet(
            """
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(74, 144, 232, 0.0),
                stop:0.18 rgba(74, 144, 232, 0.55),
                stop:0.50 rgba(61, 184, 138, 0.50),
                stop:0.82 rgba(224, 90, 90, 0.55),
                stop:1 rgba(224, 90, 90, 0.0));
            border: none;
            border-radius: 1px;
            """
        )
        main_layout.addWidget(header_rule)

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(22)

        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(260)
        self.sidebar.setObjectName("bookmarkSidebar")
        self.sidebar.setStyleSheet("""
            QWidget#bookmarkSidebar {
                background: rgba(255, 255, 255, 0.035);
                border-right: 1px solid rgba(74, 144, 232, 0.18);
                border-radius: 0px;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 14, 12)
        sidebar_layout.setSpacing(14)

        sidebar_header = QWidget()
        sidebar_header_layout = QHBoxLayout(sidebar_header)
        sidebar_header_layout.setContentsMargins(4, 0, 4, 0)
        sidebar_header_layout.setSpacing(4)

        sidebar_title = QLabel("Bookmarks")
        sidebar_title.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        sidebar_title.setStyleSheet("""
            QLabel {
                color: #B8C4D6;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 0.5px;
                padding-left: 4px;
                padding-bottom: 2px;
            }
        """)
        sidebar_header_layout.addWidget(sidebar_title, 1)

        self.add_folder_btn = QPushButton("+")
        self.add_folder_btn.clicked.connect(self.add_bookmark_section)
        self.add_folder_btn.setFixedSize(26, 26)
        self.add_folder_btn.setToolTip("Add folder")
        self.add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_folder_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_folder_btn.setStyleSheet("""
            QPushButton {
                background: rgba(74, 144, 232, 0.16);
                border: 1px solid rgba(74, 144, 232, 0.35);
                border-radius: 7px;
                color: #D6E4FF;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 18px;
                font-weight: 500;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: rgba(74, 144, 232, 0.28);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(74, 144, 232, 0.12);
            }
        """)
        sidebar_header_layout.addWidget(
            self.add_folder_btn,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        sidebar_layout.addWidget(sidebar_header)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter bookmarks")
        self.search_bar.textChanged.connect(self._filter_bookmarks)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: rgba(0, 0, 0, 0.30);
                border: 1px solid rgba(74, 144, 232, 0.22);
                border-radius: 9px;
                color: #E8ECF4;
                padding: 9px 14px;
                font-size: 14px;
                font-family: "Helvetica Neue", sans-serif;
                selection-background-color: rgba(74, 144, 232, 0.40);
            }
            QLineEdit:focus {
                border: 1px solid rgba(61, 184, 138, 0.55);
                background: rgba(0, 0, 0, 0.38);
            }
            QLineEdit::placeholder {
                color: rgba(168, 176, 192, 0.70);
            }
        """)
        self.search_bar.setFixedHeight(38)
        sidebar_layout.addWidget(self.search_bar)

        self.bookmark_tree = QTreeWidget()
        self.bookmark_tree.setHeaderHidden(True)
        self.bookmark_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bookmark_tree.customContextMenuRequested.connect(
            self._show_bookmark_context_menu
        )
        self.bookmark_tree.itemDoubleClicked.connect(self._handle_item_double_click)
        self.bookmark_tree.setRootIsDecorated(False)
        self.bookmark_tree.setItemsExpandable(True)
        self.bookmark_tree.setIndentation(0)
        self.bookmark_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bookmark_tree.setMouseTracking(True)
        self.bookmark_tree.setItemDelegate(BookmarkTreeDelegate(self.bookmark_tree))
        self.bookmark_tree.setStyleSheet("""
            QTreeWidget {
                background: transparent;
                border: none;
                outline: none;
                color: transparent;
            }
            QTreeWidget::item {
                padding: 0px;
                margin: 0px;
                border: none;
                background: transparent;
            }
            QTreeWidget::branch {
                image: none;
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.16);
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.26);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        sidebar_layout.addWidget(self.bookmark_tree, 1)

        content_layout.addWidget(self.sidebar)

        main_content = QWidget()
        main_content.setStyleSheet("background: transparent;")
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(4, 12, 0, 0)
        main_content_layout.setSpacing(12)

        tagline = QLabel("Paste URLs. Open in Safari.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignLeft)
        tagline.setStyleSheet("""
            QLabel {
                color: #7EB8F0;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 16px;
                font-weight: 550;
                letter-spacing: 0.2px;
                padding-bottom: 2px;
            }
        """)
        main_content_layout.addWidget(tagline)

        url_panel = QWidget()
        url_panel.setObjectName("urlWell")
        url_panel.setStyleSheet("""
            QWidget#urlWell {
                background: rgba(0, 0, 0, 0.24);
                border: 1px solid rgba(74, 144, 232, 0.20);
                border-radius: 12px;
            }
        """)
        url_panel_layout = QVBoxLayout(url_panel)
        url_panel_layout.setContentsMargins(14, 14, 14, 12)
        url_panel_layout.setSpacing(8)

        self.url_table = URLTableWidget()
        self.url_table.itemChanged.connect(self._update_url_counter)
        self.url_table.model().rowsInserted.connect(self._update_url_counter)
        self.url_table.model().rowsRemoved.connect(self._update_url_counter)
        self.url_table.url_activated.connect(self._open_single_url)
        self.url_table.urls_changed.connect(self._on_urls_changed)
        self.url_table.setToolTip("Double-click a URL row to open it in Safari")
        self.url_table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: none;
                color: #E8ECF4;
                font-size: 15px;
                outline: none;
                selection-background-color: transparent;
            }
            QTableWidget::item {
                padding: 0px;
                border: none;
                background: transparent;
            }
            QTableWidget QLineEdit {
                background: transparent;
                border: none;
                color: #E8ECF4;
                padding-left: 16px;
                font-size: 15px;
                selection-background-color: rgba(74, 144, 232, 0.40);
            }
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
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.26);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self.url_empty_state = QWidget()
        self.url_empty_state.setStyleSheet("background: transparent;")
        empty_layout = QVBoxLayout(self.url_empty_state)
        empty_layout.setContentsMargins(28, 28, 28, 28)
        empty_layout.setSpacing(10)
        empty_layout.addStretch()

        self.url_empty_title = QLabel("Paste URLs to get started")
        self.url_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.url_empty_title.setStyleSheet("""
            QLabel {
                color: #E8ECF4;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 20px;
                font-weight: 600;
                letter-spacing: 0.2px;
            }
        """)
        empty_layout.addWidget(self.url_empty_title)

        self.url_empty_note = QLabel(
            "Copied links appear here automatically. Each row shows Ready, Opening, or Failed."
        )
        self.url_empty_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.url_empty_note.setWordWrap(True)
        self.url_empty_note.setStyleSheet("""
            QLabel {
                color: #8A96A8;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 15px;
                font-weight: 400;
                padding-left: 40px;
                padding-right: 40px;
            }
        """)
        empty_layout.addWidget(self.url_empty_note)
        empty_layout.addStretch()

        self.url_stack_host = QWidget()
        self.url_stack = QStackedLayout(self.url_stack_host)
        self.url_stack.setContentsMargins(0, 0, 0, 0)
        self.url_stack.addWidget(self.url_empty_state)
        self.url_stack.addWidget(self.url_table)
        url_panel_layout.addWidget(self.url_stack_host, 1)
        main_content_layout.addWidget(url_panel, 1)

        self.url_counter_label = QLabel("0 URLs ready")
        self.url_counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.url_counter_label.setStyleSheet("""
            QLabel {
                color: #3DB88A;
                font-size: 13px;
                font-weight: 550;
                letter-spacing: 0.2px;
                padding-top: 2px;
                padding-right: 4px;
            }
        """)
        main_content_layout.addWidget(self.url_counter_label)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(8, 6, 8, 2)
        button_row.setSpacing(28)

        self.run_btn = GlassButton("Open All", "primary")
        self.run_btn.clicked.connect(self._run_urls_in_safari)

        self.save_btn = GlassButton("Save", "secondary")
        self.save_btn.clicked.connect(self._save_urls_to_bookmarks)

        self.undo_btn = GlassButton("Undo", "tertiary")
        self.undo_btn.clicked.connect(self._undo_url_change)
        self.undo_btn.setEnabled(False)

        self.clear_btn = GlassButton("Clear", "quaternary")
        self.clear_btn.clicked.connect(self._clear_all_data)
        for button in (
            self.run_btn,
            self.save_btn,
            self.undo_btn,
            self.clear_btn,
        ):
            button.setFixedSize(148, 46)

        button_row.addStretch()
        button_row.addWidget(self.run_btn)
        button_row.addWidget(self.save_btn)
        button_row.addWidget(self.undo_btn)
        button_row.addWidget(self.clear_btn)
        button_row.addStretch()
        main_content_layout.addLayout(button_row)

        content_layout.addWidget(main_content, 1)
        main_layout.addWidget(content_widget, 1)

        self.status_bar = QLabel("Ready")
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_bar.setStyleSheet("""
            QLabel {
                color: #6A7890;
                font-size: 12px;
                padding-right: 4px;
            }
        """)
        main_layout.addWidget(self.status_bar)

        self.safari_panel = main_content
        self.bookmarks_panel = self.sidebar
        self.settings_panel = None
        self.safari_title = self.title_label
        self.bookmarks_title = sidebar_title
        self.organize_btn = None
        self.add_link_btn = None
        self.export_btn = None
        self._current_url_snapshot = self.url_table.get_all_urls()
        self._update_url_empty_state()
        self._update_url_counter()

    def _update_undo_button_state(self):
        if hasattr(self, "undo_btn"):
            self.undo_btn.setEnabled(bool(self._url_history))

    def _update_url_empty_state(self):
        """Swap between the empty-state message and the real URL table."""
        has_urls = self.url_table.rowCount() > 0
        if hasattr(self, "url_stack"):
            self.url_stack.setCurrentWidget(
                self.url_table if has_urls else self.url_empty_state
            )
        if hasattr(self, "run_btn"):
            self.run_btn.setEnabled(has_urls)
        if hasattr(self, "save_btn"):
            self.save_btn.setEnabled(has_urls)
        if hasattr(self, "clear_btn"):
            self.clear_btn.setEnabled(has_urls)
        self._update_undo_button_state()

    def _populate_safari_tab(
        self, tab_widget: QWidget
    ):  # Legacy - kept for compatibility
        """Legacy method - functionality moved to _setup_ui."""
        pass

    def _populate_bookmarks_tab(
        self, tab_widget: QWidget
    ):  # Legacy - kept for compatibility
        """Legacy method - functionality moved to _setup_ui."""
        pass

    def _populate_settings_tab(
        self, tab_widget: QWidget
    ):  # Legacy - kept for compatibility
        """Legacy method - settings accessible via menu/dialog now."""
        pass

    def _apply_theme(self):
        """Glass Noir theme is static - no dynamic theming needed."""
        # The Glass Noir design uses fixed colors defined inline in _setup_ui
        # This method is kept for compatibility but does nothing significant
        pass

    def _run_urls_in_safari(self):
        """Runs URLs from the table in Safari with status tracking and privacy settings."""
        urls = self.url_table.get_all_urls()
        if urls:
            for row in range(self.url_table.rowCount()):
                self.url_table.set_status_state(row, "opening")

            self.worker = AsyncWorker(
                self._open_urls_with_tracking, urls, self.private_mode_enabled
            )
            self.worker.result_ready.connect(
                lambda success: self._on_safari_operation_complete(success, len(urls))
            )
            self.worker.error.connect(
                lambda err: self._show_message(
                    f"Error launching URLs: {err}", "warning"
                )
            )
            self.worker.start()
        else:
            self._show_message("No URLs found to launch.", "warning")

    def _open_single_url(self, row: int, url: str):
        """Open one URL from the list when a row is activated."""
        if not url:
            return
        self.url_table.set_status_state(row, "opening")
        self.worker = AsyncWorker(
            self._open_single_url_with_tracking,
            row,
            url,
            self.private_mode_enabled,
        )
        self.worker.result_ready.connect(self._on_single_url_operation_complete)
        self.worker.error.connect(lambda err: self._handle_single_url_error(row, err))
        self.worker.start()

    async def _open_single_url_with_tracking(
        self, row: int, url: str, private_mode: bool = True
    ) -> tuple[int, bool]:
        """Open a single URL and keep row-level status intact."""
        try:
            success = await self.safari_controller.open_urls(
                [url], private_mode=private_mode
            )
            return row, success
        except (TimeoutError, OSError) as e:
            logger.error(
                "Error opening %s: %s",
                privacy_fingerprint(url, "url"),
                e,
            )
            return row, False

    def _on_single_url_operation_complete(self, result: tuple[int, bool]):
        """Update row state after a single URL finishes opening."""
        row, success = result
        self.url_table.update_status(row, success)

    def _handle_single_url_error(self, row: int, err: str):
        self.url_table.update_status(row, False)
        self._show_message(f"Error launching URL: {err}", "warning")

    async def _open_urls_with_tracking(
        self, urls: list[str], private_mode: bool = True
    ) -> bool:
        """Opens URLs in Safari and tracks success/failure with privacy settings."""
        try:
            # Use the SafariController with privacy settings
            success = await self.safari_controller.open_urls(
                urls, private_mode=private_mode
            )

            # Update status for all URLs based on overall success
            for row in range(self.url_table.rowCount()):
                self.url_table.update_status(row, success)

            return success
        except (TimeoutError, OSError) as e:
            logger.error("Error in URL tracking: %s", e)
            # Mark all as failed on error
            for row in range(self.url_table.rowCount()):
                self.url_table.update_status(row, False)
            return False

    def _on_safari_operation_complete(self, success: bool, url_count: int):
        """Called when Safari operation completes."""
        # Don't show popup message to avoid dock bouncing
        logger.info(
            f"Safari operation completed: {url_count} URLs processed, success: {success}"
        )

    def _save_urls_to_bookmarks(self):
        """Auto-categorizes URLs by domain and saves them to bookmarks."""
        urls = self.url_table.get_all_urls()
        if not urls:
            self._show_message("No valid URLs found to save.", "warning")
            return

        domain_groups = {}
        for url in urls:
            try:
                domain = urlparse(url).netloc.replace("www.", "")
                domain_groups.setdefault(domain, []).append(url)
            except Exception:
                domain_groups.setdefault("Other", []).append(url)

        for domain, domain_urls in domain_groups.items():
            folder_name = domain.capitalize()
            folder_item = self._find_or_create_folder(folder_name)
            for url in domain_urls:
                bookmark_data = {
                    "name": self._generate_bookmark_name(url),
                    "type": "bookmark",
                    "url": url,
                }
                self._create_tree_item(bookmark_data, folder_item)
            folder_item.setExpanded(True)

        self.save_bookmarks()
        # self.tabs.setCurrentIndex(1)  # Switch to Bookmarks tab
        self._show_message(
            f"Successfully saved {len(urls)} URLs organized by domain!", "info"
        )

    def _filter_bookmarks(self, text: str):
        """Filters the bookmark tree based on search text."""
        search_text = text.lower().strip()
        root = self.bookmark_tree.invisibleRootItem()

        for i in range(root.childCount()):
            folder_item = root.child(i)
            folder_matches = search_text in folder_item.text(0).lower()
            folder_has_visible_children = False

            # Check children
            for j in range(folder_item.childCount()):
                bookmark_item = folder_item.child(j)
                bookmark_matches = False

                bookmark_data = bookmark_item.data(0, Qt.ItemDataRole.UserRole)
                if bookmark_data:
                    name = bookmark_data.get("name", "").lower()
                    url = bookmark_data.get("url", "").lower()

                    if search_text in name or search_text in url:
                        bookmark_matches = True

                # Show bookmark if:
                # 1. Search is empty (handled by setHidden check later, but here logic is specific)
                # 2. Bookmark matches
                # 3. Parent folder matches (show all content of matched folder)
                should_show_bookmark = (
                    bookmark_matches or folder_matches or (search_text == "")
                )

                bookmark_item.setHidden(not should_show_bookmark)

                if should_show_bookmark:
                    folder_has_visible_children = True

            # Show folder if:
            # 1. Search is empty
            # 2. Folder matches
            # 3. Folder has visible children
            should_show_folder = (
                folder_matches or folder_has_visible_children or (search_text == "")
            )
            folder_item.setHidden(not should_show_folder)

            # Expand folder if we are searching and it is visible
            if search_text and should_show_folder:
                folder_item.setExpanded(True)

    def _organize_urls_in_input(self):  # NEW method
        """Extracts, cleans, sorts, and reformats URLs in the table."""
        urls = self.url_table.get_all_urls()
        if not urls:
            self._show_message("No URLs found to organize.", "warning")
            return

        # Clear and re-add URLs (this will clean and sort them)
        cleaned_urls = []
        for url in urls:
            processed = self.url_processor._normalize_url(url)
            if processed:
                cleaned_urls.append(processed)

        # Sort URLs alphabetically
        cleaned_urls.sort()

        # Clear table and re-add organized URLs
        self.url_table.clear_table()
        self.url_table.add_urls(cleaned_urls)

        logger.info("Organized %d URLs in the table.", len(cleaned_urls))

    def _show_warning_message(self, message: str):
        """Shows a warning message box with theme styling."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Warning")
        msg.setText(message)
        msg.setStyleSheet(
            f"""
            QMessageBox {{
                background: #1e1e1e;
                color: #fff;
            }}
            QMessageBox QPushButton {{
                background: {self.current_theme["safari"]["accent"]}; # Use accent from safari tab
                color: #d0d0d0;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
        """
        )
        msg.exec()

    def _update_url_counter(self):
        """Updates the URL counter label based on table contents."""
        count = self.url_table.rowCount()
        if count == 0:
            self.url_counter_label.setText("Waiting for pasted URLs")
        else:
            self.url_counter_label.setText(
                f"{count} URL{'s' if count != 1 else ''} ready"
            )

    def _track_url_history(self, urls: list[str]):
        """Track URL list mutations so the Undo action can restore the prior state."""
        if self._restoring_url_history:
            self._current_url_snapshot = urls.copy()
            self._update_undo_button_state()
            return
        if urls == self._current_url_snapshot:
            return
        self._url_history.append(self._current_url_snapshot.copy())
        self._url_history = self._url_history[-20:]
        self._current_url_snapshot = urls.copy()
        self._update_undo_button_state()

    def _on_urls_changed(self, urls: list[str]):
        """Refresh derived UI state after the URL list changes."""
        self._track_url_history(urls)
        self._update_url_empty_state()
        self._update_url_counter()

    def _undo_url_change(self):
        """Restore the previous URL list state."""
        if not self._url_history:
            return
        previous_urls = self._url_history.pop()
        self._restoring_url_history = True
        try:
            self.url_table.replace_urls(previous_urls)
        finally:
            self._restoring_url_history = False
        self._current_url_snapshot = previous_urls.copy()
        self._update_undo_button_state()

    def _find_or_create_folder(self, folder_name: str) -> QTreeWidgetItem:
        """Finds an existing folder in the tree or creates a new one."""
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if (
                data
                and data.get("type") == "folder"
                and data.get("name") == folder_name
            ):
                return item

        folder_data = {"name": folder_name, "type": "folder", "children": []}
        return self._create_tree_item(folder_data)

    def _resolve_folder_style(self, folder_name: str) -> dict[str, str]:
        """Return a stable accent color for a bookmark folder row."""
        named_styles = {
            "favorites": {
                "start": "#E5738A",
                "end": "#3D081E",
                "border": "#E8A5C2",
                "icon": "#FFE7F0",
            },
            "tech": {
                "start": "#5B8DEF",
                "end": "#082A56",
                "border": "#94D5FF",
                "icon": "#E6FCFF",
            },
            "misc": {
                "start": "#9B7AE8",
                "end": "#23074F",
                "border": "#D6B1FF",
                "icon": "#F6E9FF",
            },
            "work": {
                "start": "#4DB6A0",
                "end": "#072F2A",
                "border": "#9DE9D8",
                "icon": "#EDFFF9",
            },
            "later": {
                "start": "#D4A05A",
                "end": "#492403",
                "border": "#F0C88F",
                "icon": "#FFF4D0",
            },
            "news": {
                "start": "#6B9AF5",
                "end": "#10235D",
                "border": "#AFC7FF",
                "icon": "#EEF5FF",
            },
            "reading": {
                "start": "#A8B0C0",
                "end": "#717AA8",
                "border": "#F3F5FF",
                "icon": "#FFFFFF",
            },
            "apple": {
                "start": "#7AB8E8",
                "end": "#2767C7",
                "border": "#C1E5FF",
                "icon": "#EAF7FF",
            },
            "google": {
                "start": "#5BC4B0",
                "end": "#238B8A",
                "border": "#C7FFF5",
                "icon": "#EBFFFB",
            },
            "github": {
                "start": "#8B7AE8",
                "end": "#4720BE",
                "border": "#D1C9FF",
                "icon": "#EEEBFF",
            },
            "fun": {
                "start": "#D48BC8",
                "end": "#A11BB7",
                "border": "#FFC7F2",
                "icon": "#FFEAFB",
            },
            "personal": {
                "start": "#6B9AF5",
                "end": "#265CB2",
                "border": "#BADEFF",
                "icon": "#DFF0FF",
            },
            "youtube": {
                "start": "#E57373",
                "end": "#8A203A",
                "border": "#FFB8C4",
                "icon": "#FFE2E7",
            },
            "guides": {
                "start": "#D4A05A",
                "end": "#945F1E",
                "border": "#FFE0A7",
                "icon": "#FFF1D8",
            },
            "random": {
                "start": "#5BC4A8",
                "end": "#2F6B58",
                "border": "#C2F4E4",
                "icon": "#E3FFF6",
            },
        }
        fallback_styles = [
            {
                "start": "#5B8DEF",
                "end": "#092B59",
                "border": "#9AD4FF",
                "icon": "#E8F7FF",
            },
            {
                "start": "#9B7AE8",
                "end": "#250854",
                "border": "#D6B5FF",
                "icon": "#F3E8FF",
            },
            {
                "start": "#4DB6A0",
                "end": "#07312B",
                "border": "#9CE8D8",
                "icon": "#ECFFF8",
            },
            {
                "start": "#E5738A",
                "end": "#3E081F",
                "border": "#EAB0C9",
                "icon": "#FFE5EF",
            },
            {
                "start": "#D4A05A",
                "end": "#4A2603",
                "border": "#F0CB93",
                "icon": "#FFF5D7",
            },
            {
                "start": "#6B9AF5",
                "end": "#162B67",
                "border": "#B5C5FF",
                "icon": "#F1F3FF",
            },
        ]

        normalized = folder_name.lower()
        if normalized in named_styles:
            return named_styles[normalized]

        if not hasattr(self, "_folder_style_cache"):
            self._folder_style_cache = {}

        if normalized not in self._folder_style_cache:
            index = len(self._folder_style_cache) % len(fallback_styles)
            self._folder_style_cache[normalized] = fallback_styles[index]

        return self._folder_style_cache[normalized]

    def _generate_bookmark_name(self, url: str) -> str:
        """Generates a readable name from a URL."""
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            path = urlparse(url).path.strip("/")
            if path and len(path) < 30:
                return f"{domain.capitalize()} - {path.replace('/', ' ').title()}"
            else:
                return domain.capitalize()
        except Exception:
            return "Bookmark"

    def _handle_item_double_click(self, item: QTreeWidgetItem, column: int):
        """Handles double-clicking on a bookmark or folder item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        if data.get("type") == "bookmark":
            self._open_bookmark_link(item)
        elif data.get("type") == "folder":
            item.setExpanded(not item.isExpanded())

    def _on_bookmarks_reordered(self):
        """Called when bookmarks are reordered via drag & drop. Saves the new order."""
        self._sync_tree_to_data()
        self.bookmark_manager.save_bookmarks(self.bookmarks)
        logger.info("Bookmarks reordered and saved.")

    def _sync_tree_to_data(self):
        """Rebuilds self.bookmarks from the current tree widget state."""

        def item_to_node(item: QTreeWidgetItem) -> BookmarkNode:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data.get("type") == "folder":
                children = []
                for i in range(item.childCount()):
                    children.append(item_to_node(item.child(i)))
                return BookmarkFolder(name=data["name"], children=children)
            else:
                return Bookmark(name=data["name"], url=data.get("url", ""))

        self.bookmarks = []
        for i in range(self.bookmark_tree.topLevelItemCount()):
            top_level_item = self.bookmark_tree.topLevelItem(i)
            if top_level_item is None:
                continue
            self.bookmarks.append(item_to_node(top_level_item))

    def _get_selected_parent_item(self) -> QTreeWidgetItem | None:
        """Returns the currently selected folder item, or its parent if a bookmark is selected."""
        current_item = self.bookmark_tree.currentItem()
        if not current_item:
            return None
        data = current_item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "folder":
            return current_item
        else:
            return current_item.parent()

    def add_bookmark_section(self):
        """Prompts for a new folder name and adds it to the tree."""
        parent_item = self._get_selected_parent_item()
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            folder_data = {"name": name.strip(), "type": "folder", "children": []}
            section_item = self._create_tree_item(folder_data, parent_item)
            if parent_item:
                parent_item.setExpanded(True)
            else:
                self.bookmark_tree.addTopLevelItem(section_item)
            self.save_bookmarks()

    def _create_tree_item(
        self, data: dict[str, Any], parent: QTreeWidgetItem | None = None
    ) -> QTreeWidgetItem:
        """Recursive helper to build the visual tree from data."""
        is_folder = data.get("type") == "folder"
        item = QTreeWidgetItem([data["name"]])
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        if is_folder:
            item.setData(
                0,
                Qt.ItemDataRole.UserRole + 1,
                self._resolve_folder_style(data["name"]),
            )
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if parent:
            parent.addChild(item)
        else:
            self.bookmark_tree.addTopLevelItem(item)

        # Recursively create children
        if is_folder and "children" in data:
            for child_data in data["children"]:
                self._create_tree_item(child_data, item)

        return item

    def save_bookmarks(self):
        """Saves the entire hierarchical tree structure to file."""
        data = []
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            data.append(self._serialize_item(root.child(i)))
        bookmark_nodes = [self.bookmark_manager._deserialize_node(d) for d in data]
        self.bookmark_manager.save_bookmarks(bookmark_nodes)

    def _serialize_item(self, item: QTreeWidgetItem) -> dict[str, Any]:
        """Recursively converts a tree item back into a dictionary for saving."""
        data = item.data(0, Qt.ItemDataRole.UserRole).copy()
        if data.get("type") == "folder":
            data["children"] = [
                self._serialize_item(item.child(i)) for i in range(item.childCount())
            ]
        return data

    def load_bookmarks(self):
        """Loads the hierarchical bookmark structure from file and populates the tree."""
        self.bookmark_tree.clear()
        bookmark_nodes = self.bookmark_manager.load_bookmarks()

        bookmark_nodes, changed = self._normalize_bookmark_nodes(bookmark_nodes)
        if changed:
            self.bookmark_manager.save_bookmarks(bookmark_nodes)

        bookmark_nodes.sort(key=self._bookmark_sort_key)
        for node in bookmark_nodes:
            node_data = self.bookmark_manager._serialize_node(node)
            item = self._create_tree_item(node_data)
            item.setExpanded(True)

    def _normalize_bookmark_nodes(
        self, bookmark_nodes: list[BookmarkNode]
    ) -> tuple[list[BookmarkNode], bool]:
        """Align saved bookmark folders with the glossy sidebar set without dropping user data."""
        changed = False

        def _folder_lookup() -> dict[str, BookmarkFolder]:
            return {
                node.name.lower(): node
                for node in bookmark_nodes
                if isinstance(node, BookmarkFolder)
            }

        folder_lookup = _folder_lookup()

        ai_news_node = folder_lookup.get("ai news")
        if ai_news_node is not None:
            ai_news_node.name = "News"
            changed = True
            folder_lookup = _folder_lookup()

        reading_node = folder_lookup.get("reading")
        misc_node = folder_lookup.get("misc")
        if reading_node is not None:
            if misc_node is None:
                reading_node.name = "Misc"
            else:
                misc_node.children.extend(reading_node.children)
                bookmark_nodes.remove(reading_node)
            changed = True
            folder_lookup = _folder_lookup()

        removable_empty_folders = {"news", "apple", "google", "github", "fun"}
        kept_nodes: list[BookmarkNode] = []
        for node in bookmark_nodes:
            if (
                isinstance(node, BookmarkFolder)
                and node.name.lower() in removable_empty_folders
                and node.name.lower() not in {"news"}
                and not node.children
            ):
                changed = True
                continue
            kept_nodes.append(node)
        bookmark_nodes = kept_nodes
        folder_lookup = _folder_lookup()

        for folder_name in DEFAULT_BOOKMARK_FOLDER_NAMES:
            if folder_name.lower() not in folder_lookup:
                bookmark_nodes.append(BookmarkFolder(name=folder_name, children=[]))
                changed = True
                folder_lookup = _folder_lookup()

        return bookmark_nodes, changed

    def _bookmark_sort_key(self, node: BookmarkNode) -> tuple[int, int, str]:
        preferred_order = {
            name.lower(): index
            for index, name in enumerate(DEFAULT_BOOKMARK_FOLDER_NAMES)
        }
        folder_name = node.name.lower()
        group = 0 if folder_name in preferred_order else 1
        order = preferred_order.get(folder_name, 999)
        return group, order, folder_name

    def _show_bookmark_context_menu(self, position):
        """Shows a context menu for bookmark items with relevant actions."""
        item = self.bookmark_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        # Apply theme styling to the context menu
        menu.setStyleSheet(
            """
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
                background-color: rgba(91, 141, 239, 0.28);
                color: #E8ECF4;
            }
            """
        )

        data = item.data(0, Qt.ItemDataRole.UserRole)
        item_type = data.get("type") if data else None

        if item_type == "bookmark":
            open_action = menu.addAction("Open in Safari")
            open_action.triggered.connect(lambda: self._open_bookmark_link(item))
            menu.addSeparator()

        edit_action = menu.addAction("Rename")
        edit_action.triggered.connect(lambda: self.bookmark_tree.editItem(item))

        if item_type == "folder":
            add_bookmark_action = menu.addAction("Add Bookmark to Folder")
            add_bookmark_action.triggered.connect(lambda: self._add_bookmark_link(item))
            add_folder_action = menu.addAction("Add Subfolder")
            add_folder_action.triggered.connect(self.add_bookmark_section)

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_bookmark_item(item))

        menu.exec(self.bookmark_tree.viewport().mapToGlobal(position))

    def _open_bookmark_link(self, item: QTreeWidgetItem):
        """Opens a bookmark URL in existing Safari window with privacy settings."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "bookmark":
            url = data.get("url")
            if url:
                self.worker = AsyncWorker(
                    self._open_bookmark_in_existing_window,
                    [url],
                    self.private_mode_enabled,
                )
                self.worker.start()

    async def _open_bookmark_in_existing_window(
        self, urls: list[str], private_mode: bool = True
    ) -> bool:
        """Open bookmark URLs via the escaped AppleScript builder path."""
        return await self.safari_controller.open_urls_in_front_window(
            urls, private_mode=private_mode
        )

    def _add_bookmark_link(self, parent_item: QTreeWidgetItem | None = None):
        """Prompts for bookmark details and adds a new bookmark."""
        current_item = self.bookmark_tree.currentItem()
        if not parent_item and current_item:
            data = current_item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "folder":
                parent_item = current_item

        parent = parent_item if parent_item else self._get_selected_parent_item()

        name, ok_name = QInputDialog.getText(self, "New Bookmark", "Bookmark name:")
        if not ok_name or not name.strip():
            return

        url, ok_url = QInputDialog.getText(self, "New Bookmark", "URL:")
        if ok_url and url.strip():
            bookmark_data = {
                "name": name.strip(),
                "type": "bookmark",
                "url": self.url_processor._normalize_url(url.strip()) or url.strip(),
            }
            self._create_tree_item(bookmark_data, parent)
            if parent:
                parent.setExpanded(True)
            self.save_bookmarks()

    def _delete_bookmark_item(self, item: QTreeWidgetItem):
        """Deletes a selected bookmark or folder item."""
        parent = item.parent()
        if parent:
            parent.removeChild(item)  # Use removeChild for QTreeWidgetItems
        else:
            self.bookmark_tree.takeTopLevelItem(
                self.bookmark_tree.indexOfTopLevelItem(item)
            )
        self.save_bookmarks()

    def eventFilter(self, obj, event):  # noqa: N802 - Qt override
        """Open About when the NEXUS title is double-clicked."""
        if (
            obj is getattr(self, "title_label", None)
            and event.type() == QEvent.Type.MouseButtonDblClick
        ):
            self._show_about()
            return True
        return super().eventFilter(obj, event)

    def _show_about(self) -> None:
        """Show the standardized razorcore About dialog."""
        dialog = AboutDialog(self, Config.APP_NAME)
        dialog.exec()

    def _check_for_updates(self) -> None:
        """Check GitHub Releases for a newer Nexus version."""
        result = check_for_updates(Config.APP_NAME, Config.APP_VERSION)
        if result.is_error:
            self._show_message(
                f"Update check failed: {result.error}",
                "error",
            )
            return
        if result.update_available:
            notes = result.release_notes or ""
            detail = f"New version available: {result.latest_version}"
            if result.download_url:
                detail = f"{detail}\n{result.download_url}"
            if notes:
                detail = f"{detail}\n\n{notes[:400]}"
            self._show_message(detail, "info")
        else:
            self._show_message(
                f"You are up to date (v{Config.APP_VERSION}).",
                "info",
            )

    def _show_title_context_menu(self, position) -> None:
        """Title context menu for About and update checking."""
        menu = QMenu(self)
        about_action = menu.addAction("About Nexus")
        update_action = menu.addAction("Check for Updates")
        chosen = menu.exec(self.title_label.mapToGlobal(position))
        if chosen is about_action:
            self._show_about()
        elif chosen is update_action:
            self._check_for_updates()

    def _export_bookmarks(self):
        """Exports all bookmarks to a JSON file."""
        data = []
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            data.append(self._serialize_item(root.child(i)))

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Bookmarks", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                QMessageBox.information(
                    self, "Success", "Bookmarks exported successfully!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to export bookmarks: {str(e)}"
                )

    def _load_window_state(self):
        """Loads window geometry and state from settings."""
        geometry_data = self.settings.value("mainWindow/geometry")
        if isinstance(
            geometry_data, QByteArray
        ):  # QSettings returns QByteArray for geometry/state
            self.restoreGeometry(geometry_data)
            self.restored_window_geometry = not geometry_data.isEmpty()
        state_data = self.settings.value("mainWindow/state")
        if isinstance(state_data, QByteArray):
            self.restoreState(state_data)

    def closeEvent(self, event):  # noqa: N802 - Qt override
        """Saves window state before closing."""
        self.settings.setValue("mainWindow/geometry", self.saveGeometry())
        self.settings.setValue("mainWindow/state", self.saveState())
        super().closeEvent(event)

    def _hex_to_rgb(self, hex_color: str) -> str:
        """Converts a hex color string to an RGB string for rgba() CSS functions."""
        hex_color = hex_color.lstrip("#")
        return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"

    def _clear_all_data(self):
        """Clear all URLs and optionally cleanup logs for privacy."""
        self.url_table.clear_table()

        if Config.AUTO_LOG_CLEANUP:
            try:
                cleanup_logs()
                logger.info("Privacy cleanup completed")
            except OSError as e:
                logger.warning("Could not complete privacy cleanup: %s", e)

    def _show_message(self, message: str, level: str):
        """Shows a styled QMessageBox."""
        msg = QMessageBox(self)
        msg.setText(message)
        # Use appropriate accent color for messages, typically from the Safari tab context
        color = (
            self.current_theme["safari"]["primary"]
            if level == "info"
            else self.current_theme["safari"]["accent"]
        )
        msg.setStyleSheet(
            f"background-color: #1e1e1e; color: #fff; QPushButton {{ background-color: {color}; color: #fff; padding: 5px 10px; border-radius: 4px; }}"
        )
        msg.exec()
