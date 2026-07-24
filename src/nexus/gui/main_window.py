"""Main Application Window for Nexus."""

import json
import sys
from datetime import datetime
from pathlib import Path
from secrets import token_hex
from typing import Any, cast
from urllib.parse import urlparse

from PySide6.QtCore import (
    QByteArray,
    QEvent,
    QSettings,
    QStandardPaths,
    Qt,
)
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
from nexus.core.link_converter import LinkConverter
from nexus.core.models import (
    Bookmark,
    BookmarkFolder,
    BookmarkGroup,
    BookmarkNode,
    GroupItem,
    QuickSaveEntry,
)
from nexus.core.safari import SafariController
from nexus.gui.widgets import (
    AsyncWorker,
    BookmarkTreeDelegate,
    CosmicFrame,
    GlassButton,
    MetallicLabel,
    QuickSavePanel,
    URLTableWidget,
    WindowTitleBar,
)
from nexus.utils.url_processor import URLProcessor
from razorcore.appinfo import AboutDialog
from razorcore.updates import check_for_updates


QUICK_SAVE_FOLDER_NAME = "Quick Save"


class MainWindow(QMainWindow):
    """The main application window with hierarchical bookmark support."""

    APP_NAME = Config.APP_NAME

    # Hex colors keyed by default tab name.  Order matches
    # ``DEFAULT_BOOKMARK_FOLDER_NAMES`` in ``core.bookmarks``.
    DEFAULT_TAB_PALETTE: dict[str, str] = {
        QUICK_SAVE_FOLDER_NAME: "#2EC4A0",
        "Fun": "#E5738A",
        "Misc": "#D4A05A",
        "Tech": "#5B8DEF",
        "Work": "#E85A5A",
        "Extra": "#8A95A8",
        "Hidden": "#2A2A35",
        "Special": "#F0F4FA",
        "Favorites": "#5BA86A",
    }

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
        self.link_converter = LinkConverter()
        self.safari_controller = SafariController()

        app_data_dir = Path(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppDataLocation
            )
        )
        self.bookmark_manager = BookmarkManager(app_data_dir / Config.BOOKMARKS_FILE)

        from nexus.core.group_store import GroupStore

        self.group_store = GroupStore(app_data_dir / Config.BOOKMARK_GROUPS_FILE)

        self._setup_window()
        self._load_window_state()  # Load window geometry/state
        self._setup_ui()  # Setup UI components
        self.load_bookmarks()  # Load bookmarks into the tree
        self._apply_theme()  # Apply theme after all UI is set up

        quick_save_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        quick_save_shortcut.activated.connect(self._quick_save_urls)

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
        main_layout.setContentsMargins(22, 0, 22, 16)
        main_layout.setSpacing(8)

        if sys.platform == "darwin":
            self.window_titlebar = WindowTitleBar(self, "Nexus")
            main_layout.addWidget(self.window_titlebar)

        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        self.title_label = MetallicLabel("Nexus", variant="hero")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFixedHeight(58)
        self.title_label.setToolTip("Double-click for About · Right-click for updates")
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.title_label.customContextMenuRequested.connect(
            self._show_title_context_menu
        )
        self.title_label.installEventFilter(self)
        header_layout.addWidget(self.title_label)

        self.summary_label = MetallicLabel(
            "Safari bookmark manager and batch URL opener — paste links, organize folders, open everything at once.",
            variant="dim",
        )
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.summary_label.setWordWrap(True)
        header_layout.addWidget(self.summary_label)
        main_layout.addWidget(header_widget)

        header_rule = QFrame()
        header_rule.setFixedHeight(2)
        header_rule.setStyleSheet(
            """
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(74, 144, 232, 0.0),
                stop:0.18 rgba(74, 144, 232, 0.70),
                stop:0.50 rgba(155, 122, 232, 0.65),
                stop:0.82 rgba(46, 196, 160, 0.70),
                stop:1 rgba(74, 144, 232, 0.0));
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
                background: rgba(2, 6, 14, 0.88);
                border-right: 1px solid rgba(74, 144, 232, 0.28);
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

        sidebar_title = MetallicLabel("Bookmarks", variant="body")
        sidebar_title.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        sidebar_header_layout.addWidget(sidebar_title, 1)

        self.add_folder_btn = QPushButton("+")
        self.add_folder_btn.clicked.connect(self.add_bookmark_section)
        self.add_folder_btn.setFixedSize(26, 26)
        self.add_folder_btn.setToolTip("Add folder")
        self.add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_folder_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_folder_btn.setStyleSheet("""
            QPushButton {
                background: rgba(74, 144, 232, 0.22);
                border: 1px solid rgba(120, 180, 255, 0.55);
                border-radius: 7px;
                color: #E8F2FF;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 18px;
                font-weight: 500;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background: rgba(74, 144, 232, 0.38);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(74, 144, 232, 0.16);
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
                background: rgba(2, 6, 14, 0.95);
                border: 1px solid rgba(74, 144, 232, 0.35);
                border-radius: 9px;
                color: #F0F4FA;
                padding: 9px 14px;
                font-size: 14px;
                font-family: "Helvetica Neue", sans-serif;
                selection-background-color: rgba(74, 144, 232, 0.55);
            }
            QLineEdit:focus {
                border: 1px solid rgba(120, 180, 255, 0.75);
                background: rgba(2, 6, 14, 1.0);
            }
            QLineEdit::placeholder {
                color: rgba(148, 168, 200, 0.75);
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
        self.bookmark_tree.itemClicked.connect(self._handle_bookmark_item_clicked)
        self.bookmark_tree.setRootIsDecorated(False)
        self.bookmark_tree.setItemsExpandable(True)
        self.bookmark_tree.setIndentation(0)
        self.bookmark_tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bookmark_tree.setMouseTracking(True)
        self.bookmark_tree.setAcceptDrops(True)
        self.bookmark_tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.bookmark_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.bookmark_tree.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.bookmark_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.bookmark_tree.model().rowsMoved.connect(self._on_top_level_reordered)
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

        tagline_row = QHBoxLayout()
        tagline_row.setContentsMargins(0, 0, 0, 0)
        tagline_row.setSpacing(8)

        tagline = MetallicLabel("Paste URLs. Open in Safari.", variant="accent")
        tagline.setAlignment(Qt.AlignmentFlag.AlignLeft)
        tagline_row.addWidget(tagline, 1)

        self.load_file_btn = QPushButton("Load File")
        self.load_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_file_btn.setFixedHeight(28)
        self.load_file_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.load_file_btn.clicked.connect(self._load_file_into_table)
        self.load_file_btn.setStyleSheet("""
            QPushButton {
                background: rgba(46, 196, 160, 0.15);
                border: 1px solid rgba(46, 196, 160, 0.45);
                border-radius: 6px;
                color: #7AF0D0;
                font-family: "Helvetica Neue", sans-serif;
                font-size: 12px;
                font-weight: 600;
                padding: 4px 14px;
            }
            QPushButton:hover {
                background: rgba(46, 196, 160, 0.28);
                color: #AAFAE8;
            }
            QPushButton:pressed {
                background: rgba(46, 196, 160, 0.10);
            }
        """)
        tagline_row.addWidget(self.load_file_btn)
        main_content_layout.addLayout(tagline_row)

        url_panel = QWidget()
        url_panel.setObjectName("urlWell")
        url_panel.setStyleSheet("""
            QWidget#urlWell {
                background: rgb(3, 7, 16);
                border: 1px solid rgba(74, 144, 232, 0.22);
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
        self.url_table.file_dropped.connect(self.load_file_from_path)
        self.url_table.setToolTip("Double-click a URL row to open it in Safari")
        self.url_table.setStyleSheet("""
            QTableWidget {
                background: transparent;
                border: none;
                color: #F0F4FA;
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
                color: #F0F4FA;
                padding-left: 16px;
                font-size: 15px;
                selection-background-color: rgba(110, 130, 168, 0.45);
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

        self.url_empty_title = MetallicLabel(
            "Paste URLs to get started", variant="section"
        )
        self.url_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.url_empty_title)

        self.url_empty_note = MetallicLabel(
            "Copied links appear here automatically. Each row shows Ready, Opening, or Failed.",
            variant="dim",
        )
        self.url_empty_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.url_empty_note.setWordWrap(True)
        empty_layout.addWidget(self.url_empty_note)
        empty_layout.addStretch()

        self.url_stack_host = QWidget()
        self.url_stack = QStackedLayout(self.url_stack_host)
        self.url_stack.setContentsMargins(0, 0, 0, 0)
        self.url_stack.addWidget(self.url_empty_state)
        self.url_stack.addWidget(self.url_table)

        self.quick_save_panel = QuickSavePanel()
        self.quick_save_panel.delete_requested.connect(self._delete_quick_save_entry)
        self.quick_save_panel.copy_urls_requested.connect(
            self._copy_quick_save_entry_urls
        )
        self.quick_save_panel.load_urls_requested.connect(
            self._load_quick_save_entry_to_table
        )
        self.quick_save_panel.notes_changed.connect(self._update_quick_save_notes)
        self.url_stack.addWidget(self.quick_save_panel)

        url_panel_layout.addWidget(self.url_stack_host, 1)
        main_content_layout.addWidget(url_panel, 1)

        self.url_counter_label = QLabel("0 URLs ready")
        self.url_counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.url_counter_label.setStyleSheet("""
            QLabel {
                color: #4AE89A;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.2px;
                padding-top: 2px;
                padding-right: 4px;
            }
        """)
        main_content_layout.addWidget(self.url_counter_label)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(8, 6, 8, 2)
        button_row.setSpacing(14)

        self.run_btn = GlassButton("Open All", "open")
        self.run_btn.clicked.connect(self._run_urls_in_safari)

        self.save_btn = GlassButton("Save", "save")
        self.save_btn.clicked.connect(self._save_urls_to_bookmarks)

        self.quick_save_btn = GlassButton("Quick Save", "quick")
        self.quick_save_btn.clicked.connect(self._quick_save_urls)

        self.rich_links_btn = GlassButton("Rich Links", "rich")
        self.rich_links_btn.clicked.connect(self._copy_rich_links)
        self.rich_links_btn.setToolTip(
            "Copy URLs as rich HTML links — paste into Apple Notes with ⌘V\n"
            "Right-click for options"
        )
        self.rich_links_btn.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.rich_links_btn.customContextMenuRequested.connect(
            self._show_rich_links_options
        )

        self.undo_btn = GlassButton("Undo", "undo")
        self.undo_btn.clicked.connect(self._undo_url_change)
        self.undo_btn.setEnabled(False)

        self.clear_btn = GlassButton("Clear", "clear")
        self.clear_btn.clicked.connect(self._clear_all_data)
        for button in (
            self.run_btn,
            self.save_btn,
            self.quick_save_btn,
            self.rich_links_btn,
            self.undo_btn,
            self.clear_btn,
        ):
            button.setFixedSize(120, 46)

        button_row.addStretch()
        button_row.addWidget(self.run_btn)
        button_row.addWidget(self.save_btn)
        button_row.addWidget(self.quick_save_btn)
        button_row.addWidget(self.rich_links_btn)
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
        if hasattr(self, "url_stack") and hasattr(self, "quick_save_panel"):
            # Don't yank the user out of the Quick Save database view.
            if self.url_stack.currentWidget() is not self.quick_save_panel:
                self.url_stack.setCurrentWidget(
                    self.url_table if has_urls else self.url_empty_state
                )
        elif hasattr(self, "url_stack"):
            self.url_stack.setCurrentWidget(
                self.url_table if has_urls else self.url_empty_state
            )
        # Keep action buttons colored and clickable; handlers no-op when empty.
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
        """Save the URLs in the table as a new bookmark group."""
        urls = self.url_table.get_all_urls()
        if not urls:
            self._show_message("No valid URLs found to save.", "warning")
            return

        from nexus.gui.dialogs.save_group_dialog import SaveGroupDialog

        folders: list[str] = []
        for i in range(self.bookmark_tree.topLevelItemCount()):
            top_item = self.bookmark_tree.topLevelItem(i)
            if top_item is not None:
                folders.append(top_item.text(0))
        preselect = self._currently_selected_folder_name() or folders[0]
        dialog = SaveGroupDialog(folders=folders, preselect=preselect, parent=self)
        if dialog.exec() != SaveGroupDialog.DialogCode.Accepted:
            return
        name = dialog.group_name
        target = dialog.target_folder
        if not name:
            return

        group = BookmarkGroup(
            id="grp_" + token_hex(4),
            name=name,
            created_at=datetime.now().isoformat(timespec="seconds"),
            items=[
                GroupItem(title=self._generate_bookmark_name(u), url=u) for u in urls
            ],
        )
        self.group_store.upsert_group(group)

        target_item = self._find_folder_by_name(target)
        if target_item is not None:
            marker = {
                "type": "group",
                "id": group.id,
                "name": group.name,
                "count": len(group.items),
            }
            self._create_tree_item(marker, target_item)
            target_item.setExpanded(True)
        self.save_bookmarks()

        self.url_table.clear_table()
        self._set_status(f"Saved {len(urls)} URLs to '{name}' in {target}")

    def _quick_save_urls(self):
        """Save the current URL list as a dated Quick Save block (newest first)."""
        urls = self.url_table.get_all_urls()
        if not urls:
            clipboard = QApplication.clipboard()
            if clipboard:
                urls = self.url_processor.extract_urls(clipboard.text())

        if not urls:
            self._show_message(
                "No URLs found to quick save. Paste or copy a URL first.", "warning"
            )
            return

        normalized = [
            self.url_processor._normalize_url(url) or url for url in urls
        ]
        entry = QuickSaveEntry(
            id="qs_" + token_hex(4),
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            urls=normalized,
            notes="",
        )

        folder_item = self._find_or_create_folder(QUICK_SAVE_FOLDER_NAME)
        data = folder_item.data(0, Qt.ItemDataRole.UserRole) or {
            "name": QUICK_SAVE_FOLDER_NAME,
            "type": "folder",
            "children": [],
        }
        children = list(data.get("children") or [])
        children.insert(0, entry.to_dict())
        data["children"] = children
        folder_item.setData(0, Qt.ItemDataRole.UserRole, data)
        # Quick Save has no expandable subfolders/rows in the sidebar.
        folder_item.setExpanded(False)

        self.save_bookmarks()
        self._show_quick_save_view(folder_item)
        self._set_status(
            f"Quick saved {len(normalized)} URL"
            f"{'s' if len(normalized) != 1 else ''} to {QUICK_SAVE_FOLDER_NAME}"
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
        if (
            hasattr(self, "url_stack")
            and hasattr(self, "quick_save_panel")
            and self.url_stack.currentWidget() is self.quick_save_panel
        ):
            return
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

    def _resolve_folder_style(
        self, folder_name: str, accent: str | None = None
    ) -> dict[str, str]:
        """Return an accent color for a bookmark folder row.

        Lookup order:
        1. The folder's own ``accent`` argument (set via NewFolderDialog).
        2. The fixed palette for the ten default tabs.
        3. A stable fallback cycle for any other name.
        """
        if accent:
            return self._style_from_accent(accent)
        if folder_name in self.DEFAULT_TAB_PALETTE:
            return self._style_from_accent(self.DEFAULT_TAB_PALETTE[folder_name])

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
        if not hasattr(self, "_folder_style_cache"):
            self._folder_style_cache = {}

        normalized = folder_name.lower()
        if normalized not in self._folder_style_cache:
            index = len(self._folder_style_cache) % len(fallback_styles)
            self._folder_style_cache[normalized] = fallback_styles[index]

        return self._folder_style_cache[normalized]

    @staticmethod
    def _style_from_accent(hex_color: str) -> dict[str, str]:
        """Build a 4-color style dict from a single accent hex."""
        c = QColor(hex_color)
        return {
            "start": c.name().upper(),
            "end": c.darker(140).name().upper(),
            "border": c.lighter(120).name().upper(),
            "icon": c.lighter(150).name().upper(),
        }

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
            if data.get("name") == QUICK_SAVE_FOLDER_NAME:
                self._show_quick_save_view(item)
                return
            item.setExpanded(not item.isExpanded())

    def _handle_bookmark_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Single-click: open Quick Save database view, otherwise restore URL table."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "folder" and data.get("name") == QUICK_SAVE_FOLDER_NAME:
            self._show_quick_save_view(item)
            return
        self._show_url_table_view()

    def _show_url_table_view(self) -> None:
        """Show the URL empty state or URL table (whichever is appropriate)."""
        if self.url_table.rowCount() == 0:
            self.url_stack.setCurrentWidget(self.url_empty_state)
        else:
            self.url_stack.setCurrentWidget(self.url_table)

    def _show_quick_save_view(self, folder_item: QTreeWidgetItem | None = None) -> None:
        """Show the Quick Save panel filled from the Quick Save folder."""
        if folder_item is None:
            folder_item = self._find_folder_by_name(QUICK_SAVE_FOLDER_NAME)
        if folder_item is None:
            folder_item = self._find_or_create_folder(QUICK_SAVE_FOLDER_NAME)

        self.bookmark_tree.setCurrentItem(folder_item)
        data = folder_item.data(0, Qt.ItemDataRole.UserRole) or {}
        entries = [
            child
            for child in (data.get("children") or [])
            if isinstance(child, dict) and child.get("type") == "quick_save"
        ]
        entries.sort(
            key=lambda e: str(e.get("created_at") or ""),
            reverse=True,
        )
        self.quick_save_panel.set_entries(entries)
        self.url_stack.setCurrentWidget(self.quick_save_panel)
        self.url_counter_label.setText(
            f"{len(entries)} Quick Save{'s' if len(entries) != 1 else ''}"
        )

    def _get_quick_save_folder_data(self) -> tuple[QTreeWidgetItem, dict[str, Any]]:
        folder_item = self._find_or_create_folder(QUICK_SAVE_FOLDER_NAME)
        data = folder_item.data(0, Qt.ItemDataRole.UserRole) or {
            "name": QUICK_SAVE_FOLDER_NAME,
            "type": "folder",
            "children": [],
        }
        return folder_item, data

    def _set_quick_save_children(
        self, folder_item: QTreeWidgetItem, children: list[dict[str, Any]]
    ) -> None:
        data = folder_item.data(0, Qt.ItemDataRole.UserRole) or {
            "name": QUICK_SAVE_FOLDER_NAME,
            "type": "folder",
            "children": [],
        }
        data["children"] = children
        folder_item.setData(0, Qt.ItemDataRole.UserRole, data)

    def _delete_quick_save_entry(self, entry_id: str) -> None:
        folder_item, data = self._get_quick_save_folder_data()
        children = [
            child
            for child in (data.get("children") or [])
            if not (
                isinstance(child, dict)
                and child.get("type") == "quick_save"
                and child.get("id") == entry_id
            )
        ]
        self._set_quick_save_children(folder_item, children)
        self.save_bookmarks()
        self._show_quick_save_view(folder_item)
        self._set_status("Deleted Quick Save block")

    def _copy_quick_save_entry_urls(self, entry_id: str) -> None:
        urls = self.quick_save_panel.copy_entry_urls_to_clipboard(entry_id)
        if not urls:
            folder_item, data = self._get_quick_save_folder_data()
            for child in data.get("children") or []:
                if (
                    isinstance(child, dict)
                    and child.get("type") == "quick_save"
                    and child.get("id") == entry_id
                ):
                    urls = [str(u) for u in child.get("urls") or [] if str(u).strip()]
                    clipboard = QApplication.clipboard()
                    if clipboard is not None and urls:
                        clipboard.setText("\n".join(urls))
                    break
            _ = folder_item
        if urls:
            self._set_status(
                f"Copied {len(urls)} bookmark{'s' if len(urls) != 1 else ''}"
            )
        else:
            self._set_status("No bookmarks to copy")

    def _load_quick_save_entry_to_table(self, entry_id: str) -> None:
        _folder_item, data = self._get_quick_save_folder_data()
        urls: list[str] = []
        for child in data.get("children") or []:
            if (
                isinstance(child, dict)
                and child.get("type") == "quick_save"
                and child.get("id") == entry_id
            ):
                urls = [str(u) for u in child.get("urls") or [] if str(u).strip()]
                break
        if not urls:
            self._show_message("No bookmarks in this Quick Save block.", "warning")
            return
        self.url_table.add_urls(urls)
        self._show_url_table_view()
        self._set_status(
            f"Loaded {len(urls)} bookmark{'s' if len(urls) != 1 else ''} into URL table"
        )

    def _update_quick_save_notes(self, entry_id: str, notes: str) -> None:
        folder_item, data = self._get_quick_save_folder_data()
        children = list(data.get("children") or [])
        changed = False
        for child in children:
            if (
                isinstance(child, dict)
                and child.get("type") == "quick_save"
                and child.get("id") == entry_id
            ):
                if child.get("notes") != notes:
                    child["notes"] = notes
                    changed = True
                break
        if changed:
            self._set_quick_save_children(folder_item, children)
            self.save_bookmarks()

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

    def _currently_selected_folder_name(self) -> str | None:
        """Return the name of the currently selected top-level folder, if any."""
        item = self.bookmark_tree.currentItem()
        if not item:
            return None
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "folder":
            return data.get("name")
        parent = item.parent()
        if parent:
            parent_data = parent.data(0, Qt.ItemDataRole.UserRole) or {}
            return parent_data.get("name")
        return None

    def _find_folder_by_name(self, name: str) -> QTreeWidgetItem | None:
        """Find a top-level folder item by its displayed name."""
        root = self.bookmark_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "folder" and data.get("name") == name:
                return item
        return None

    def _set_status(self, message: str) -> None:
        """Update the status bar label if it has been created."""
        if hasattr(self, "status_bar"):
            self.status_bar.setText(message)

    def _on_top_level_reordered(self) -> None:
        """Called after a drag-reorder of top-level tabs; persists the new order."""
        self.save_bookmarks()

    def add_bookmark_section(self):
        """Prompts for a new folder name + color and adds it to the tree."""
        parent_item = self._get_selected_parent_item()
        from nexus.gui.dialogs.new_folder_dialog import NewFolderDialog

        dialog = NewFolderDialog(self)
        if dialog.exec() != NewFolderDialog.DialogCode.Accepted:
            return
        name = dialog.folder_name
        accent = dialog.accent
        if not name:
            return
        folder_data = {
            "name": name,
            "type": "folder",
            "accent": accent,
            "children": [],
        }
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
        is_group = data.get("type") == "group"
        is_quick_save_folder = is_folder and data.get("name") == QUICK_SAVE_FOLDER_NAME
        item = QTreeWidgetItem([data.get("name", "(missing group)")])
        # Keep a deep-enough copy so Quick Save children live on the item,
        # not as expandable sidebar rows.
        item.setData(0, Qt.ItemDataRole.UserRole, dict(data))
        if is_folder:
            folder_style = self._resolve_folder_style(
                data["name"],
                accent=data.get("accent"),
            )
            item.setData(0, Qt.ItemDataRole.UserRole + 1, folder_style)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_quick_save_folder:
                # No subfolders / child rows — entries render in QuickSavePanel.
                children = []
                for child in data.get("children") or []:
                    if isinstance(child, dict):
                        children.append(dict(child))
                payload = dict(data)
                payload["children"] = children
                item.setData(0, Qt.ItemDataRole.UserRole, payload)
                item.setChildIndicatorPolicy(
                    QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
                )
            elif "children" in data:
                for child_data in data["children"]:
                    if isinstance(child_data, dict):
                        self._create_tree_item(child_data, item)
        elif is_group:
            item.setData(
                0,
                Qt.ItemDataRole.UserRole + 1,
                self._resolve_folder_style(
                    data.get("name", ""),
                    accent=data.get("accent"),
                ),
            )
            item.setFlags(
                (item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                & ~Qt.ItemFlag.ItemIsSelectable
            )
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if is_group and parent is None:
            # Group markers are only meaningful as children of folders.
            return item

        if parent:
            parent.addChild(item)
        else:
            self.bookmark_tree.addTopLevelItem(item)

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
            if data.get("name") == QUICK_SAVE_FOLDER_NAME:
                # Children are stored on UserRole, not as tree widgets.
                data["children"] = [
                    dict(child)
                    for child in (data.get("children") or [])
                    if isinstance(child, dict)
                ]
            else:
                data["children"] = [
                    self._serialize_item(item.child(i))
                    for i in range(item.childCount())
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
            if node_data.get("name") == QUICK_SAVE_FOLDER_NAME:
                item.setExpanded(False)
            else:
                item.setExpanded(True)

    def _normalize_bookmark_nodes(
        self, bookmark_nodes: list[BookmarkNode]
    ) -> tuple[list[BookmarkNode], bool]:
        """Align saved bookmark folders with the sidebar set.

        - Removes empty legacy defaults and the retired ``hey`` / ``Sort`` /
          ``Future`` tabs
        - Renames ``Quick Saves`` → ``Quick Save`` and migrates old bookmarks
          into ``quick_save`` blocks
        - Ensures ``Quick Save`` and the standard default tabs exist
        """
        changed = False
        old_empty_defaults = {
            "favorites",
            "tech",
            "misc",
            "work",
            "later",
            "news",
        }
        retired_empty_tabs = {"hey", "sort", "future"}
        retired_tab_migrations: list[BookmarkNode] = []

        kept_nodes: list[BookmarkNode] = []
        quick_save_folder: BookmarkFolder | None = None

        for node in bookmark_nodes:
            if isinstance(node, BookmarkFolder):
                name_lower = node.name.lower()
                if name_lower in retired_empty_tabs:
                    changed = True
                    if node.children:
                        retired_tab_migrations.extend(node.children)
                    continue
                if name_lower in old_empty_defaults and not node.children:
                    changed = True
                    continue
                if name_lower in {"quick save", "quick saves"}:
                    migrated = self._coerce_quick_save_folder(node)
                    if quick_save_folder is None:
                        quick_save_folder = migrated
                    else:
                        quick_save_folder.children.extend(migrated.children)
                    if (
                        migrated.name != node.name
                        or migrated.children != node.children
                    ):
                        changed = True
                    continue
            kept_nodes.append(node)

        if quick_save_folder is None:
            quick_save_folder = BookmarkFolder(
                name=QUICK_SAVE_FOLDER_NAME,
                children=[],
                accent=self.DEFAULT_TAB_PALETTE.get(QUICK_SAVE_FOLDER_NAME),
            )
            changed = True
        elif quick_save_folder.name != QUICK_SAVE_FOLDER_NAME:
            quick_save_folder.name = QUICK_SAVE_FOLDER_NAME
            changed = True

        bookmark_nodes = [quick_save_folder, *kept_nodes]

        if retired_tab_migrations:
            migration_target = DEFAULT_BOOKMARK_FOLDER_NAMES[0]
            target_folder: BookmarkFolder | None = None
            for node in bookmark_nodes:
                if isinstance(node, BookmarkFolder) and node.name == migration_target:
                    target_folder = node
                    break
            if target_folder is None:
                target_folder = BookmarkFolder(name=migration_target, children=[])
                bookmark_nodes.append(target_folder)
            target_folder.children.extend(retired_tab_migrations)

        existing_names = {
            node.name.lower()
            for node in bookmark_nodes
            if isinstance(node, BookmarkFolder)
        }
        for folder_name in DEFAULT_BOOKMARK_FOLDER_NAMES:
            if folder_name.lower() not in existing_names:
                bookmark_nodes.append(BookmarkFolder(name=folder_name, children=[]))
                existing_names.add(folder_name.lower())
                changed = True

        return bookmark_nodes, changed

    def _coerce_quick_save_folder(self, folder: BookmarkFolder) -> BookmarkFolder:
        """Normalize a Quick Save(s) folder into quick_save marker children."""
        children: list[BookmarkNode] = []
        for child in folder.children:
            if isinstance(child, dict) and child.get("type") == "quick_save":
                entry = QuickSaveEntry.from_dict(cast(dict[str, Any], child))
                if not entry.id:
                    entry.id = "qs_" + token_hex(4)
                children.append(entry.to_dict())
                continue
            if isinstance(child, Bookmark):
                children.append(
                    QuickSaveEntry(
                        id="qs_" + token_hex(4),
                        created_at=datetime.now()
                        .astimezone()
                        .isoformat(timespec="seconds"),
                        urls=[child.url],
                        notes="",
                    ).to_dict()
                )
                continue
            if isinstance(child, dict) and child.get("type") == "bookmark":
                url = str(child.get("url") or "").strip()
                if url:
                    children.append(
                        QuickSaveEntry(
                            id="qs_" + token_hex(4),
                            created_at=datetime.now()
                            .astimezone()
                            .isoformat(timespec="seconds"),
                            urls=[url],
                            notes="",
                        ).to_dict()
                    )
                continue
            # Preserve unknown markers (e.g. groups) if somehow present.
            children.append(child)

        return BookmarkFolder(
            name=QUICK_SAVE_FOLDER_NAME,
            children=children,
            accent=folder.accent
            or self.DEFAULT_TAB_PALETTE.get(QUICK_SAVE_FOLDER_NAME),
        )

    def _bookmark_sort_key(self, node: BookmarkNode) -> tuple[int, int, str]:
        preferred_order = {
            name.lower(): index
            for index, name in enumerate(
                (QUICK_SAVE_FOLDER_NAME, *DEFAULT_BOOKMARK_FOLDER_NAMES)
            )
        }
        if isinstance(node, dict):
            folder_name = str(node.get("name", "")).lower()
        else:
            folder_name = node.name.lower()
        group = 0 if folder_name in preferred_order else 1
        order = preferred_order.get(folder_name, 999)
        return group, order, folder_name

    def _show_bookmark_context_menu(self, position):
        """Shows a context menu for folder, bookmark, and group items."""
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

        if item_type == "group":
            open_action = menu.addAction("Open in Safari")
            open_action.triggered.connect(lambda: self._open_group_in_safari(item))
            menu.addSeparator()
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._rename_group(item))
            move_menu = menu.addMenu("Move to…")
            parent = item.parent()
            current_folder_name = parent.text(0) if parent else ""
            for i in range(self.bookmark_tree.topLevelItemCount()):
                folder_item = self.bookmark_tree.topLevelItem(i)
                if folder_item is None:
                    continue
                folder_data = folder_item.data(0, Qt.ItemDataRole.UserRole)
                if folder_data and folder_data.get("name") != current_folder_name:
                    move_menu.addAction(folder_data["name"]).triggered.connect(
                        lambda checked=False, fi=folder_item: self._move_group_to(
                            item, fi
                        )
                    )
            menu.addSeparator()
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_group(item))
        elif item_type == "bookmark":
            open_action = menu.addAction("Open in Safari")
            open_action.triggered.connect(lambda: self._open_bookmark_link(item))
            menu.addSeparator()

            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self.bookmark_tree.editItem(item))

            color_menu = menu.addMenu("Color")
            for hex_ in [
                "#E5738A",
                "#D4A05A",
                "#5B8DEF",
                "#E85A5A",
                "#8A95A8",
                "#A87A5A",
                "#2A2A35",
                "#F0F4FA",
                "#5BA86A",
                "#6B6B7A",
            ]:
                color_menu.addAction(hex_.upper()).triggered.connect(
                    lambda checked=False, h=hex_: self._set_bookmark_accent(item, h)
                )

            copy_action = menu.addAction("Copy URL")
            copy_action.triggered.connect(lambda: self._copy_bookmark_url(item))
            menu.addSeparator()

            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_bookmark_item(item))
        else:
            # Folder (or other top-level) menu
            folder_name = (data or {}).get("name", "")
            if folder_name == QUICK_SAVE_FOLDER_NAME:
                open_action = menu.addAction("Open Quick Save")
                open_action.triggered.connect(
                    lambda: self._show_quick_save_view(item)
                )
                menu.exec(self.bookmark_tree.viewport().mapToGlobal(position))
                return

            edit_action = menu.addAction("Rename")
            edit_action.triggered.connect(lambda: self.bookmark_tree.editItem(item))

            add_bookmark_action = menu.addAction("Add Bookmark to Folder")
            add_bookmark_action.triggered.connect(lambda: self._add_bookmark_link(item))
            add_folder_action = menu.addAction("Add Subfolder")
            add_folder_action.triggered.connect(self.add_bookmark_section)
            menu.addSeparator()

            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._delete_bookmark_item(item))

        menu.exec(self.bookmark_tree.viewport().mapToGlobal(position))

    def _open_group_in_safari(self, item: QTreeWidgetItem) -> None:
        """Open every URL in a saved group via the front Safari window."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        group = self.group_store.get_group(data["id"])
        if not group:
            return
        urls = [g.url for g in group.items]
        if not urls:
            return
        self.worker = AsyncWorker(
            self.safari_controller.open_urls_in_front_window,
            urls,
            self.private_mode_enabled,
        )
        self.worker.start()

    def _rename_group(self, item: QTreeWidgetItem) -> None:
        """Rename a group in the sidecar and update the tree marker."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Group",
            "New name:",
            text=data.get("name", ""),
        )
        if not ok or not new_name.strip():
            return
        group = self.group_store.get_group(data["id"])
        if group is None:
            return
        group.name = new_name.strip()
        self.group_store.upsert_group(group)
        data["name"] = new_name.strip()
        item.setText(0, new_name.strip())
        self.save_bookmarks()

    def _move_group_to(
        self, item: QTreeWidgetItem, target_folder_item: QTreeWidgetItem
    ) -> None:
        """Move a group marker from its current folder to another folder."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        old_parent = item.parent()
        if old_parent is not None:
            old_parent.removeChild(item)
        target_folder_item.addChild(item)
        target_folder_item.setExpanded(True)
        self.save_bookmarks()

    def _delete_group(self, item: QTreeWidgetItem) -> None:
        """Delete a group after confirmation, removing the sidecar entry."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "group":
            return
        confirm = QMessageBox.question(
            self,
            "Delete Group",
            f"Delete the group '{data.get('name', '')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.group_store.delete_group(data["id"])
        parent = item.parent()
        if parent is not None:
            parent.removeChild(item)
        self.save_bookmarks()

    def _set_bookmark_accent(self, item: QTreeWidgetItem, accent: str) -> None:
        """Update a bookmark row's accent and persist immediately."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "bookmark":
            return
        data["accent"] = accent
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        self.save_bookmarks()

    def _copy_bookmark_url(self, item: QTreeWidgetItem) -> None:
        """Copy a bookmark's URL to the system clipboard."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "bookmark":
            return
        url = data.get("url", "")
        if not url:
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(url)

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
        data = item.data(0, Qt.ItemDataRole.UserRole) or {}
        if data.get("type") == "folder" and data.get("name") == QUICK_SAVE_FOLDER_NAME:
            self._show_message(
                "Quick Save is a built-in column and cannot be deleted.",
                "warning",
            )
            return
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

    def _load_file_into_table(self):
        """Open a file dialog and load URLs from a .txt/.csv/.md file."""
        last_dir = str(self.settings.value("richLinks/lastDir", ""))
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load URL File",
            last_dir,
            "Text Files (*.txt);;CSV Files (*.csv);;Markdown Files (*.md);;All Files (*)",
        )
        if not file_path:
            return

        self.settings.setValue("richLinks/lastDir", str(Path(file_path).parent))

        try:
            lines = self.link_converter.load(file_path)
            parsed = self.link_converter.parse_lines(lines)
            urls = [e["text"] for e in parsed if e["type"] == "url"]
            non_url_count = sum(1 for e in parsed if e["type"] == "text")

            if urls:
                self.url_table.add_urls(urls)
                msg = f"Loaded {len(urls)} URL{'s' if len(urls) != 1 else ''}"
                if non_url_count:
                    msg += f" ({non_url_count} non-URL line{'s' if non_url_count != 1 else ''} skipped)"
                self._set_status(msg)
            else:
                self._show_message(
                    "No valid URLs found in the selected file.", "warning"
                )
        except (FileNotFoundError, ValueError, OSError) as e:
            self._show_message(f"Failed to load file: {e}", "warning")

    def _copy_rich_links(self):
        """Copy all URLs in the table as rich HTML links to the clipboard."""
        urls = self.url_table.get_all_urls()
        if not urls:
            self._show_message(
                "No URLs to copy. Paste or load URLs first.", "warning"
            )
            return

        # Apply options from QSettings
        skip_dupes = bool(self.settings.value("richLinks/skipDuplicates", True, type=bool))
        sort_alpha = bool(self.settings.value("richLinks/sortAlpha", False, type=bool))
        preserve_blanks = bool(
            self.settings.value("richLinks/preserveBlanks", True, type=bool)
        )

        parsed = self.link_converter.parse_lines(urls)
        if skip_dupes:
            parsed = self.link_converter.remove_duplicates(parsed)
        if sort_alpha:
            parsed = self.link_converter.sort_lines(parsed)

        url_count = sum(1 for e in parsed if e["type"] == "url")
        html = self.link_converter.generate_html(
            parsed, preserve_blanks=preserve_blanks
        )
        success = self.link_converter.copy_rich_html_to_clipboard(html)

        if success:
            self._set_status(
                f"Copied {url_count} rich link{'s' if url_count != 1 else ''}"
                f" to clipboard — paste into Apple Notes with ⌘V"
            )
        else:
            self._set_status(
                f"Failed to copy {url_count} link{'s' if url_count != 1 else ''}"
                f" to clipboard"
            )

    def _show_rich_links_options(self, position):
        """Show a context menu with toggleable options for Copy Rich Links."""
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

        skip_dupes = bool(self.settings.value("richLinks/skipDuplicates", True, type=bool))
        sort_alpha = bool(self.settings.value("richLinks/sortAlpha", False, type=bool))
        preserve_blanks = bool(
            self.settings.value("richLinks/preserveBlanks", True, type=bool)
        )

        skip_action = menu.addAction("Skip Duplicate URLs")
        skip_action.setCheckable(True)
        skip_action.setChecked(skip_dupes)
        skip_action.triggered.connect(
            lambda checked: self.settings.setValue("richLinks/skipDuplicates", checked)
        )

        sort_action = menu.addAction("Sort Alphabetically")
        sort_action.setCheckable(True)
        sort_action.setChecked(sort_alpha)
        sort_action.triggered.connect(
            lambda checked: self.settings.setValue("richLinks/sortAlpha", checked)
        )

        blanks_action = menu.addAction("Preserve Blank Lines")
        blanks_action.setCheckable(True)
        blanks_action.setChecked(preserve_blanks)
        blanks_action.triggered.connect(
            lambda checked: self.settings.setValue("richLinks/preserveBlanks", checked)
        )

        menu.exec(self.rich_links_btn.mapToGlobal(position))

    def load_file_from_path(self, file_path: str):
        """Load URLs from a file path (used by drag-and-drop from URLTableWidget)."""
        try:
            lines = self.link_converter.load(file_path)
            parsed = self.link_converter.parse_lines(lines)
            urls = [e["text"] for e in parsed if e["type"] == "url"]
            non_url_count = sum(1 for e in parsed if e["type"] == "text")

            if urls:
                self.url_table.add_urls(urls)
                msg = f"Loaded {len(urls)} URL{'s' if len(urls) != 1 else ''}"
                if non_url_count:
                    msg += f" ({non_url_count} non-URL line{'s' if non_url_count != 1 else ''} skipped)"
                self._set_status(msg)
            else:
                self._show_message(
                    "No valid URLs found in the dropped file.", "warning"
                )
        except (FileNotFoundError, ValueError, OSError) as e:
            self._show_message(f"Failed to load file: {e}", "warning")

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
