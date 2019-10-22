# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets


class CheckboxDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None

    def paint(self, painter, option, index):
        """ Paint the cell with a styled option button, showing a checkbox

        See links below for inspiration:
        https://stackoverflow.com/a/11778012
        https://stackoverflow.com/q/15235273
        """
        painter.save()
        value = bool(index.data(QtCore.Qt.DisplayRole))
        button = QtWidgets.QStyleOptionButton()
        button.state = QtWidgets.QStyle.State_Enabled
        button.state |= QtWidgets.QStyle.State_Off if not value else QtWidgets.QStyle.State_On
        button.rect = option.rect
        # button.text = "False" if not value else "True"  # This also adds text
        QtWidgets.QApplication.style().drawPrimitive(
            QtWidgets.QStyle.PE_IndicatorCheckBox, button, painter
        )
        painter.restore()
