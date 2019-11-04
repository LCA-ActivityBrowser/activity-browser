# -*- coding: utf-8 -*-
import numpy as np
import brightway2 as bw
from pandas import DataFrame
from PySide2.QtCore import QAbstractItemModel, QAbstractTableModel, QModelIndex, Qt
from PySide2.QtGui import QBrush

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
                col_name = AB_names_to_bw_keys.get(col_name, "")
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


class ParameterItem(TreeItem):
    COLUMNS = ["Name", "Group", "Amount", "Formula"]

    def __init__(self, data: list, parent=None):
        super().__init__(data, parent)

    @staticmethod
    def build_header(header: str, parent: TreeItem) -> 'ParameterItem':
        item = ParameterItem([header, "", "", ""], parent)
        parent.appendChild(item)
        return item

    @classmethod
    def build_item(cls, param, parent: TreeItem) -> 'ParameterItem':
        """ Depending on the parameter type, the group is changed, defaults to
        'project'.

        For Activity parameters, use a 'header' item as parent, create one
        if it does not exist.
        """
        group = "project"
        if hasattr(param, "code") and hasattr(param, "database"):
            database = "database - {}".format(str(param.database))
            if database not in [x.data(0) for x in parent.children]:
                cls.build_header(database, parent)
            parent = next(x for x in parent.children if x.data(0) == database)
            group = getattr(param, "group")
        elif hasattr(param, "database"):
            group = param.database

        item = cls([
            getattr(param, "name", ""),
            group,
            getattr(param, "amount", 0.0),
            getattr(param, "formula", ""),
        ], parent)

        # If the variable is found, we're working on an activity parameter
        if "database" in locals():
            cls.build_exchanges(param, item)

        parent.appendChild(item)
        return item

    @classmethod
    def build_exchanges(cls, act_param, parent: TreeItem) -> None:
        """ Take the given activity parameter, retrieve the matching activity
        and construct tree-items for each exchange with a `formula` field.
        """
        act = bw.get_activity((act_param.database, act_param.code))

        for exc in [exc for exc in act.exchanges() if "formula" in exc]:
            act_input = bw.get_activity(exc.input)
            item = cls([
                act_input.get("name"),
                parent.data(1),
                exc.amount,
                exc.get("formula"),
            ], parent)
            parent.appendChild(item)


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


class ParameterTreeModel(BaseTreeModel):
    """
    Ordering and foldouts as follows:
    - Project parameters:
        - All 'root' objects
        - No children
    - Database parameters:
        - All 'root' objects
        - No children
    - Activity parameters:
        - Never root objects.
        - Placed under simple 'database' root objects
        - Exchanges as children
    - Exchange parameters:
        - Never root objects
        - Children of relevant activity parameter
        - No children
    """

    def __init__(self, data: dict, parent=None):
        super().__init__(data, parent)

    def setup_model_data(self, data: dict) -> None:
        """ First construct the root, then process the data.
        """
        self.root = ParameterItem.build_root()

        for param in data.get("project", []):
            ParameterItem.build_item(param,  self.root)
        for param in data.get("database", []):
            ParameterItem.build_item(param,  self.root)
        for param in data.get("activity", []):
            ParameterItem.build_item(param,  self.root)
