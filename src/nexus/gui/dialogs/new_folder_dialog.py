"""New Folder dialog: a name field plus a swatch palette for color picking.

The "Custom…" option opens :class:`QColorDialog` and returns the user-picked
hex.  Picking a palette swatch is instant; the dialog itself does not run an
event loop — callers must ``.exec()`` it.
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


# 10 default-tab accent colors.  Order matches the sidebar in
# ``docs/superpowers/specs/2026-07-16-bookmark-groups-design.md``.
DEFAULT_PALETTE: tuple[str, ...] = (
    "#E5738A",  # Fun     (pink)
    "#D4A05A",  # Misc    (orange)
    "#5B8DEF",  # Tech    (blue)
    "#E85A5A",  # Work    (red)
    "#8A95A8",  # Extra   (grey)
    "#A87A5A",  # Warm brown
    "#2A2A35",  # Hidden  (black)
    "#F0F4FA",  # Special (white)
    "#5BA86A",  # Favorites (green)
    "#6B6B7A",  # Sort    (slate)
)


class NewFolderDialog(QDialog):
    """Modal: a name field and a swatch combo box for the folder accent."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Folder")
        self.setModal(True)

        self._name_input = QLineEdit(self)
        self._name_input.setMaxLength(40)
        self._name_input.setPlaceholderText("Folder name")
        self._name_input.textChanged.connect(self._sync_ok_state)

        self._accent_combo = QComboBox(self)
        for hex_ in DEFAULT_PALETTE:
            self._accent_combo.addItem(hex_.upper(), hex_)
        self._accent_combo.addItem("Custom…", "__custom__")
        self._accent_combo.currentIndexChanged.connect(self._on_combo_changed)

        form = QFormLayout()
        form.addRow("Folder name:", self._name_input)
        form.addRow("Color:", self._accent_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._custom_color: str | None = None
        self._sync_ok_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def folder_name(self) -> str:
        return self._name_input.text().strip()

    @folder_name.setter
    def folder_name(self, value: str) -> None:
        self._name_input.setText(value)

    @property
    def accent(self) -> str:
        if self._accent_combo.currentData() == "__custom__":
            return self._custom_color or DEFAULT_PALETTE[0]
        return str(self._accent_combo.currentData())

    @accent.setter
    def accent(self, value: str) -> None:
        idx = self._accent_combo.findData(value)
        if idx >= 0:
            self._accent_combo.setCurrentIndex(idx)
            return
        # Custom hex — stash it and switch to the "Custom…" entry without
        # triggering the QColorDialog that ``_on_combo_changed`` would
        # otherwise open.  Programmatic callers want the setter to be
        # non-interactive.
        self._custom_color = value
        custom_idx = self._accent_combo.findData("__custom__")
        self._accent_combo.blockSignals(True)
        self._accent_combo.setCurrentIndex(custom_idx)
        self._accent_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sync_ok_state(self) -> None:
        self._ok_button.setEnabled(bool(self._name_input.text().strip()))

    def _on_combo_changed(self, index: int) -> None:
        data = self._accent_combo.itemData(index)
        if data != "__custom__":
            return
        chosen = QColorDialog.getColor(
            QColor(self._custom_color or DEFAULT_PALETTE[0]),
            self,
            "Pick a folder color",
        )
        if chosen.isValid():
            # Persist the picked color and re-select "Custom…" so the
            # ``accent`` getter keeps returning it.  blockSignals prevents
            # a recursive currentIndexChanged -> _on_combo_changed.
            self._custom_color = chosen.name()
            self._accent_combo.blockSignals(True)
            self._accent_combo.setCurrentIndex(index)
            self._accent_combo.blockSignals(False)
            return
        # User cancelled the color dialog — revert the combo to the
        # previously chosen palette color.
        self._accent_combo.blockSignals(True)
        self._accent_combo.setCurrentIndex(max(0, index - 1))
        self._accent_combo.blockSignals(False)
