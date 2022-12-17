# -*- coding: utf-8 -*-
from typing import Optional

import numpy as np
import pandas as pd
from PySide2.QtCore import (
    QAbstractItemModel, QAbstractTableModel, QModelIndex, Qt, Signal,
)
from PySide2.QtGui import QBrush

from activity_browser.bwutils import commontasks as bc
from activity_browser.ui.style import style_item


class PandasModel(QAbstractTableModel):
    """ Abstract pandas table model adapted from
    https://stackoverflow.com/a/42955764.

    TODO: Further improve the model by implementing insertRows and removeRows
     methods, this will allow us to stop recreating the proxy model on every
     add/delete call. See https://doc.qt.io/qt-5/qabstracttablemodel.html
    """
    HEADERS = []
    updated = Signal()

    def __init__(self, df: pd.DataFrame = None, parent=None):
        super().__init__(parent)
        self._dataframe: Optional[pd.DataFrame] = df
        self.filterable_columns = None
        self.different_column_types = {}

    def rowCount(self, parent=None, *args, **kwargs):
        return self._dataframe.shape[0]

    def columnCount(self, parent=None, *args, **kwargs):
        return self._dataframe.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            value = self._dataframe.iat[index.row(), index.column()]
            if isinstance(value, np.float64):
                value = float(value)
            elif isinstance(value, bool):
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

    def row_data(self, index: int) -> list:
        """Return the row at index as a list."""
        return self._dataframe.iloc[index, :].tolist()

    def to_clipboard(self, rows, columns, include_header: bool = False):
        """ Copy the given rows and columns of the dataframe to clipboard
        """
        self._dataframe.iloc[rows, columns].to_clipboard(
            index=False, header=include_header
        )

    def to_csv(self, path: str) -> None:
        """Store the dataframe as csv in the given path."""
        self._dataframe.to_csv(path)

    def to_excel(self, path: str) -> None:
        """Store the underlying dataframe as excel in the given path"""
        self._dataframe.to_excel(excel_writer=path)

    def sync(self, *args, **kwargs) -> None:
        """(Re)build the dataframe according to the given arguments."""
        self._dataframe = pd.DataFrame([], columns=self.HEADERS)

    @staticmethod
    def proxy_to_source(proxy: QModelIndex) -> QModelIndex:
        """Step from the QSortFilterProxyModel to the underlying PandasModel."""
        model = proxy.model()
        if not hasattr(model, "mapToSource"):
            return proxy  # Proxy is actually the PandasModel
        return model.mapToSource(proxy)

    def test_query_on_column(self, test_type: str, col_data: pd.Series, query) -> pd.Series:
        """Compare query and col_data on test_type, return array with boolean test results."""
        if test_type == 'equals':
            return col_data == query
        elif test_type == 'does not equal':
            return col_data != query
        elif test_type == 'contains':
            return col_data.str.contains(query, regex=False)
        elif test_type == 'does not contain':
            return ~col_data.str.contains(query, regex=False)
        elif test_type == 'starts with':
            return col_data.str.startswith(query)
        elif test_type == 'does not start with':
            return ~col_data.str.startswith(query)
        elif test_type == 'ends with':
            return col_data.str.endswith(query)
        elif test_type == 'does not end with':
            return ~col_data.str.endswith(query)
        elif test_type == '=':
            return col_data.astype(float) == float(query)
        elif test_type == '!=':
            return col_data.astype(float) != float(query)
        elif test_type == '>=':
            return col_data.astype(float) >= float(query)
        elif test_type == '<=':
            return col_data.astype(float) <= float(query)
        elif test_type == '<= x <=':
            return (float(query[0]) <= col_data.astype(float)) \
                   & (col_data.astype(float) <= float(query[1]))
        else:
            print("WARNING: unknown filter type >{}<, assuming 'EQUALS'".format(test_type))
            return col_data == query

    def get_filter_mask(self, filters: dict) -> pd.Series:
        """Generate a filter mask of the dataframe based on the filters.

        Returns a pd.Series of boolean results (the mask).
        """
        # get the column name from index
        fc_rev = {v: k for k, v in self.filterable_columns.items()}

        all_mode = filters['mode']
        all_mask = None
        # iterate over columns
        for col_idx, col_filters in filters.items():
            if col_idx == 'mode':
                continue
            col_name = fc_rev[col_idx]
            col_data = self._dataframe[col_name]
            col_mode = col_filters.get('mode', False)
            col_mask = None
            # iterate over filters within column
            for col_filt in col_filters['filters']:
                if self.different_column_types.get(col_name, False):
                    # this is a 'num' column
                    filt_type, query = col_filt
                    col_data_ = col_data
                else:
                    # this is a 'str' column
                    filt_type, query, case_sensitive = col_filt
                    if case_sensitive:
                        col_data_ = col_data.astype(str)
                    else:
                        col_data_ = col_data.astype(str).str.upper()
                        query = query.upper()

                # run the test
                new_mask = self.test_query_on_column(filt_type, col_data_, query)
                if not any(new_mask):
                    # no matches for this mask, let user know:
                    print("There were no matches for filter: {}: '{}'".format(col_filt[0], col_filt[1]))

                # create or combine new mask within column
                if isinstance(col_mask, pd.Series) and col_mode == 'AND':
                    col_mask = col_mask & new_mask
                elif isinstance(col_mask, pd.Series) and col_mode == 'OR':
                    col_mask = col_mask + new_mask
                else:
                    col_mask = new_mask

            # create or combine new mask on columns
            if isinstance(all_mask, pd.Series) and all_mode == 'AND':
                all_mask = all_mask & col_mask
            elif isinstance(all_mask, pd.Series) and all_mode == 'OR':
                all_mask = all_mask + col_mask
            else:
                all_mask = col_mask
        return all_mask


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
    __slots__ = ["_data", "_parent", "_children"]

    def __init__(self, data: list, parent=None):
        self._data = data
        self._parent = parent
        self._children = []

    @classmethod
    def build_root(cls, cols: list) -> 'TreeItem':
        return cls(cols)

    def clear(self) -> None:
        """Use this method to recursively prune a branch from a tree model.
        When called on the root item, removes the entire tree.

        Make sure to only use this in conjunction with model.beginModelReset
        and model.endModelReset to avoid python crashing.
        """
        for c in self._children:
            c.clear()
        self._children = []

    def appendChild(self, item) -> None:
        self._children.append(item)

    def child(self, row: int) -> 'TreeItem':
        return self._children[row]

    @property
    def children(self) -> list:
        return self._children

    def childCount(self) -> int:
        return len(self._children)

    def data(self, column: int):
        return self._data[column]

    def parent(self) -> Optional['TreeItem']:
        return self._parent

    def row(self) -> int:
        return self._parent.children.index(self) if self._parent else 0

    def __repr__(self) -> str:
        return "({})".format(", ".join(str(x) for x in self._data))


class BaseTreeModel(QAbstractItemModel):
    """ Base Model used to present data for QTreeView.
    """
    HEADERS = []
    updated = Signal()

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)
        self.root = None
        self._data = {}

    def columnCount(self, parent: QModelIndex = None, *args, **kwargs) -> int:
        return len(self.HEADERS)

    def data(self, index, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            item = index.internalPointer()
            return item.data(index.column())

        if role == Qt.ForegroundRole:
            col_name = self.HEADERS[index.column()]
            return QBrush(style_item.brushes.get(
                col_name, style_item.brushes.get("default")
            ))

    def headerData(self, column, orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.HEADERS[column]
            except IndexError:
                pass
        return None

    def index(self, row: int, column: int, parent: QModelIndex = None, *args, **kwargs):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent = parent.internalPointer() if parent.isValid() else self.root
        child = parent.child(row)
        if child:
            return self.createIndex(row, column, child)
        else:
            return QModelIndex()

    def parent(self, child: QModelIndex = None):
        if not child.isValid():
            return QModelIndex()

        child = child.internalPointer()
        parent = child.parent()
        if parent == self.root:
            return QModelIndex()

        return self.createIndex(parent.row(), 0, parent)

    def rowCount(self, parent=None, *args, **kwargs):
        if not parent or parent.column() > 0:
            return 0
        parent = parent.internalPointer() if parent.isValid() else self.root
        return parent.childCount()

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def setup_model_data(self) -> None:
        """ Method used to construct the tree of items for the model.
        """
        raise NotImplementedError

    def sync(self, *args, **kwargs) -> None:
        pass
