# -*- coding: utf-8 -*-
from typing import Any, MutableMapping, Optional
from PySide2 import QtWidgets

from activity_browser.ui.tables.models.properties import PropertyModel
from activity_browser.ui.tables.properties import PropertyTable


class PropertyEditor(QtWidgets.QDialog):
    """Property editor dialog"""

    def __init__(self, properties: Optional[dict[str, float]], read_only: bool, 
                 parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Property Editor")
        self._data_model = PropertyModel(read_only)
        if not read_only:
            self._data_model.dataChanged.connect(self._handle_data_changed)
        self._editor_table = PropertyTable(self._data_model)
        self._editor_table.populate(properties)
        self._save_button = QtWidgets.QPushButton("Save changes")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self.accept)
        cancel_button = QtWidgets.QPushButton("Close" if read_only else "Cancel")
        cancel_button.clicked.connect(self.reject)

        # Prevent hitting enter in the table from closing the dialog
        self._save_button.setAutoDefault(False)
        cancel_button.setAutoDefault(False)
        self._message_label = QtWidgets.QLabel()
        if read_only:
            self._message_label.setText("Read only")
        else:
            self._message_label.setText("No changes yet")
    
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._editor_table)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self._save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        layout.addWidget(self._message_label)
        self.setLayout(layout)

    def properties(self) -> dict[str, float]:
        """Access method to get the result of the editing"""
        return self._data_model.get_properties()

    def _handle_data_changed(self):
        """Update the message label and enable/disable the save button"""
        if self._data_model.has_duplicate_key():
            self._message_label.setText("Error: there are duplicate property names")
            self._save_button.setEnabled(False)
        else:
            if self._data_model.is_modified():
                self._message_label.setText("Modified")
                self._save_button.setEnabled(True)
            else:
                self._message_label.setText("No changes")
                self._save_button.setEnabled(False)

    @staticmethod
    def edit_properties(target: MutableMapping[str, Any], read_only: bool, 
                        parent: Optional[QtWidgets.QWidget] = None) -> bool:
        """
        Opens the property editor for the properties of the target
        Return True if the properties were changed.
        """
        original_properties = target.get("properties")
        editor = PropertyEditor(original_properties, read_only, parent)
        # Do not save the changes if the user pressed cancel
        if editor.exec_() == editor.DialogCode.Accepted:
            # Get the values modified by the user
            updated_properties = editor.properties()
            changed = True
            # Nothing to do
            if not original_properties and not updated_properties:
                changed = False
            # The user has deleted all properties
            elif original_properties and not updated_properties:
                del target["properties"]
            # There were no properties and the user created some
            elif not original_properties and updated_properties:
                target["properties"] = updated_properties
            else:
                # Properties changed, merge the values, to avoid reordering
                # the unmodified properties
                for property in list(original_properties.keys()):
                    if not property in updated_properties:
                        del original_properties[property]
                original_properties |= updated_properties
            return changed
        return False
        