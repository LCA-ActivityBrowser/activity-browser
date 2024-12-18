import pandas as pd
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt, Signal, SignalInstance

from activity_browser.ui.icons import qicons


class ABAbstractItemModel(QtCore.QAbstractItemModel):
    grouped: SignalInstance = Signal(list)

    def __init__(self, parent=None, dataframe=None):
        super().__init__(parent)

        self.dataframe: pd.DataFrame | None = None  # DataFrame containing the visible data
        self.dataframe_: pd.DataFrame | None = None  # DataFrame containing the original (unfiltered) data
        self.root: ABBranchItem | None = None  # root ABItem for the object tree
        self.grouped_columns: [int] = []  # list of all columns that are currently being grouped
        self.filtered_columns: [int] = set()  # set of all columns that have filters applied
        self._query = ""  # Pandas query currently applied to the dataframe
        self.columns = []

        # if a dataframe is set as kwarg set it up
        if dataframe is not None:
            self.setDataFrame(dataframe)

    def setDataFrame(self, dataframe: pd.DataFrame):
        self.beginResetModel()

        # set the index to a RangeIndex
        # todo: research whether this is totally necessary
        dataframe.index = pd.RangeIndex(len(dataframe))

        self.dataframe = dataframe
        self.dataframe_ = dataframe

        # extend the columns
        self.columns = self.columns + [col for col in self.dataframe.columns if col not in self.columns]

        self.endResetModel()

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        """
        Create a QModelIndex based on a specific row, column and parent. Sets the associated ABItem as
        internalPointer. This will be the root ABItem if the parent is invalid.
        """
        # get the parent ABItem, or the root ABItem if the parent is invalid
        parent = parent.internalPointer() if parent.isValid() else self.root

        # get the child ABItem from the parent with the same rank as the specified row
        child = parent.iloc(row)

        # create and return a QModelIndex
        return self.createIndex(row, column, child)

    def indexFromPath(self, path: [str]) -> QtCore.QModelIndex:
        """
        Create a QModelIndex based on a specific path for the ABItem tree. The index column will be 0.
        """
        # get the ABItem for that specific path
        child = self.root.loc(path)
        if child is None:
            return QtCore.QModelIndex()

        # create and return a QModelIndex with the child's rank as row and 0 as column
        return self.createIndex(child.rank(), 0, child)

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """
        Return the parent of a QModelIndex.
        """
        if not child.isValid():
            return QtCore.QModelIndex()

        # get the ABItem from the QModelIndex
        child = child.internalPointer()

        # try to get the parent ABItem from the child
        try:
            parent = child.parent()
        # return an invalid/empty QModelIndex if this fails
        except:
            return QtCore.QModelIndex()

        # if the parent is the root ABItem return an invalid/empty QModelIndex
        if parent == self.root:
            return QtCore.QModelIndex()

        # create and return a QModelIndex with the child's rank as row and 0 as column
        return self.createIndex(parent.rank(), 0, parent)

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        """
        Return the number of rows within the model
        """
        # return 0 if there is no DataFrame
        if self.dataframe is None:
            return 0
        # if the parent is the top of the table, the rowCount is the number of children for the root ABItem
        if not parent.isValid():
            value = len(self.root.children())
        # else it's the number of children within the ABItem saved within the internalPointer
        elif isinstance(parent.internalPointer(), ABAbstractItem):
            value = len(parent.internalPointer().children())
        # this shouldn't happen, but a failsafe
        else:
            value = 0
        return value

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        """
        Return the number of columns within the model
        """
        # return 0 if there is no DataFrame
        if self.dataframe is None:
            return 0
        return len(self.columns)

    def data(self, index: QtCore.QModelIndex, role=Qt.DisplayRole):
        """
        Get the data associated with a specific index and role
        """
        if not index.isValid() or not isinstance(index.internalPointer(), ABAbstractItem):
            return None

        # redirect to the displayData method
        if role == Qt.DisplayRole:
            return self.displayData(index)

        # redirect to the fontData method
        if role == Qt.FontRole:
            return self.fontData(index)

        if role == Qt.DecorationRole:
            key = self.columns[index.column()]
            return index.internalPointer().decorationData(key)

        # else return None
        return None

    def displayData(self, index):
        """
        Return the display data for a specific index
        """
        entry: ABAbstractItem = index.internalPointer()

        data = entry[self.columns[index.column()]]

        if data is None and index.column() == 0:
            data = entry.key()

        if data is None:
            return None

        # clean up the data to a table-readable format
        display = str(data).replace("\n", " ")

        # if the display is nan, change to the user-friendlier Undefined
        if display == "nan":
            display = "Undefined"

        return display

    def fontData(self, index):
        """
        Return the font data for a specific index
        """
        font = QtGui.QFont()

        # set the font to italic if the display value is Undefined
        if self.displayData(index) == "Undefined":
            font.setItalic(True)

        return font

    def headerData(self, section, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal:
            return None

        if role == Qt.DisplayRole:
            if section == 0 and self.grouped_columns:
                return " > ".join([self.columns[column] for column in self.grouped_columns] + [self.columns[0]])
            return self.columns[section]

        if role == Qt.FontRole and section in self.filtered_columns:
            font = QtGui.QFont()
            font.setUnderline(True)
            return font

        if role == Qt.DecorationRole and section in self.filtered_columns:
            return qicons.filter

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled

    def endResetModel(self):
        """
        Reset the model based on dataframe, query and grouped columns. Should be called to reflect the changes of
        changing the dataframe, grouped columns or query string.
        """
        # apply any existing queries to the dataframe
        if q := self.query():
            self.dataframe = self.dataframe_.query(q).reset_index(drop=True)
        else:
            self.dataframe = self.dataframe_

        # rebuild the ABItem tree
        self.root = ABBranchItem("root")
        items = self.createItems()

        # if no grouping of Entries, just append everything as a direct child of the root ABItem
        if not self.grouped_columns:
            for i, item in enumerate(items):
                item.set_parent(self.root)
        # else build paths based on the grouped columns and create an ABItem tree
        else:
            column_names = [self.columns[column] for column in self.grouped_columns]

            for i, *paths in self.dataframe[column_names].itertuples():
                joined_path = []

                for path in paths:
                    joined_path.extend(path) if isinstance(path, (list, tuple)) else joined_path.append(path)

                joined_path.append(i)
                self.root.put(items[i], joined_path)

        super().endResetModel()

    def createItems(self) -> list["ABAbstractItem"]:
        return [ABDataItem(index, data) for index, data in self.dataframe.to_dict(orient="index").items()]

    def sort(self, column: int, order=Qt.AscendingOrder):
        if column + 1 > len(self.columns):
            return

        self.beginResetModel()

        column_name = self.columns[column]
        self.dataframe_.sort_values(by=column_name, ascending=order == Qt.AscendingOrder, inplace=True, ignore_index=True)

        self.endResetModel()

    def group(self, column: int):
        self.beginResetModel()
        self.grouped_columns.append(column)
        self.endResetModel()
        self.grouped.emit(self.grouped_columns)

    def ungroup(self):
        self.beginResetModel()
        self.grouped_columns.clear()
        self.endResetModel()
        self.grouped.emit(self.grouped_columns)

    def query(self) -> str:
        return self._query

    def setQuery(self, query: str):
        """Apply the query string to the dataframe and rebuild the model"""
        self.beginResetModel()
        self._query = query
        self.endResetModel()

    def hasChildren(self, parent: QtCore.QModelIndex):
        item = parent.internalPointer()
        if isinstance(item, ABAbstractItem):
            return item.has_children()
        return super().hasChildren(parent)


class ABAbstractItem:

    def __init__(self, key, parent=None):
        self._key = key
        self._child_keys = []
        self._child_items = {}
        self._parent = None

        if parent:
            self.set_parent(parent)

    def __getitem__(self, item):
        raise NotImplementedError

    def parent(self) -> "ABAbstractItem":
        return self._parent

    def key(self):
        return self._key

    def children(self):
        return self._child_items

    def path(self) -> [str]:
        return self.parent().path() + [self.key()] if self.parent() else []

    def rank(self) -> int:
        """Return the rank of the ABItem within the parent. Returns -1 if there is no parent."""
        if self.parent is None:
            return -1
        return self.parent()._child_keys.index(self.key())

    def has_children(self) -> bool:
        return bool(self._child_keys)

    def set_parent(self, parent: "ABAbstractItem"):
        if self.key() in parent.children():
            raise KeyError(f"Item {self.key()} is already a child of {parent.key()}")

        if self.parent():
            self.parent()._child_keys.remove(self.key())
            del self.parent()._child_items[self.key()]

        parent._child_items[self.key()] = self
        parent._child_keys.append(self.key())
        self._parent = parent

    def loc(self, key_or_path: object | list[object], default=None):
        key = key_or_path.pop(0) if isinstance(key_or_path, list) else key_or_path

        if isinstance(key_or_path, list) and len(key_or_path) > 0:
            return self._child_items[key].loc(key_or_path, default)

        return self._child_items.get(key, default)

    def iloc(self, index: int, default=None):
        return self.loc(self._child_keys[index], default)

    def decorationData(self, key: str):
        return None


class ABBranchItem(ABAbstractItem):

    def __getitem__(self, item):
        return None

    def put(self, item: ABAbstractItem, path):
        key = path.pop(0)
        if path:
            sub = self.loc(key)
            sub = sub if sub else self.__class__(key, self)
            sub.put(item, path)
        else:
            item.set_parent(self)

    def set_parent(self, parent: "ABAbstractItem"):
        if self.key() in parent._child_items:
            twin = parent.loc(self.key())
            for child in twin.child_items.values():
                child.set_parent(self)

        if self.parent():
            self.parent()._child_keys.remove(self.key())
            del self.parent()._child_items[self.key()]

        parent._child_items[self.key()] = self

        branches = [isinstance(parent._child_items[key], ABBranchItem) for key in parent._child_keys]
        i = branches.index(False) if False in branches else len(branches)
        parent._child_keys.insert(i, self.key())
        self._parent = parent


class ABDataItem(ABAbstractItem):
    def __init__(self, key, data, parent=None):
        super().__init__(key, parent)
        self.data = data

    def __getitem__(self, item):
        return self.data.get(item)

