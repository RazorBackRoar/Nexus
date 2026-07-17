"""Save Group dialog: a name field and a target-folder combo box."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)


class SaveGroupDialog(QDialog):
    """Modal: collect a group name and a target tab to drop the group into."""

    def __init__(
        self,
        folders: list[str],
        preselect: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Group")
        self.setModal(True)

        self._name_input = QLineEdit(self)
        self._name_input.setMaxLength(60)
        self._name_input.setPlaceholderText("e.g. Sunday reading")
        self._name_input.textChanged.connect(self._sync_ok_state)

        self._folder_combo = QComboBox(self)
        for name in folders:
            self._folder_combo.addItem(name)
        if preselect and preselect in folders:
            idx = folders.index(preselect)
            self._folder_combo.setCurrentIndex(idx)

        form = QFormLayout()
        form.addRow("Group name:", self._name_input)
        form.addRow("Save into:", self._folder_combo)

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def group_name(self) -> str:
        return self._name_input.text().strip()

    @group_name.setter
    def group_name(self, value: str) -> None:
        self._name_input.setText(value)

    @property
    def target_folder(self) -> str:
        return self._folder_combo.currentText()

    @target_folder.setter
    def target_folder(self, value: str) -> None:
        idx = self._folder_combo.findText(value)
        if idx >= 0:
            self._folder_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sync_ok_state(self) -> None:
        self._ok_button.setEnabled(bool(self._name_input.text().strip()))
