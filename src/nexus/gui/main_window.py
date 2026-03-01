"""Main Application Window for Nexus."""

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PySide6.QtCore import (
    QByteArray,
    QSettings,
    QStandardPaths,
    Qt,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexus.core.bookmarks import BookmarkManager
from nexus.core.config import Config, cleanup_logs, logger
from nexus.core.models import Bookmark, BookmarkFolder, BookmarkNode
from nexus.core.safari import SafariController
from nexus.gui.widgets import (
    AsyncWorker,
    GlassButton,
    URLTableWidget,
)
from nexus.utils.url_processor import URLProcessor


class MainWindow(QMainWindow):
    """The main application window with hierarchical bookmark support."""

    def __init__(self):
        """Initialize with default theme."""
        super().__init__()
        self._setup_themes()  # Define themes
        self.settings = QSettings()
        self._load_settings()  # Load saved theme or default

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
        """Defines the available color themes with 3 distinct colors for each main tab."""
        self.themes = {
            "Neon Blue": {
                "safari": {
                    "primary": "#00f5ff",
                    "secondary": "#00aaff",
                    "accent": "#ff1744",
                },
                "bookmarks": {
                    "primary": "#9933ff",
                    "secondary": "#6600cc",
                    "accent": "#39ff14",
                },
                "theme_settings": {
                    "primary": "#00f5ff",
                    "secondary": "#9933ff",
                    "accent": "#ffeb3b",
                },  # Primary is Blue
            },
            "Hot Pink": {
                "safari": {
                    "primary": "#ff2d92",
                    "secondary": "#cc0066",
                    "accent": "#4caf50",
                },
                "bookmarks": {
                    "primary": "#b200ff",
                    "secondary": "#8000cc",
                    "accent": "#ffeb3b",
                },
                "theme_settings": {
                    "primary": "#ff2d92",
                    "secondary": "#b200ff",
                    "accent": "#39ff14",
                },  # Primary is Pink
            },
            "Cyber Green": {
                "safari": {
                    "primary": "#39ff14",
                    "secondary": "#00cc00",
                    "accent": "#ff5722",
                },
                "bookmarks": {
                    "primary": "#ffff00",
                    "secondary": "#cccc00",
                    "accent": "#ff2d92",
                },
                "theme_settings": {
                    "primary": "#39ff14",
                    "secondary": "#ffff00",
                    "accent": "#00f5ff",
                },  # Primary is Green
            },
            "Electric Purple": {
                "safari": {
                    "primary": "#b200ff",
                    "secondary": "#8000cc",
                    "accent": "#ffeb3b",
                },
                "bookmarks": {
                    "primary": "#00f5ff",
                    "secondary": "#00aaff",
                    "accent": "#ff1744",
                },
                "theme_settings": {
                    "primary": "#b200ff",
                    "secondary": "#ff2d92",
                    "accent": "#4caf50",
                },  # Primary is Purple
            },
            "Sunset Orange": {
                "safari": {
                    "primary": "#ff6d00",
                    "secondary": "#cc5500",
                    "accent": "#2196f3",
                },
                "bookmarks": {
                    "primary": "#ff2d92",
                    "secondary": "#cc0066",
                    "accent": "#39ff14",
                },
                "theme_settings": {
                    "primary": "#ff6d00",
                    "secondary": "#ff2d92",
                    "accent": "#b200ff",
                },  # Primary is Orange
            },
        }

    def _load_settings(self):
        """Loads theme settings from QSettings."""
        default_theme_name = "Neon Blue"
        default_theme_colors = self.themes[default_theme_name]

        self.current_theme_name = self.settings.value("theme/name", default_theme_name)

        # Initialize current_theme with default structure
        self.current_theme = {
            "safari": {
                "primary": "#00f5ff",
                "secondary": "#00aaff",
                "accent": "#ff1744",
            },
            "bookmarks": {
                "primary": "#9933ff",
                "secondary": "#6600cc",
                "accent": "#39ff14",
            },
            "theme_settings": {
                "primary": "#00f5ff",
                "secondary": "#9933ff",
                "accent": "#ffeb3b",
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
        """Sets up the main window properties with Glass Noir styling."""
        self.setWindowTitle("Nexus")  # Set title for Dock
        self.setMinimumSize(1100, 700)
        self.resize(1100, 700)
        # Glass Noir gradient background
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0a0a0f, stop:1 #12121a);
            }
        """)

    def _setup_ui(self):
        """Sets up the Glass Noir single-pane UI with sidebar."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== HEADER: Centered NEXUS title + Tagline =====
        header_widget = QWidget()
        header_widget.setFixedHeight(95)  # Increased height for tagline
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(header_widget)  # Vertical layout
        header_layout.setContentsMargins(20, 10, 20, 10)
        header_layout.setSpacing(4)

        self.title_label = QLabel("NEXUS")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 36px;
                font-weight: 300;
                letter-spacing: 12px;
            }
        """)
        # Add glow effect to title
        title_glow = QGraphicsDropShadowEffect()
        title_glow.setBlurRadius(30)
        title_glow.setColor(QColor(0, 245, 255, 180))  # Cyan glow
        title_glow.setOffset(0, 0)
        self.title_label.setGraphicsEffect(title_glow)
        header_layout.addWidget(self.title_label)

        # Pink tagline (now in header)
        tagline = QLabel("Paste URLs. Open in Safari. Instantly.")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tagline.setStyleSheet("""
            QLabel {
                color: #ff2d92;
                font-size: 16px;
                font-weight: 600;
                font-style: italic;
                letter-spacing: 1px;
            }
        """)
        header_layout.addWidget(tagline)

        main_layout.addWidget(header_widget)

        # ===== CONTENT: Sidebar + Main area =====
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 0, 20, 20)
        content_layout.setSpacing(20)

        # ----- SIDEBAR: Bookmark folders -----
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(25, 25, 35, 0.95),
                    stop:0.5 rgba(20, 20, 30, 0.97),
                    stop:1 rgba(15, 15, 25, 0.98));
                border: 1px solid qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(139, 92, 246, 0.5),
                    stop:0.5 rgba(0, 245, 255, 0.3),
                    stop:1 rgba(139, 92, 246, 0.5));
                border-radius: 16px;
            }
        """)
        # Add subtle glow to sidebar
        sidebar_glow = QGraphicsDropShadowEffect()
        sidebar_glow.setBlurRadius(15)
        sidebar_glow.setColor(QColor(139, 92, 246, 60))  # Purple glow
        sidebar_glow.setOffset(0, 0)
        self.sidebar.setGraphicsEffect(sidebar_glow)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(12)

        # Sidebar title with cyan accent (centered)
        sidebar_title = QLabel("BOOKMARKS")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_title.setStyleSheet("""
            QLabel {
                color: #00f5ff;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 4px;
                padding: 8px 8px 16px 8px;
                background: transparent;
                border: none;
                border-bottom: 2px solid rgba(0, 245, 255, 0.4);
            }
        """)
        sidebar_layout.addWidget(sidebar_title)

        # Search bar for bookmarks
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search bookmarks...")
        self.search_bar.textChanged.connect(self._filter_bookmarks)
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(0, 245, 255, 0.3);
                border-radius: 8px;
                color: #e0e0e0;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(0, 245, 255, 0.7);
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        sidebar_layout.addWidget(self.search_bar)

        # Bookmark tree with improved styling
        self.bookmark_tree = QTreeWidget()
        self.bookmark_tree.setHeaderHidden(True)
        self.bookmark_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bookmark_tree.customContextMenuRequested.connect(
            self._show_bookmark_context_menu
        )
        self.bookmark_tree.itemDoubleClicked.connect(self._handle_item_double_click)
        self.bookmark_tree.setStyleSheet("""
            QTreeWidget {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                outline: none;
            }
            QTreeWidget::item {
                padding: 14px 20px;
                border-radius: 10px;
                margin: 4px 6px;
                background: transparent;
            }
            QTreeWidget::item:hover {
                background: rgba(255, 255, 255, 0.06);
            }
            QTreeWidget::item:selected {
                background: rgba(255, 255, 255, 0.1);
            }
            QTreeWidget::branch {
                background: transparent;
                image: none;
                border: none;
            }
            QTreeWidget::branch:has-children:open,
            QTreeWidget::branch:has-children:closed {
                background: transparent;
                border: none;
                image: none;
            }
            QTreeWidget:focus {
                outline: none;
                border: none;
            }
            QTreeWidget::item:focus {
                outline: none;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                border-radius: 4px;
                margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        self.bookmark_tree.setRootIsDecorated(
            False
        )  # Hide root decoration to remove 'grey bars' indentation
        self.bookmark_tree.setItemsExpandable(True)
        self.bookmark_tree.setIndentation(10)  # Minimal indentation
        self.bookmark_tree.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )  # Remove focus indicator
        sidebar_layout.addWidget(self.bookmark_tree, 1)

        # Add folder button with icon styling
        self.add_folder_btn = GlassButton("+ New Folder", "secondary")
        self.add_folder_btn.clicked.connect(self.add_bookmark_section)
        sidebar_layout.addWidget(self.add_folder_btn)

        content_layout.addWidget(self.sidebar)

        # ----- MAIN CONTENT: URL area -----
        main_content = QWidget()
        main_content.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 20, 32, 0.97),
                    stop:0.3 rgba(18, 18, 28, 0.98),
                    stop:0.7 rgba(15, 15, 25, 0.98),
                    stop:1 rgba(12, 12, 22, 0.99));
                border: 1px solid qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 180, 180, 0.4),
                    stop:0.5 rgba(139, 92, 246, 0.3),
                    stop:1 rgba(255, 45, 146, 0.3));
                border-radius: 16px;
            }
        """)
        # Add outer glow to main content
        content_glow = QGraphicsDropShadowEffect()
        content_glow.setBlurRadius(20)
        content_glow.setColor(QColor(0, 180, 180, 40))  # Teal glow
        content_glow.setOffset(0, 0)
        main_content.setGraphicsEffect(content_glow)
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(24, 24, 24, 24)
        main_content_layout.setSpacing(20)

        # (Tagline moved to header)

        # URL Table with enhanced styling and colored headers
        self.url_table = URLTableWidget()
        self.url_table.itemChanged.connect(self._update_url_counter)
        self.url_table.model().rowsInserted.connect(self._update_url_counter)
        self.url_table.model().rowsRemoved.connect(self._update_url_counter)
        self.url_table.setStyleSheet("""
            QTableWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(15, 15, 25, 0.8),
                    stop:1 rgba(10, 10, 20, 0.9));
                border: 1px solid rgba(0, 180, 180, 0.25);
                border-radius: 12px;
                color: #e0e0e0;
                font-size: 15px; /* Increased row text size */
                gridline-color: rgba(0, 180, 180, 0.1);
                selection-background-color: rgba(0, 180, 180, 0.3);
            }
            QTableWidget::item {
                padding: 12px 10px;
                border-bottom: 1px solid rgba(0, 180, 180, 0.08);
            }
            QTableWidget::item:hover {
                background: rgba(0, 180, 180, 0.1);
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 180, 180, 0.35), stop:1 rgba(255, 45, 146, 0.35));
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 180, 180, 0.2), stop:1 rgba(255, 45, 146, 0.15));
                color: #00e5e5;
                padding: 14px 12px;
                border: none;
                border-bottom: 1px solid rgba(0, 212, 212, 0.4);
                font-weight: 700;
                font-size: 14px; /* Increased header text size */
                letter-spacing: 1px;
            }
            QScrollBar:vertical {
                background: rgba(0, 0, 0, 0.2);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 180, 180, 0.4);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 180, 180, 0.6);
            }
        """)
        main_content_layout.addWidget(self.url_table, 1)

        # URL counter with accent styling
        self.url_counter_label = QLabel("0 URLs")
        self.url_counter_label.setStyleSheet("""
            QLabel {
                color: #8b8b8b;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
                padding: 4px 0;
            }
        """)
        main_content_layout.addWidget(self.url_counter_label)

        # Action buttons row - Distributed evenly (Space them out there are 4)
        button_row = QHBoxLayout()
        button_row.setSpacing(10)  # Using stretch instead for even spacing

        self.run_btn = GlassButton("🚀   Open All", "primary")
        self.run_btn.clicked.connect(self._run_urls_in_safari)

        self.save_btn = GlassButton("🔖   Save", "secondary")
        self.save_btn.clicked.connect(self._save_urls_to_bookmarks)

        self.private_mode_btn = GlassButton("🔓   Private Mode", "tertiary")
        self.private_mode_btn.setCheckable(True)
        self.private_mode_btn.setChecked(Config.DEFAULT_PRIVATE_MODE)
        self.private_mode_btn.clicked.connect(self._toggle_private_mode)

        self.clear_btn = GlassButton("🗑️   Clear", "danger")
        self.clear_btn.clicked.connect(self._clear_all_data)

        # Distribute buttons evenly: Stretch-Btn-Stretch-Btn-Stretch-Btn-Stretch-Btn-Stretch
        # Or simpler: Btn-Stretch-Btn-Stretch-Btn-Stretch-Btn

        button_row.addWidget(self.run_btn)
        button_row.addStretch()
        button_row.addWidget(self.clear_btn)
        button_row.addStretch()
        button_row.addWidget(self.private_mode_btn)
        button_row.addStretch()
        button_row.addWidget(self.save_btn)

        main_content_layout.addLayout(button_row)

        content_layout.addWidget(main_content, 1)

        main_layout.addWidget(content_widget, 1)

        # ===== STATUS BAR =====
        self.status_bar = QLabel("Ready")
        self.status_bar.setStyleSheet("""
            QLabel {
                color: #444444;
                font-size: 11px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 8px 20px;
            }
        """)
        main_layout.addWidget(self.status_bar)

        # Store references for legacy compatibility (some methods reference these)
        self.safari_panel = main_content
        self.bookmarks_panel = self.sidebar
        self.settings_panel = None
        self.safari_title = self.title_label
        self.bookmarks_title = sidebar_title
        self.organize_btn = None  # Removed in redesign
        self.add_link_btn = None  # Use context menu instead
        self.export_btn = None  # Use context menu instead

    def _update_private_mode_style(self):
        """Update private mode button appearance based on state."""
        if hasattr(self, "private_mode_btn"):
            if self.private_mode_btn.isChecked():
                self.private_mode_btn.setText("🔒   Private Mode")
                self.private_mode_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(139, 92, 246, 0.2);
                        color: #a78bfa;
                        border: 1px solid rgba(139, 92, 246, 0.4);
                        border-radius: 10px;
                        padding: 12px 24px;
                        font-weight: 600;
                        font-size: 14px;
                        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    }
                    QPushButton:hover {
                        background: rgba(139, 92, 246, 0.3);
                    }
                """)
            else:
                self.private_mode_btn.setText("🔓   Private Mode")
                self.private_mode_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.05);
                        color: #888888;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 10px;
                        padding: 12px 24px;
                        font-weight: 600;
                        font-size: 14px;
                        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.1);
                    }
                """)

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
            # Reset all status indicators to pending
            for row in range(self.url_table.rowCount()):
                # Reset status to pending (⏳)
                status_item = self.url_table.item(row, 2)
                if status_item:
                    status_item.setText("⏳")

            # Get private mode setting
            private_mode = self.private_mode_btn.isChecked()

            # Use AsyncWorker for non-blocking UI
            self.worker = AsyncWorker(self._open_urls_with_tracking, urls, private_mode)
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
        self.url_counter_label.setText(f"{count} URL{'s' if count != 1 else ''} found")

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
        # No icons - just clean text
        item = QTreeWidgetItem([data["name"]])
        item.setData(0, Qt.ItemDataRole.UserRole, data)

        input_name = data["name"]
        # Normalize name for color lookup (case insensitive)
        norm_name = input_name.lower()

        # Color mapping based on user request (v1.27.1 palette)
        # Default rotation colors if not specified
        default_colors = [
            "#00E5FF",  # Personal (Cyan)
            "#FF1744",  # YouTube (Red)
            "#FFEA00",  # Guides (Yellow)
            "#B388FF",  # GitHub (Purple)
            "#00FF85",  # Random (Green)
        ]

        # Specific color overrides (user-defined)
        specific_colors = {
            "personal": "#00E5FF",
            "youtube": "#FF1744",
            "guides": "#FFEA00",
            "github": "#B388FF",
            "random": "#00FF85",
        }

        # Apply font styling directly to the item - bigger text
        font = item.font(0)
        font.setBold(is_folder)
        font.setPointSize(18 if is_folder else 14)  # Larger font sizes
        item.setFont(0, font)

        # Apply color to folders
        if is_folder:
            if norm_name in specific_colors:
                color = specific_colors[norm_name]
            else:
                # Get folder index for color rotation
                if not hasattr(self, "_folder_color_index"):
                    self._folder_color_index = 0
                color = default_colors[self._folder_color_index % len(default_colors)]
                self._folder_color_index += 1

            item.setForeground(0, QColor(color))
            item.setFlags(
                item.flags() & ~Qt.ItemFlag.ItemIsEditable
            )  # Folders not editable inline
        else:
            # Bookmarks are gray
            item.setForeground(0, QColor("#aaaaaa"))
            # Make sure bookmarks are NOT editable
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

        # Migration: Rename "AI News" to "News" if it exists
        ai_news_node = next(
            (
                n
                for n in bookmark_nodes
                if isinstance(n, BookmarkFolder) and n.name == "AI News"
            ),
            None,
        )
        if ai_news_node:
            ai_news_node.name = "News"
            self.bookmark_manager.save_bookmarks(bookmark_nodes)

        # Ensure all required default folders exist
        required_folders = ["News", "Apple", "Misc", "Google", "Github", "Fun"]
        existing_names = {
            n.name for n in bookmark_nodes if isinstance(n, BookmarkFolder)
        }

        folders_added = False
        for req_name in required_folders:
            if req_name not in existing_names:
                bookmark_nodes.append(BookmarkFolder(name=req_name, children=[]))
                folders_added = True

        if folders_added:
            self.bookmark_manager.save_bookmarks(bookmark_nodes)

        # Sort bookmarks alphabetically by name
        bookmark_nodes.sort(key=lambda x: x.name.lower())
        for node in bookmark_nodes:
            node_data = self.bookmark_manager._serialize_node(node)
            item = self._create_tree_item(node_data)
            item.setExpanded(True)

    def _show_bookmark_context_menu(self, position):
        """Shows a context menu for bookmark items with relevant actions."""
        item = self.bookmark_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        # Apply theme styling to the context menu
        menu.setStyleSheet(
            f"""
            QMenu {{
                background-color: #2a2a2a;
                color: #fff;
                border: 1px solid {self.current_theme["bookmarks"]["primary"]}; # Use bookmarks primary
                border-radius: 5px;
            }}
            QMenu::item:selected {{
                background-color: {self.current_theme["bookmarks"]["primary"]};
                color: #000;
            }}
        """
        )

        data = item.data(0, Qt.ItemDataRole.UserRole)
        item_type = data.get("type") if data else None

        if item_type == "bookmark":
            open_action = menu.addAction("🌐 Open in Safari")
            open_action.triggered.connect(lambda: self._open_bookmark_link(item))
            menu.addSeparator()

        edit_action = menu.addAction("✏️ Rename")
        edit_action.triggered.connect(lambda: self.bookmark_tree.editItem(item))

        if item_type == "folder":
            add_bookmark_action = menu.addAction("🔗 Add Bookmark to Folder")
            add_bookmark_action.triggered.connect(lambda: self._add_bookmark_link(item))
            add_folder_action = menu.addAction("📁 Add Subfolder")
            add_folder_action.triggered.connect(self.add_bookmark_section)

        delete_action = menu.addAction("🗑️ Delete")
        delete_action.triggered.connect(lambda: self._delete_bookmark_item(item))

        menu.exec(self.bookmark_tree.viewport().mapToGlobal(position))

    def _open_bookmark_link(self, item: QTreeWidgetItem):
        """Opens a bookmark URL in existing Safari window with privacy settings."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "bookmark":
            url = data.get("url")
            if url:
                # Get private mode setting
                private_mode = self.private_mode_btn.isChecked()
                # Use AsyncWorker for non-blocking UI - opens in same Safari window
                self.worker = AsyncWorker(
                    self._open_bookmark_in_existing_window, [url], private_mode
                )
                self.worker.start()

    async def _open_bookmark_in_existing_window(
        self, urls: list[str], private_mode: bool = True
    ) -> bool:
        """Opens bookmark URLs in Safari, creating window if needed."""
        if not urls:
            return False

        processed_urls = [url.replace('"', '\\"') for url in urls]
        script_parts = ['tell application "Safari"', "activate"]

        # Check if Safari has any windows, create one if needed
        script_parts.extend(
            ["if (count of windows) = 0 then", "    make new document", "end if"]
        )

        # Add URLs as new tabs
        for i, url in enumerate(processed_urls):
            if i == 0:
                # First URL goes to current/new window
                script_parts.append(f'set URL of front document to "{url}"')
            else:
                # Additional URLs as new tabs
                script_parts.extend(
                    [
                        "delay 0.5",
                        f'tell front window to make new tab with properties {{URL:"{url}"}}',
                    ]
                )

        script_parts.append("end tell")
        applescript = "\n".join(script_parts)

        try:
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                applescript,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=Config.REQUEST_TIMEOUT
            )
            if process.returncode == 0:
                logger.info(
                    "Successfully opened %d bookmark URLs.", len(processed_urls)
                )
                return True
            logger.error("Safari AppleScript error: %s", stderr.decode())
            return False
        except (TimeoutError, OSError) as e:
            logger.error("Error opening bookmark URLs: %s", e)
            return False

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

    def _toggle_private_mode(self):
        """Toggle private mode setting and update button text."""
        is_private = self.private_mode_btn.isChecked()
        self.private_mode_btn.setText(
            f"🔒 Private Mode: {'ON' if is_private else 'OFF'}"
        )
        logger.info("Private mode %s", "enabled" if is_private else "disabled")

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
