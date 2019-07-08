# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui

from ..style import style_item


class PandasModel(QtCore.QAbstractTableModel):
    """
    adapted from https://stackoverflow.com/a/42955764
    """
    def __init__(self, dataframe, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=None):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None):
        return self._dataframe.shape[1]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                value = self._dataframe.iloc[index.row(), index.column()]
                try:
                    return QtCore.QVariant(float(value))
                except:
                    return QtCore.QVariant(str(value))
                # if type(value) == np.float64:  # QVariant cannot use the pandas/numpy float64 type
                #     value = float(value)
                # else:
                #     # this enables to show also tuples (e.g. category information like ('air', 'urban air') )
                #     value = str(value)
                # return QtCore.QVariant(value)

            if role == QtCore.Qt.ForegroundRole:
                col_name = self._dataframe.columns[index.column()]
                return QtGui.QBrush(style_item.brushes.get(col_name, style_item.brushes.get("default")))

        return None

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._dataframe.columns[section]
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self._dataframe.index[section]
        return None


class DragPandasModel(PandasModel):
    """Same as PandasModel, but enabling dragging."""
    def __init__(self, parent=None):
        super(DragPandasModel, self).__init__(parent)

    def flags(self, index):
        # return QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDropEnabled
        return QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
