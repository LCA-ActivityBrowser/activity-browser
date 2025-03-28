from typing import Callable, Union, List, Tuple

from qtpy import QtWidgets
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtGui import QBrush

ComboBoxItem = Union[str, Tuple[str, str], Tuple[str, str, QBrush]]


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):
    """
    A combobox delegate for use where items are scoped to a list of items
    """

    def __init__(self, item_source: Union[List[ComboBoxItem], Callable[[], list[ComboBoxItem]]], parent=None):
        """
        :param item_source: List of items to be shown in the combo box or a callable
                        returning the items, to allow the delegate to update the
                        list of items in the combobox.
                        An item can be:
                            - a string
                            - a display string - value string pair
                            - a display string, value string and text color (QBrush) triple
        """
        super(ComboBoxDelegate, self).__init__(parent)
        self.item_source = item_source  # List of items to be shown in the combo box
        self._early_commit_item_text = ""

    def set_early_commit_item(self, item_text: str):
        """Set the early commit trigger."""
        self._early_commit_item_text = item_text

    def createEditor(self, parent, option, index):
        # Get them item list
        if callable(self.item_source):
            raw_items = self.item_source()
        else:
            raw_items = self.item_source
        # Extract the colors, if provided
        item_colors = [item[2] if len(item) == 3 else None for item in raw_items]
        # Create the items in form of (str, str)
        items: list[tuple[str, str]] = []
        for item in raw_items:
            if isinstance(item, str):
                items.append((item, item))
            else:
                items.append((item[0], item[1]))

        self.item_values = [item[1] for item in items]
        editor = QtWidgets.QComboBox(parent)
        for item in items:
            userdata = None
            if not isinstance(item, str):
                item, userdata = item
            editor.addItem(item, userdata)
        editor.setCurrentIndex(self.item_values.index(index.data()))
        # Set the colors for the entries
        for i, brush in enumerate(item_colors):
            if brush is not None:
                editor.setItemData(i, brush, QtCore.Qt.ForegroundRole)
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
