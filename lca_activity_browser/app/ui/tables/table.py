# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets
from ...signals import signals


class ABTableItem(QtWidgets.QTableWidgetItem):
    def __init__(self, text, **kwargs):
        super(ABTableItem, self).__init__(text)
        # assign attributes, e.g. "database", "key", "exchange", "direction", "editable"
        for k, v in kwargs.items():
            setattr(self, k, v)
        if hasattr(self, "editable"):
            if self.editable:
                self.setFlags(self.flags() | QtCore.Qt.ItemIsEditable)
                self.previous = self.text()
        else:
            self.editable = False
            self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)  # existing flags, but not editable


class ABTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None, *args):
        super(ABTableWidget, self).__init__(parent)
        # same in all tables:
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def sync(self):
        self.clear()

    def resize_custom(self):
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.setMaximumHeight(self.rowHeight(0) * (self.rowCount() + 1) + self.autoScrollMargin())

    @QtCore.pyqtSlot()
    def keyPressEvent(self, e):
        if e.modifiers() and QtCore.Qt.ControlModifier:
            selected = self.selectedRanges()

            if e.key() == QtCore.Qt.Key_C:  # copy
                s = ""
                for r in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                    for c in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        try:
                            s += str(self.item(r, c).text()) + "\t"
                        except AttributeError:
                            s += "\t"
                    s = s[:-1] + "\n"  # eliminate last '\t'
                signals.copy_selection_to_clipboard.emit(s)

            elif e.key() == QtCore.Qt.Key_V:  # paste
                pass
