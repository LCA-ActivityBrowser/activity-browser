# -*- coding: utf-8 -*-
from pandas import DataFrame
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QBrush
from stats_arrays import uncertainty_choices

from ..style import style_item


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
        """ Reads out and displays the data from the dataframe for each index

        If we're displaying a column called 'uncertainty type', special rules
        apply
        """
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            value = self._dataframe.iloc[index.row(), index.column()]
            if ("uncertainty type" in self._dataframe.columns and
                    self._dataframe.columns[index.column()] == "uncertainty type"):
                value = int(value) if value else 0
                distribution = uncertainty_choices.id_dict[value]
                value = distribution.description
            try:
                return QVariant(float(value))
            except (ValueError, TypeError) as e:
                # Also handle 'None' values from dataframe.
                return QVariant(str(value)) if value else QVariant()

        if role == Qt.ForegroundRole:
            col_name = self._dataframe.columns[index.column()]
            return QBrush(style_item.brushes.get(col_name, style_item.brushes.get("default")))

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def headerData(self, section: int, orientation, role: int=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return self._dataframe.columns[section]
        elif orientation == Qt.Vertical:
            return self._dataframe.index[section]

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
    def __init__(self, dataframe: DataFrame, parent=None):
        super().__init__(dataframe, parent)

    def flags(self, index):
        """ Returns ItemIsEditable flag
        """
        return super().flags(index) | Qt.ItemIsEditable

    def setData(self, index, value, role = Qt.EditRole):
        """ Inserts the given validated data into the given index
        """
        if index.isValid() and role == Qt.EditRole:
            self._dataframe.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False


class DragPandasModel(PandasModel):
    """Same as PandasModel, but enabling dragging.
    """
    def __init__(self, dataframe: DataFrame, parent=None):
        super().__init__(dataframe, parent)

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled


class SimpleCopyDragPandasModel(SimpleCopyPandasModel):
    def __init__(self, dataframe: DataFrame, parent=None):
        super().__init__(dataframe, parent)

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled


class EditableDragPandasModel(EditablePandasModel):
    def __init__(self, dataframe: DataFrame, parent=None):
        super().__init__(dataframe, parent)

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled
