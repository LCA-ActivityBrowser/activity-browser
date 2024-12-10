# -*- coding: utf-8 -*-
from typing import Any, MutableMapping, Optional

from qtpy import QtWidgets

from activity_browser.ui.tables.tags import TagTable


class TagEditor(QtWidgets.QDialog):
    """Tag editor dialog"""

    def __init__(
        self,
        target: MutableMapping[str, Any] = None,
        tags: Optional[dict[str, Any]] = None,
        read_only: bool = False,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Tag Editor")
        self.setMinimumWidth(400)
        self._tag_table = TagTable(
            tags or {},
            read_only=read_only,
            database=target.get("database"),
            parent=self,
        )
        self._save_button = QtWidgets.QPushButton("Save changes")
        self._save_button.setEnabled(False)

        self._message_label = QtWidgets.QLabel()
        if read_only:
            self._message_label.setText("Read only")
        else:
            self._message_label.setText("No changes yet")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._tag_table)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self._save_button)
        layout.addLayout(button_layout)
        layout.addWidget(self._message_label)
        self.setLayout(layout)

        self._connect_signals()

    def _connect_signals(self):
        self._save_button.clicked.connect(self.accept)
        self._tag_table.model.updated.connect(self._handle_data_changed)
        self._tag_table.model.dataChanged.connect(self._handle_data_changed)

    def tags(self) -> dict[str, Any]:
        """Access method to get the result of the editing"""
        return self._tag_table.model.get_tags()

    def _handle_data_changed(self):
        """Update the message label and enable/disable the save button"""
        if self._tag_table.model.has_duplicate_key():
            self._message_label.setText("Error: there are duplicate tag names")
            self._save_button.setEnabled(False)
        else:
            self._message_label.setText("Modified")
            self._save_button.setEnabled(True)

    @staticmethod
    def edit(
        target: MutableMapping[str, Any],
        read_only: bool,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> bool:
        """
        Opens the tag editor for the tags of the target
        Return True if the tags were changed.
        """
        tags = target.get("tags")
        editor = TagEditor(target, tags, read_only, parent)
        # Do not save the changes if the user pressed cancel
        if editor.exec_() == editor.DialogCode.Accepted:
            target["tags"] = editor.tags()
            return True
        return False
