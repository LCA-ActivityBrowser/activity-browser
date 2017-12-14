# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui
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
            self.setForeground(style_item.brushes.get(self.color, (0,0,0)))


class ABTableWidget(QtWidgets.QTableWidget):
    def __init__(self, parent=None, *args):
        super(ABTableWidget, self).__init__(parent)
        # same in all tables:
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.setSortingEnabled(True)

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
            # if self.rowCount() > 0:
            #     self.setMaximumHeight(self.rowHeight(0) * (self.rowCount() + 1) + self.autoScrollMargin())
            # else:
            #     self.setMaximumHeight(50)
        return wrapper

    # def sizeHint(self):
    #     """ Could be implemented like this to return the width and heights of the table. """
    #     width = self.width()
    #     if self.rowCount() > 0:
    #         height = self.rowHeight(0) * (self.rowCount() + 1) + self.autoScrollMargin()
    #         print("Size Hint:", height)
    #         return QtCore.QSize(width, height)
    #     else:
    #         return QtCore.QSize(width, 50)


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


class ABStandardTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None, *args):
        super(ABStandardTable, self).__init__(parent)
        # same in all tables:
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

    def update_table(self, data, keys, edit_keys=None, bold=False):
        """
        A generic method to update (fill) a QTableWidget
        :param data: list of dictionaries
        :param keys: dictionary keys that are to be displayed
        """

        self.clear()
        if not data:
            self.setRowCount(0)
            print("No data passed to table.")
        else:
            self.setSortingEnabled(False)
            self.blockSignals(True)
            # self.setRowCount(len(data))
            # self.setRowCount(10)
            self.setColumnCount(len(keys))
            self.setHorizontalHeaderLabels(keys)

        for row, row_data in enumerate(data):
            for col, key in enumerate(keys):
                self.setItem(row, col, ABTableItem(row_data[key]))

        # for i, d in enumerate(data):
        #     for j in range(len(keys)):
        #         item = ABTableItem(str(d[keys[j]]))
        #         if "key" in d:
        #             item.activity_or_database_key = d["key"]
        #             item.key_type = d["key_type"]
        #         if 'path' in d:
        #             item.path = d['path']
        #         if 'uuid_' in d:
        #             item.uuid_ = d['uuid_']
        #         if edit_keys and keys[j] in edit_keys:
        #             item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        #         # Color
        #         item.setTextColor(QtWidgets.QColor(
        #             *style.colors_table_current_activity.get(
        #             keys[j], (0, 0, 0))))
        #         # Font
        #         if bold:
        #             font = QtWidgets.QFont()
        #             font.setBold(True)
        #             font.setPointSize(9)
        #             item.setFont(font)
        #         self.setItem(i, j, item)
        # if edit_keys:
        #     self.setEditTriggers(QtWidgets.QTableWidget.AllEditTriggers)
        # else:
        #     self.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.blockSignals(False)
        self.setSortingEnabled(True)


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