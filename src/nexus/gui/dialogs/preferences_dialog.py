"""Preferences panel dialog for Nexus."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nexus.core.config import Config
from nexus.gui.theme import get_theme_manager


class PreferencesDialog(QDialog):
    """Multi-tab application preferences panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(560, 480)

        self.settings = QSettings("Nexus", "Nexus")

        esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        esc_shortcut.activated.connect(self.close)

        self._build_ui()
        self._load_settings()
        self._apply_theme()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 18, 20, 18)
        main_layout.setSpacing(14)

        # Tabs
        self.tabs = QTabWidget(self)

        self.tabs.addTab(self._create_appearance_tab(), "Appearance")
        self.tabs.addTab(self._create_safari_tab(), "Safari")
        self.tabs.addTab(self._create_privacy_tab(), "Privacy")
        self.tabs.addTab(self._create_rich_links_tab(), "Rich Links")
        self.tabs.addTab(self._create_storage_tab(), "Storage & Data")

        main_layout.addWidget(self.tabs, 1)

        # Dialog Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        apply_btn = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_btn:
            apply_btn.clicked.connect(self._save_settings)

        main_layout.addWidget(buttons)

    def _create_appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.theme_mode_combo = QComboBox()
        self.theme_mode_combo.addItem("System (Sync with macOS)", "system")
        self.theme_mode_combo.addItem("Dark Mode (Cosmic Obsidian)", "dark")
        self.theme_mode_combo.addItem("Light Mode (Frosted Lumina)", "light")
        form.addRow("Appearance:", self.theme_mode_combo)

        self.palette_combo = QComboBox()
        for name in (
            "Midnight Blue",
            "Celestial Purple",
            "Emerald Lagoon",
            "Sunset Blaze",
            "Monochrome Steel",
        ):
            self.palette_combo.addItem(name, name)
        form.addRow("Color Scheme:", self.palette_combo)

        layout.addLayout(form)

        info_box = QGroupBox("Dynamic Glass Effects")
        info_layout = QVBoxLayout(info_box)
        self.starfield_check = QCheckBox(
            "Enable shooting star particles in window shell"
        )
        self.starfield_check.setChecked(True)
        info_layout.addWidget(self.starfield_check)
        layout.addWidget(info_box)

        layout.addStretch()
        return widget

    def _create_safari_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 100)
        self.batch_size_spin.setValue(20)
        form.addRow("Batch Size (Tabs per Window):", self.batch_size_spin)

        self.delay_min_spin = QDoubleSpinBox()
        self.delay_min_spin.setRange(0.1, 5.0)
        self.delay_min_spin.setSingleStep(0.05)
        self.delay_min_spin.setSuffix(" s")
        form.addRow("Min Pacing Delay:", self.delay_min_spin)

        self.delay_max_spin = QDoubleSpinBox()
        self.delay_max_spin.setRange(0.1, 10.0)
        self.delay_max_spin.setSingleStep(0.05)
        self.delay_max_spin.setSuffix(" s")
        form.addRow("Max Pacing Delay:", self.delay_max_spin)

        layout.addLayout(form)

        opt_box = QGroupBox("Safari Automation Options")
        opt_layout = QVBoxLayout(opt_box)
        self.stealth_check = QCheckBox(
            "Anti-Detection Stealth Mode (Domain Staggering)"
        )
        self.stealth_check.setChecked(Config.STEALTH_MODE)
        self.private_mode_check = QCheckBox(
            "Open URLs in Private Browsing Windows by default"
        )
        opt_layout.addWidget(self.stealth_check)
        opt_layout.addWidget(self.private_mode_check)
        layout.addWidget(opt_box)

        layout.addStretch()
        return widget

    def _create_privacy_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        box = QGroupBox("Privacy & Clipboard Ingest")
        box_layout = QVBoxLayout(box)

        self.clipboard_monitor_check = QCheckBox(
            "Auto-detect and ingest copied links from system clipboard"
        )
        self.clipboard_monitor_check.setChecked(True)
        box_layout.addWidget(self.clipboard_monitor_check)

        self.auto_cleanup_logs_check = QCheckBox(
            "Automatically sanitize/cleanup logs after URL operations"
        )
        self.auto_cleanup_logs_check.setChecked(True)
        box_layout.addWidget(self.auto_cleanup_logs_check)

        self.anonymize_check = QCheckBox(
            "Anonymize URLs in logs with SHA-256 fingerprinting"
        )
        self.anonymize_check.setChecked(True)
        box_layout.addWidget(self.anonymize_check)

        layout.addWidget(box)
        layout.addStretch()
        return widget

    def _create_rich_links_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        box = QGroupBox("Copy Rich Links Formatting")
        box_layout = QVBoxLayout(box)

        self.skip_duplicates_check = QCheckBox("Skip duplicate URLs when copying")
        box_layout.addWidget(self.skip_duplicates_check)

        self.sort_alpha_check = QCheckBox("Sort copied links alphabetically")
        box_layout.addWidget(self.sort_alpha_check)

        self.preserve_blanks_check = QCheckBox("Preserve blank separator lines")
        box_layout.addWidget(self.preserve_blanks_check)

        layout.addWidget(box)
        layout.addStretch()
        return widget

    def _create_storage_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        data_dir = Path.home() / "Library" / "Application Support" / "Nexus"
        self.path_edit = QLineEdit(str(data_dir))
        self.path_edit.setReadOnly(True)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit)

        reveal_btn = QPushButton("Reveal in Finder")
        reveal_btn.clicked.connect(self._reveal_data_dir)
        path_layout.addWidget(reveal_btn)

        form.addRow("Application Data:", path_layout)

        self.backup_count_spin = QSpinBox()
        self.backup_count_spin.setRange(1, 50)
        self.backup_count_spin.setValue(7)
        form.addRow("Backup Copies to Retain:", self.backup_count_spin)

        layout.addLayout(form)
        layout.addStretch()
        return widget

    def _reveal_data_dir(self) -> None:
        data_dir = Path.home() / "Library" / "Application Support" / "Nexus"
        data_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir)))

    def _load_settings(self) -> None:
        # Appearance
        mode = str(self.settings.value("theme/mode", "dark"))
        idx = self.theme_mode_combo.findData(mode)
        if idx >= 0:
            self.theme_mode_combo.setCurrentIndex(idx)

        palette = str(self.settings.value("theme/name", "Midnight Blue"))
        idx = self.palette_combo.findData(palette)
        if idx >= 0:
            self.palette_combo.setCurrentIndex(idx)

        # Safari
        self.batch_size_spin.setValue(
            int(str(self.settings.value("safari/batchSize", 20)))
        )
        self.delay_min_spin.setValue(
            float(
                str(
                    self.settings.value("safari/delayMin", Config.URL_OPENING_DELAY_MIN)
                )
            )
        )
        self.delay_max_spin.setValue(
            float(
                str(
                    self.settings.value("safari/delayMax", Config.URL_OPENING_DELAY_MAX)
                )
            )
        )
        self.stealth_check.setChecked(
            bool(self.settings.value("safari/stealthMode", Config.STEALTH_MODE))
        )
        self.private_mode_check.setChecked(
            bool(self.settings.value("safari/defaultPrivateMode", False))
        )

        # Privacy
        self.clipboard_monitor_check.setChecked(
            bool(self.settings.value("privacy/autoMonitorClipboard", True))
        )
        self.auto_cleanup_logs_check.setChecked(
            bool(self.settings.value("privacy/autoLogCleanup", True))
        )

        # Rich Links
        self.skip_duplicates_check.setChecked(
            bool(self.settings.value("richLinks/skipDuplicates", True))
        )
        self.sort_alpha_check.setChecked(
            bool(self.settings.value("richLinks/sortAlpha", False))
        )
        self.preserve_blanks_check.setChecked(
            bool(self.settings.value("richLinks/preserveBlanks", True))
        )

        # Storage
        self.backup_count_spin.setValue(
            int(str(self.settings.value("backup/retentionCount", 7)))
        )

    def _save_settings(self) -> None:
        new_mode = self.theme_mode_combo.currentData()
        self.settings.setValue("theme/mode", new_mode)
        self.settings.setValue("theme/name", self.palette_combo.currentData())

        # Update global theme manager
        tm = get_theme_manager()
        tm.set_mode(new_mode)

        # Safari
        self.settings.setValue("safari/batchSize", self.batch_size_spin.value())
        self.settings.setValue("safari/delayMin", self.delay_min_spin.value())
        self.settings.setValue("safari/delayMax", self.delay_max_spin.value())
        self.settings.setValue("safari/stealthMode", self.stealth_check.isChecked())
        self.settings.setValue(
            "safari/defaultPrivateMode", self.private_mode_check.isChecked()
        )

        # Privacy
        self.settings.setValue(
            "privacy/autoMonitorClipboard", self.clipboard_monitor_check.isChecked()
        )
        self.settings.setValue(
            "privacy/autoLogCleanup", self.auto_cleanup_logs_check.isChecked()
        )

        # Rich Links
        self.settings.setValue(
            "richLinks/skipDuplicates", self.skip_duplicates_check.isChecked()
        )
        self.settings.setValue("richLinks/sortAlpha", self.sort_alpha_check.isChecked())
        self.settings.setValue(
            "richLinks/preserveBlanks", self.preserve_blanks_check.isChecked()
        )

        # Storage
        self.settings.setValue("backup/retentionCount", self.backup_count_spin.value())

    def _on_accept(self) -> None:
        self._save_settings()
        self.accept()

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
            QGroupBox {{
                color: {t.text_accent};
                border: 1px solid {t.card_border};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
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
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {t.input_bg};
                color: {t.input_text};
                border: 1px solid {t.input_border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {t.input_focus_border};
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
            QCheckBox {{
                color: {t.text_primary};
                spacing: 8px;
            }}
            """
        )
