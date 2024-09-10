from typing import Union, List, Tuple

from PySide2 import QtWidgets
from PySide2.QtCore import Qt


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):
    """
    A combobox delegate for use where items are scoped to a list of items
    """

    def __init__(self, items: Union[List[str], List[Tuple[str, str]]], parent=None):
        """
        :param items: List of items to be shown in the combo box
        """
        super(ComboBoxDelegate, self).__init__(parent)
        self.items = items  # List of items to be shown in the combo box
        if isinstance(self.items[0], str):
            self.items = [(item, item) for item in self.items]
        self.item_keys = [item[0] for item in self.items]
        self.item_values = [item[1] for item in self.items]

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        for item in self.items:
            userdata = None
            if not isinstance(item, str):
                item, userdata = item
            editor.addItem(item, userdata)
        editor.setCurrentIndex(self.item_values.index(index.data()))
        return editor

    def setEditorData(self, editor, index):
        # hides the items in the background for tables views
        editor.setAutoFillBackground(True)
        current_text = index.model().data(index, Qt.EditRole)
        current_index = editor.findText(current_text)
        if current_index >= 0:
            editor.setCurrentIndex(current_index)

    def setModelData(self, editor, model, index):
        model.setData(index, self.item_values[editor.currentIndex()], Qt.EditRole)
