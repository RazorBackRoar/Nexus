"""Bookmark Health Scanner Dialog for finding duplicates and dead links."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nexus.core.health_scanner import (
    LinkHealthResult,
    find_duplicates,
    scan_dead_links_concurrently,
)
from nexus.gui.theme import get_theme_manager


if TYPE_CHECKING:
    from nexus.core.bookmarks import BookmarkManager
    from nexus.core.group_store import GroupStore


class DeadLinkWorker(QThread):
    """Background worker for checking URL liveness without freezing the UI."""

    progress = Signal(int, int)
    finished_scanning = Signal(list)

    def __init__(self, items: list[tuple[str, str, str]]) -> None:
        super().__init__()
        self.items = items

    def run(self) -> None:
        def on_progress(done: int, total: int) -> None:
            self.progress.emit(done, total)

        results = scan_dead_links_concurrently(
            self.items, max_workers=6, progress_callback=on_progress
        )
        self.finished_scanning.emit(results)


class HealthReportDialog(QDialog):
    """Dialog displaying duplicate bookmarks and dead link report."""

    def __init__(
        self,
        bookmark_manager: BookmarkManager,
        group_store: GroupStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.bookmark_manager = bookmark_manager
        self.group_store = group_store
        self._worker: DeadLinkWorker | None = None

        self.setWindowTitle("Bookmark Health Scanner")
        self.setModal(True)
        self.resize(720, 520)

        esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        esc_shortcut.activated.connect(self.close)

        self._build_ui()
        self._apply_theme()
        self._run_duplicate_scan()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title_label = QLabel("Bookmark Health Scanner")
        title_font = QFont()
        title_font.setPointSize(17)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        header.addWidget(title_label)
        header.addStretch()

        done_btn = QPushButton("Done")
        done_btn.clicked.connect(self.accept)
        header.addWidget(done_btn)
        main_layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget(self)

        # Duplicate tab
        dupe_widget = QWidget()
        dupe_layout = QVBoxLayout(dupe_widget)
        dupe_layout.setContentsMargins(8, 12, 8, 8)
        dupe_layout.setSpacing(10)

        self.dupe_summary = QLabel("Scanning bookmarks for duplicates…")
        self.dupe_summary.setObjectName("summaryLabel")
        dupe_layout.addWidget(self.dupe_summary)

        self.dupe_tree = QTreeWidget()
        self.dupe_tree.setHeaderLabels(["URL / Item Name", "Location", "Copies"])
        self.dupe_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.dupe_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.dupe_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        dupe_layout.addWidget(self.dupe_tree, 1)

        dupe_btn_row = QHBoxLayout()
        self.copy_dupes_btn = QPushButton("Copy Duplicate URLs")
        self.copy_dupes_btn.clicked.connect(self._copy_duplicate_urls)
        self.refresh_dupes_btn = QPushButton("Rescan Duplicates")
        self.refresh_dupes_btn.clicked.connect(self._run_duplicate_scan)
        dupe_btn_row.addWidget(self.copy_dupes_btn)
        dupe_btn_row.addWidget(self.refresh_dupes_btn)
        dupe_btn_row.addStretch()
        dupe_layout.addLayout(dupe_btn_row)

        self.tabs.addTab(dupe_widget, "Duplicate URLs")

        # Dead links tab
        dead_widget = QWidget()
        dead_layout = QVBoxLayout(dead_widget)
        dead_layout.setContentsMargins(8, 12, 8, 8)
        dead_layout.setSpacing(10)

        dead_top = QHBoxLayout()
        self.dead_summary = QLabel("Check links to find unreachable websites or 404 errors.")
        self.dead_summary.setObjectName("summaryLabel")
        dead_top.addWidget(self.dead_summary)
        dead_top.addStretch()

        self.scan_links_btn = QPushButton("Scan Links for Dead URLs")
        self.scan_links_btn.clicked.connect(self._start_dead_link_scan)
        dead_top.addWidget(self.scan_links_btn)
        dead_layout.addLayout(dead_top)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        dead_layout.addWidget(self.progress_bar)

        self.dead_table = QTableWidget()
        self.dead_table.setColumnCount(4)
        self.dead_table.setHorizontalHeaderLabels(["Name", "URL", "Location", "Issue"])
        self.dead_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.dead_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.dead_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.dead_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        dead_layout.addWidget(self.dead_table, 1)

        dead_btn_row = QHBoxLayout()
        self.copy_dead_btn = QPushButton("Copy Dead URLs")
        self.copy_dead_btn.setEnabled(False)
        self.copy_dead_btn.clicked.connect(self._copy_dead_urls)
        dead_btn_row.addWidget(self.copy_dead_btn)
        dead_btn_row.addStretch()
        dead_layout.addLayout(dead_btn_row)

        self.tabs.addTab(dead_widget, "Dead Link Checker")

        main_layout.addWidget(self.tabs, 1)

    def _run_duplicate_scan(self) -> None:
        self.dupe_tree.clear()
        duplicates = find_duplicates(self.bookmark_manager, self.group_store)

        if not duplicates:
            self.dupe_summary.setText("✓ No duplicate bookmark URLs found! Your library is clean.")
            self.copy_dupes_btn.setEnabled(False)
            return

        total_dupes = sum(len(occs) for occs in duplicates.values())
        self.dupe_summary.setText(
            f"Found {len(duplicates)} duplicate URLs ({total_dupes} total bookmark occurrences):"
        )
        self.copy_dupes_btn.setEnabled(True)

        for url, occurrences in sorted(duplicates.items(), key=lambda kv: len(kv[1]), reverse=True):
            parent_item = QTreeWidgetItem(self.dupe_tree)
            parent_item.setText(0, url)
            parent_item.setText(1, "Multiple locations")
            parent_item.setText(2, f"{len(occurrences)} copies")
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)

            for occ in occurrences:
                child_item = QTreeWidgetItem(parent_item)
                child_item.setText(0, occ.name or occ.url)
                child_item.setText(1, occ.container_name)
                child_item.setText(2, occ.container_type)

            parent_item.setExpanded(True)

    def _copy_duplicate_urls(self) -> None:
        duplicates = find_duplicates(self.bookmark_manager, self.group_store)
        if not duplicates:
            return
        text = "\n".join(duplicates.keys())
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)

    def _extract_all_items(self) -> list[tuple[str, str, str]]:
        """Extract all bookmarks as (url, name, container_name) tuples."""
        items: list[tuple[str, str, str]] = []
        try:
            from nexus.core.models import Bookmark, BookmarkFolder

            def _traverse(folder: BookmarkFolder, path: str) -> None:
                curr = f"{path} > {folder.name}" if path else folder.name
                for child in folder.children:
                    if isinstance(child, BookmarkFolder):
                        _traverse(child, curr)
                    elif isinstance(child, Bookmark):
                        if child.url:
                            items.append((child.url, child.name, curr))
                    elif isinstance(child, dict) and child.get("type") == "bookmark":
                        url = child.get("url", "")
                        if url:
                            items.append((url, child.get("name", url), curr))

            for node in self.bookmark_manager.load_bookmarks():
                if isinstance(node, BookmarkFolder):
                    _traverse(node, "")
                elif isinstance(node, Bookmark) and node.url:
                    items.append((node.url, node.name, "Root"))
        except Exception:
            pass

        return items

    def _start_dead_link_scan(self) -> None:
        items = self._extract_all_items()
        if not items:
            self.dead_summary.setText("No bookmarks found to scan.")
            return

        self.scan_links_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(items))
        self.progress_bar.setValue(0)
        self.dead_summary.setText(f"Checking {len(items)} bookmarks for dead links…")
        self.dead_table.setRowCount(0)

        self._worker = DeadLinkWorker(items)
        self._worker.progress.connect(self._on_dead_scan_progress)
        self._worker.finished_scanning.connect(self._on_dead_scan_finished)
        self._worker.start()

    def _on_dead_scan_progress(self, completed: int, total: int) -> None:
        self.progress_bar.setValue(completed)
        self.progress_bar.setFormat(f"Checked {completed} of {total} ({int(completed * 100 / max(1, total))}%)")

    def _on_dead_scan_finished(self, results: list[LinkHealthResult]) -> None:
        self.progress_bar.setVisible(False)
        self.scan_links_btn.setEnabled(True)

        if not results:
            self.dead_summary.setText("✓ All bookmarks responded successfully! No dead links detected.")
            self.copy_dead_btn.setEnabled(False)
            return

        self.dead_summary.setText(f"Found {len(results)} unresponsive or dead links:")
        self.copy_dead_btn.setEnabled(True)
        self.dead_table.setRowCount(len(results))

        for row, res in enumerate(results):
            self.dead_table.setItem(row, 0, QTableWidgetItem(res.name))
            self.dead_table.setItem(row, 1, QTableWidgetItem(res.url))
            self.dead_table.setItem(row, 2, QTableWidgetItem(res.container_name))
            issue = f"HTTP {res.status_code}" if res.status_code else (res.error_message or "Unreachable")
            self.dead_table.setItem(row, 3, QTableWidgetItem(issue))

    def _copy_dead_urls(self) -> None:
        urls: list[str] = []
        for r in range(self.dead_table.rowCount()):
            item = self.dead_table.item(r, 1)
            if item and item.text():
                urls.append(item.text())
        if urls:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText("\n".join(urls))

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
            QLabel#summaryLabel {{
                color: {t.text_secondary};
                font-size: 13px;
            }}
            QTabWidget::pane {{
                border: 1px solid {t.card_border};
                border-radius: 8px;
                background-color: {t.well_bg};
            }}
            QTabBar::tab {{
                background: {t.card_bg};
                color: {t.text_secondary};
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {t.well_bg};
                color: {t.text_primary};
                font-weight: bold;
                border-bottom: 2px solid {t.text_accent};
            }}
            QTreeWidget, QTableWidget {{
                background-color: {t.well_bg};
                color: {t.text_primary};
                border: 1px solid {t.card_border};
                border-radius: 6px;
                gridline-color: {t.card_border};
            }}
            QHeaderView::section {{
                background-color: {t.card_bg};
                color: {t.text_primary};
                padding: 4px 8px;
                border: none;
                border-right: 1px solid {t.card_border};
                border-bottom: 1px solid {t.card_border};
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
            QProgressBar {{
                border: 1px solid {t.card_border};
                border-radius: 6px;
                text-align: center;
                background-color: {t.card_bg};
                color: {t.text_primary};
                height: 18px;
            }}
            QProgressBar::chunk {{
                background-color: {t.status_ready};
                border-radius: 5px;
            }}
            """
        )
