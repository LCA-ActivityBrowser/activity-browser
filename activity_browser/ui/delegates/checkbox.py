# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets


class CheckboxDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return None

    @staticmethod
    def is_checked(state) -> bool:
        if state is None:
            return False
        checked = QtCore.Qt.CheckState.Checked
        if state == checked:
            return True
        return getattr(state, "value", state) == getattr(checked, "value", 2)

    @classmethod
    def _cell_checked(cls, index) -> bool:
        state = index.data(QtCore.Qt.ItemDataRole.CheckStateRole)
        if state is not None:
            return cls.is_checked(state)
        return bool(index.data(QtCore.Qt.ItemDataRole.DisplayRole))

    def paint(self, painter, option, index):
        painter.save()
        checked = self._cell_checked(index)
        button = QtWidgets.QStyleOptionButton()
        button.state = QtWidgets.QStyle.StateFlag.State_Enabled
        button.state |= (
            QtWidgets.QStyle.StateFlag.State_On if checked else QtWidgets.QStyle.StateFlag.State_Off
        )
        button.rect = option.rect
        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
        style.drawControl(
            QtWidgets.QStyle.ControlElement.CE_CheckBox, button, painter, option.widget
        )
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if not index.flags() & QtCore.Qt.ItemFlag.ItemIsUserCheckable:
            return False
        if event.type() != QtCore.QEvent.Type.MouseButtonRelease:
            return False
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        new = (
            QtCore.Qt.CheckState.Unchecked
            if self._cell_checked(index)
            else QtCore.Qt.CheckState.Checked
        )
        return model.setData(index, new, QtCore.Qt.ItemDataRole.CheckStateRole)
