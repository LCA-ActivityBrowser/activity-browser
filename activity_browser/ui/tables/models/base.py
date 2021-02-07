# -*- coding: utf-8 -*-
from typing import Optional

import numpy as np
import pandas as pd
from PySide2.QtCore import (
    QAbstractItemModel, QAbstractTableModel, QModelIndex,
    QSortFilterProxyModel, Qt
)
from PySide2.QtGui import QBrush

from activity_browser.bwutils import commontasks as bc
from activity_browser.ui.style import style_item


class PandasModel(QAbstractTableModel):
    """ Abstract pandas table model adapted from
    https://stackoverflow.com/a/42955764.
    """
    HEADERS = []

    def __init__(self, df: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self._dataframe: Optional[pd.DataFrame] = df

    def rowCount(self, parent=None, *args, **kwargs):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return self._dataframe.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            value = self._dataframe.iat[index.row(), index.column()]
            if isinstance(value, np.float):
                value = float(value)
            elif isinstance(value, np.bool_):
                value = value.item()
            elif isinstance(value, np.int64):
                value = value.item()
            elif isinstance(value, tuple):
                value = str(value)
            return value

        if role == Qt.ForegroundRole:
            col_name = self._dataframe.columns[index.column()]
            if col_name not in style_item.brushes:
                col_name = bc.AB_names_to_bw_keys.get(col_name, "")
            return QBrush(style_item.brushes.get(col_name, style_item.brushes.get("default")))

        return None

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._dataframe.columns[section]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self._dataframe.index[section]
        return None

    def to_clipboard(self, rows, columns, include_header: bool = False):
        """ Copy the given rows and columns of the dataframe to clipboard
        """
        self._dataframe.iloc[rows, columns].to_clipboard(
            index=False, header=include_header
        )

    def to_excel(self, path: str) -> None:
        """Store the underlying dataframe as excel in the given path"""
        self._dataframe.to_excel(excel_writer=path)

    def sync(self, *args, **kwargs) -> None:
        """(Re)build the dataframe according to the given arguments."""
        self._dataframe = pd.DataFrame([], columns=self.HEADERS)

    def refresh_model(self) -> None:
        """Rebuild the proxy model after the underlying model has been changed."""
        parent = self.parent()
        if parent is None:
            return
        parent.proxy_model = QSortFilterProxyModel(parent)
        parent.proxy_model.setSourceModel(self)
        parent.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)
        parent.setModel(parent.proxy_model)

    @staticmethod
    def proxy_to_source(proxy: QModelIndex) -> QModelIndex:
        """Step from the QSortFilterProxyModel to the underlying PandasModel."""
        model = proxy.model()
        if not hasattr(model, "mapToSource"):
            return proxy  # Proxy is actually the PandasModel
        return model.mapToSource(proxy)


class EditablePandasModel(PandasModel):
    """ Allows underlying dataframe to be edited through Delegate classes.
    """
    def flags(self, index):
        """ Returns ItemIsEditable flag
        """
        return super().flags(index) | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
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


class EditableDragPandasModel(EditablePandasModel):
    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled


class TreeItem(object):
    COLUMNS = []

    def __init__(self, data, parent=None):
        self._data = data
        self._parent = parent
        self._children = []

    @classmethod
    def build_root(cls) -> 'TreeItem':
        root = cls(cls.COLUMNS)
        return root

    def appendChild(self, item):
        self._children.append(item)

    def child(self, row: int):
        return self._children[row]

    @property
    def children(self) -> list:
        return self._children

    def childCount(self):
        return len(self._children)

    def columnCount(self):
        return len(self.COLUMNS)

    def data(self, column: int):
        return self._data[column]

    def parent(self):
        return self._parent

    def row(self):
        if self._parent:
            return self._parent.children.index(self)
        return 0

    def __repr__(self):
        return "({})".format(", ".join(str(x) for x in self._data))


class BaseTreeModel(QAbstractItemModel):
    """ Base Model used to present data for QTreeView.
    """
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.root = None
        self.setup_model_data(data)

    def columnCount(self, parent=None) -> int:
        if parent and parent.isValid():
            return parent.internalPointer().columnCount()
        return self.root.columnCount()

    def data(self, index, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        item = index.internalPointer()
        if role == Qt.DisplayRole:
            return item.data(index.column())

        if role == Qt.ForegroundRole:
            col_name = self.root.COLUMNS[index.column()]
            return QBrush(style_item.brushes.get(
                col_name, style_item.brushes.get("default")
            ))

    def headerData(self, column, orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.root.COLUMNS[column]
            except IndexError:
                pass
        return None

    def index(self, row, column, parent=None):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parent = self.root
        else:
            parent = parent.internalPointer()

        child = parent.child(row)
        if child:
            return self.createIndex(row, column, child)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        child = index.internalPointer()
        parent = child.parent()

        if parent == self.root:
            return QModelIndex()

        return self.createIndex(parent.row(), 0, parent)

    def rowCount(self, parent=None):
        if parent and parent.column() > 0:
            return 0

        if not parent.isValid():
            parent = self.root
        else:
            parent = parent.internalPointer()

        return parent.childCount()

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def setup_model_data(self, data) -> None:
        """ Method used to construct the tree of items for the model.
        """
        raise NotImplementedError
