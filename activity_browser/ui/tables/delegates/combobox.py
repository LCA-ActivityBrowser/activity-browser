from typing import Callable, Union, List, Tuple

from PySide2 import QtWidgets
from PySide2.QtCore import Qt

ComboBoxItem = Union[str, Tuple[str, str]]

class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):
    """
    A combobox delegate for use where items are scoped to a list of items
    """

    def __init__(self, item_source: Union[List[ComboBoxItem], Callable[[], list[ComboBoxItem]]], parent=None):
        """
        :param items: List of items to be shown in the combo box. Can be a callable
                        returning the items, to allow the delegate to update the
                        list of items in the combobox.
        """
        super(ComboBoxDelegate, self).__init__(parent)
        self.item_source = item_source  # List of items to be shown in the combo box

    def set_early_commit_item(self, item_text: str):
        """Set the early commit trigger."""
        self._early_commit_item_text = item_text

    def createEditor(self, parent, option, index):
        if callable(self.item_source):
            items = self.item_source()
        else:
            items = self.item_source
        if isinstance(items[0], str):
            items = [(item, item) for item in items]
        self.item_values = [item[1] for item in items]
        editor = QtWidgets.QComboBox(parent)
        for item in items:
            userdata = None
            if not isinstance(item, str):
                item, userdata = item
            editor.addItem(item, userdata)
        editor.setCurrentIndex(self.item_values.index(index.data()))
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

    def setEditorData(self, editor, index):
        # hides the items in the background for tables views
        editor.setAutoFillBackground(True)
        current_text = index.model().data(index, Qt.EditRole)
        current_index = editor.findText(current_text)
        if current_index >= 0:
            editor.setCurrentIndex(current_index)

    def setModelData(self, editor, model, index):
        model.setData(index, self.item_values[editor.currentIndex()], Qt.EditRole)
