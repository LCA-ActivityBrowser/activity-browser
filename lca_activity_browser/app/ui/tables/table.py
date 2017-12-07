# -*- coding: utf-8 -*-
from ...signals import signals
from PyQt5 import QtCore, QtWidgets


class ABTableItem(QtWidgets.QTableWidgetItem):
    def __init__(self, text, **kwargs):
        super(ABTableItem, self).__init__(text)
        self.database = kwargs.get('database')
        self.key = kwargs.get('key')
        self.exchange = kwargs.get('exchange')
        self.direction = kwargs.get('direction')
        self.editable = kwargs.get('editable') or False
        if self.editable:
            self.setFlags(self.flags() | QtCore.Qt.ItemIsEditable)
            self.previous = self.text()
        else:
            self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)  # existing flags, but not editable


class ABTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None, *args):
        super(ABTableWidget, self).__init__(parent)
        # same in all tables:
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def sync(self):
        self.clear()

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

            elif e.key() == QtCore.Qt.Key_V: # paste
                pass

