# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets
from ..style import style_item
from ...signals import signals


class ABTableItem(QtWidgets.QTableWidgetItem):
    def __init__(self, text, **kwargs):
        super(ABTableItem, self).__init__(text)

        self.previous = text  # for going back to this value if the new text does not make sense

        # assign attributes, e.g. "database", "key", "exchange", "direction", "editable"
        for k, v in kwargs.items():
            setattr(self, k, v)

        # Default flags
        self.setFlags(self.flags() | QtCore.Qt.ItemIsSelectable)
        self.setFlags(self.flags() | QtCore.Qt.ItemIsEnabled)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsUserCheckable)
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsTristate)

        if hasattr(self, "set_flags"):
            for f in self.set_flags:
                self.setFlags(self.flags() | f)  # toggle flag state

        if self.flags() & QtCore.Qt.ItemIsUserCheckable:
            self.setCheckState(QtCore.Qt.Unchecked)

        if hasattr(self, "color"):
            self.setForeground(
                style_item.brushes.get(self.color, style_item.brushes.get("default"))
            )


class ABTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None, *args):
        super(ABTableWidget, self).__init__(parent)
        # same in all tables:
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.setSortingEnabled(True)
        # self.setSizePolicy(QtWidgets.QSizePolicy(
        #     QtWidgets.QSizePolicy.Preferred,
        #     QtWidgets.QSizePolicy.Maximum)
        # )

    @classmethod  # needs to be a classmethod for decorating subclass methods
    def decorated_sync(cls, sync):
        """ A wrapper for the tables' sync method to do generic stuff
        before and after the individual tables' sync method."""
        def wrapper(self, *args, **kwargs):
            # before making the table
            self.clear()
            # the actual sync
            sync(self, *args, **kwargs)
            # after syncing
            self.resizeColumnsToContents()
            self.resizeRowsToContents()
            if self.rowCount() > 0:
                self.setMaximumHeight(
                    self.rowHeight(0) * (self.rowCount() + 1) + self.autoScrollMargin()
                )
            else:
                self.setMaximumHeight(50)
        return wrapper

    def sizeHint(self):
        """ Could be implemented like this to return the width and heights of the table. """
        if self.rowCount() > 0:
            height = self.rowHeight(0) * (self.rowCount() + 1) + self.autoScrollMargin()
            # print("Size Hint:", height)
            return QtCore.QSize(self.width(), height)
        else:
            return QtCore.QSize(self.width(), 50)

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
        else:
            QtWidgets.QTableWidget.keyPressEvent(self, e)
