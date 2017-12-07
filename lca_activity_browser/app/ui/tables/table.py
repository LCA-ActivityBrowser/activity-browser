# -*- coding: utf-8 -*-
from ...signals import signals
from PyQt5 import QtCore, QtWidgets



class ABTableWidgetItem(QtWidgets.QTableWidgetItem):
    def __init__(self, parent=None):
        super(ABTableWidgetItem, self).__init__(parent)
        self.activity_or_database_key = None
        self.key_type = None
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)  # existing flags, but not editable
        self.uuid_ = None


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

