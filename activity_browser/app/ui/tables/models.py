# -*- coding: utf-8 -*-
from pandas import DataFrame
from PyQt5.QtCore import QAbstractTableModel, Qt, QVariant
from PyQt5.QtGui import QBrush

from ..style import style_item
from .delegates import FloatDelegate, StringDelegate


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
        if index.isValid():
            if role == Qt.DisplayRole:
                value = self._dataframe.iloc[index.row(), index.column()]
                try:
                    return QVariant(float(value))
                except:
                    return QVariant(str(value))

            if role == Qt.ForegroundRole:
                col_name = self._dataframe.columns[index.column()]
                return QBrush(style_item.brushes.get(col_name, style_item.brushes.get("default")))

        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._dataframe.columns[section]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self._dataframe.index[section]
        return None


class EditablePandasModel(PandasModel):
    """ Allows underlying dataframe to be edited through Delegate classes.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def flags(self, index):
        """ Returns ItemIsEditable flag
        """
        return Qt.ItemIsEditable

    def setData(self, index, value, role = Qt.EditRole):
        """"""
        return False


class DragPandasModel(PandasModel):
    """Same as PandasModel, but enabling dragging.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def flags(self, index):
        return Qt.ItemIsDragEnabled | Qt.ItemIsSelectable | Qt.ItemIsEnabled


class EditableDragPandasModel(EditablePandasModel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def flags(self, index):
        return Qt.ItemIsDragEnabled | Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable
