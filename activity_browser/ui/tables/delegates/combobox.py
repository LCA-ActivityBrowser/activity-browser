# -*- coding: utf-8 -*-
from typing import Callable, Union
from PySide2 import QtCore, QtWidgets


class ComboboxDelegate(QtWidgets.QStyledItemDelegate):
    """Generic Combobox delegate."""

    def __init__(self, data_source: Union[list[str], Callable[[], list[str]]], parent=None):
        super().__init__(parent)
        self._data_source = data_source
        self._early_commit_item_text = ""

    def set_early_commit_item(self, item_text: str):
        """Set the early commit trigger."""
        self._early_commit_item_text = item_text

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        if callable(self._data_source):
            data = self._data_source()
        else:
            data = self._data_source
        editor.insertItems(0, data)
        if self._early_commit_item_text != "":
            editor.activated.connect(
                lambda index: self._handle_activated(editor, index)
            )
        return editor
    
    def _handle_activated(self, editor: QtWidgets.QComboBox, index: int):
        """
        In case the user selected the early commit item (either by
        clicking with the mouse, or by the arrows when the dropdown is
        closed) the selected text will be commited to the model.

        This allows the model to pop-up an editor dialog when this item 
        is selected (instead of waiting for the user to commit the action
        by hitting enter or clicking away).
        """
        if editor.itemText(index) == self._early_commit_item_text:
            self.commitData.emit(editor)

    def setEditorData(self, editor: QtWidgets.QComboBox, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        value = str(index.data(QtCore.Qt.DisplayRole))
        editor.setCurrentText(value)

    def setModelData(
        self,
        editor: QtWidgets.QComboBox,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        """Take the editor, read the given value and set it in the model."""
        value = editor.currentText()
        model.setData(index, value, QtCore.Qt.EditRole)
