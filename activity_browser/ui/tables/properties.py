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
        self._model.rowsInserted.connect(self._handle_rows_inserted)

        self.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().resizeSection(2, 40)

    def populate(self, data: Optional[dict[str, float]]) -> None:
        """Load the data into the table"""
        self._model.populate(data)
        for i in range(self._model.rowCount()):
            index = self._model.createIndex(i, 2)
            self.openPersistentEditor(index)

    def _handle_rows_inserted(self, parent: QtCore.QModelIndex, first: int, last: int):
        """Show the delete row delegates for new rows"""
        # first , last are inclusive
        for i in range(first, last + 1):
            index = self._model.createIndex(i, 2)
            self.openPersistentEditor(index)
