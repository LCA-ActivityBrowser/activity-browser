# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets


class CheckboxDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None

    def paint(self, painter, option, index):
        """Paint the cell with a styled option button, showing a checkbox

        See links below for inspiration:
        https://stackoverflow.com/a/11778012
        https://stackoverflow.com/q/15235273

        NOTE: PyQt 5.9.2 needs to treat OSX different from others.
         qtpy 5.13.1 and higher no longer has this issue.
        """
        painter.save()
        value = bool(index.data(QtCore.Qt.DisplayRole))
        button = QtWidgets.QStyleOptionButton()
        button.state = QtWidgets.QStyle.State_Enabled
        button.state |= (
            QtWidgets.QStyle.State_Off if not value else QtWidgets.QStyle.State_On
        )
        painter.translate(QtCore.QPoint(option.rect.left(), option.rect.center().y()))
        style = option.widget.style()
        style.drawControl(QtWidgets.QStyle.CE_CheckBox, button, painter, option.widget)
        painter.restore()
