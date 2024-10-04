# -*- coding: utf-8 -*-
from typing import Optional
from PySide2 import QtCore, QtWidgets

from .delegates import DeleteButtonDelegate, StringDelegate, FloatDelegate
from .models.properties import PropertyModel


class PropertyTable(QtWidgets.QTableView):
    """Table view for editing properties"""
    def __init__(self, model: PropertyModel, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked |
            QtWidgets.QAbstractItemView.EditTrigger.SelectedClicked |
            QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed |
            QtWidgets.QAbstractItemView.EditTrigger.AnyKeyPressed
        )

        self.setItemDelegateForColumn(0, StringDelegate(self))
        # Use FloatDelegate, so that int values do not trigger an int validation
        self.setItemDelegateForColumn(1, FloatDelegate(self))
        delete_delegate = DeleteButtonDelegate(self)
        self.setItemDelegateForColumn(2, delete_delegate)

        self._model = model
        self.setModel(self._model)
        delete_delegate.delete_request.connect(self._model.handle_delete_request)
        self._model.dataChanged.connect(self._handle_data_changed)

        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        # Read-only mode has fewer columns
        if self.model().columnCount() >= 3:
            self.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)
            self.horizontalHeader().resizeSection(2, 40)

    def _show_delete_button_for_row(self, row: int):
        key_index = self._model.index(row, 0)
        index = self._model.index(row, 2)
        # No delete button for the last empty row
        if self.model().data(key_index) != "":
            self.openPersistentEditor(index)

    def populate(self, data: Optional[dict[str, float]]) -> None:
        """Load the data into the table"""
        self._model.populate(data)
        # Read-only mode has fewer columns
        if self.model().columnCount() >= 3:
            for i in range(self._model.rowCount()):
                self._show_delete_button_for_row(i)

    def _handle_data_changed(self, top_left: QtCore.QModelIndex, 
            bottom_right: QtCore.QModelIndex):
        """Show the delete row delegates for new rows"""
        for i in range(top_left.row(), bottom_right.row() + 1):
            self._show_delete_button_for_row(i)
