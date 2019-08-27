# -*- coding: utf-8 -*-
import numpy as np
from pandas import DataFrame
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QBrush

from ..style import style_item
from ...bwutils.commontasks import AB_names_to_bw_keys


class PandasModel(QAbstractTableModel):
    """ Abstract pandas table model adapted from
    https://stackoverflow.com/a/42955764.
    """
    def __init__(self, dataframe: DataFrame, parent=None):
        super().__init__(parent)
        self._dataframe = dataframe

    def rowCount(self, parent=None):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None):
        return self._dataframe.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            value = self._dataframe.iat[index.row(), index.column()]
            if isinstance(value, np.float):
                value = float(value)
            elif isinstance(value, np.bool_):
                value = bool(value)
            elif isinstance(value, np.int64):
                value = int(value)
            elif isinstance(value, tuple):
                value = str(value)
            return QVariant() if value is None else QVariant(value)

        if role == Qt.ForegroundRole:
            col_name = self._dataframe.columns[index.column()]
            if col_name not in style_item.brushes:
                col_name = AB_names_to_bw_keys.get(col_name, "")
            return QBrush(style_item.brushes.get(col_name, style_item.brushes.get("default")))

        return QVariant()

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._dataframe.columns[section]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self._dataframe.index[section]
        return None

    def to_clipboard(self, rows, columns):
        """ Copy the given rows and columns of the dataframe to clipboard
        """
        self._dataframe.iloc[rows, columns].to_clipboard(index=False)


class SimpleCopyPandasModel(PandasModel):
    """ Override the to_clipboard method to exclude copying table headers
    """
    def to_clipboard(self, rows, columns):
        self._dataframe.iloc[rows, columns].to_clipboard(
            index=False, header=False
        )


class EditablePandasModel(PandasModel):
    """ Allows underlying dataframe to be edited through Delegate classes.
    """
    def flags(self, index):
        """ Returns ItemIsEditable flag
        """
        return super().flags(index) | Qt.ItemIsEditable

    def setData(self, index, value, role = Qt.EditRole):
        """ Inserts the given validated data into the given index
        """
        if index.isValid() and role == Qt.EditRole:
            self._dataframe.iat[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False


# Take the classes defined above and add the ItemIsDragEnabled flag
class DragPandasModel(PandasModel):
    """Same as PandasModel, but enabling dragging."""
    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled


class SimpleCopyDragPandasModel(SimpleCopyPandasModel):
    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled


class EditableDragPandasModel(EditablePandasModel):
    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled
