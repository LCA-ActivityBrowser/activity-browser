# -*- coding: utf-8 -*-
from typing import Callable, Union
from PySide2 import QtCore, QtWidgets


class TextButtonDelegate(QtWidgets.QStyledItemDelegate):
    """For showing a persistent button with a text in tables"""

    clicked = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, label_source: Union[str, Callable[[], str]], parent=None):
        super().__init__(parent)
        self._label_source = label_source

    def createEditor(self,
                     parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem,
                     index: QtCore.QModelIndex):
        button = QtWidgets.QPushButton(parent)
        button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        button.setAutoDefault(False)
        button.clicked.connect(lambda: self.clicked.emit(index))
        return button

    def setEditorData(self, editor, index):
        # hides the items in the background for tables views
        editor.setAutoFillBackground(True)
        current_text = index.data()
        editor.setText(current_text)

    def setModelData(self, editor, model, index):
        # data will be set through clicked signal handler
        pass
