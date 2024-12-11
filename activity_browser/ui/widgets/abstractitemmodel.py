import pandas as pd
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt, Signal, SignalInstance

from activity_browser.ui.icons import qicons


class ABAbstractItemModel(QtCore.QAbstractItemModel):
    grouped: SignalInstance = Signal(list)

    columns = [""]

    def __init__(self, parent=None, dataframe=None):
        super().__init__(parent)

        self.dataframe: pd.DataFrame | None = None  # DataFrame containing the visible data
        self.dataframe_: pd.DataFrame | None = None  # DataFrame containing the original (unfiltered) data
        self.root: ABItem | None = None  # root ABItem for the object tree
        self.grouped_columns: [int] = []  # list of all columns that are currently being grouped
        self.filtered_columns: [int] = set()  # set of all columns that have filters applied
        self._query = ""  # Pandas query currently applied to the dataframe

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
        child = parent.ranked_child(row)

        # create and return a QModelIndex
        return self.createIndex(row, column, child)

    def indexFromPath(self, path: [str]) -> QtCore.QModelIndex:
        """
        Create a QModelIndex based on a specific path for the ABItem tree. The index column will be 0.
        """
        # get the ABItem for that specific path
        child = self.root.get(path)

        # create and return a QModelIndex with the child's rank as row and 0 as column
        return self.createIndex(child.rank, 0, child)

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
            parent = child.parent
        # return an invalid/empty QModelIndex if this fails
        except:
            return QtCore.QModelIndex()

        # if the parent is the root ABItem return an invalid/empty QModelIndex
        if parent == self.root:
            return QtCore.QModelIndex()

        # create and return a QModelIndex with the child's rank as row and 0 as column
        return self.createIndex(parent.rank, 0, parent)

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        """
        Return the number of rows within the model
        """
        # return 0 if there is no DataFrame
        if self.dataframe is None:
            return 0
        # if the parent is the top of the table, the rowCount is the number of children for the root ABItem
        if not parent.isValid():
            value = len(self.root.children)
        # else it's the number of children within the ABItem saved within the internalPointer
        elif isinstance(parent.internalPointer(), ABItem):
            value = len(parent.internalPointer().children)
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
        if not index.isValid() or not isinstance(index.internalPointer(), ABItem):
            return None

        # redirect to the displayData method
        if role == Qt.DisplayRole:
            return self.displayData(index)

        # redirect to the fontData method
        if role == Qt.FontRole:
            return self.fontData(index)

        # else return None
        return None

    def displayData(self, index):
        """
        Return the display data for a specific index
        """
        entry: ABItem = index.internalPointer()
        display = None

        # return the entry name if the column is 0, meaning the branch of the tree
        if index.column() == 0 and entry.children:
            display = str(entry.name)

        # if we're not in the tree column and the Entry.value is an integer get the data from the dataframe
        if not index.column() == 0 and isinstance(entry.value, int):
            # Entry.value corresponds with the row number in the dataframe, the index column can be used to get the
            # column name from self.columns.
            data = self.dataframe.loc[entry.value, self.columns[index.column()]]

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
            if section == 0:
                return str([self.columns[column] for column in self.grouped_columns])
            return self.columns[section]

        if role == Qt.FontRole and section in self.filtered_columns:
            font = QtGui.QFont()
            font.setUnderline(True)
            return font

        if role == Qt.DecorationRole and section in self.filtered_columns:
            return qicons.filter

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled

    def dataframeIndices(self, ABItem: QtCore.QModelIndex, recursive=True) -> [int]:
        if isinstance(ABItem, QtCore.QModelIndex):
            ABItem = ABItem.internalPointer()
        if not isinstance(ABItem, ABItem):
            raise ValueError("Invalid ABItem")

        df_indices = []

        # add own pandas index
        if isinstance(ABItem.value, int):
            df_indices.append(ABItem.value)

        if recursive:
            for child in ABItem.children.values():
                df_indices.extend(self.dataframeIndices(child))

        return df_indices

    def resolveIndex(self, index: QtCore.QModelIndex) -> pd.DataFrame:
        df_indices = self.dataframeIndices(index)
        return self.dataframe.iloc[df_indices]

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
        self.root = ABItem("root")
        items = self.createItems()

        # if no grouping of Entries, just append everything as a direct child of the root ABItem
        if not self.grouped_columns:
            for i, item in enumerate(items):
                self.root.put(item, [i])
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

    def createItems(self) -> list["ABItem"]:
        return [ABItem(i, value=i) for i in range(len(self.dataframe))]

    def sort(self, column: int, order=Qt.AscendingOrder):
        if column == 0:
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


class ABItem:
    def __init__(self, name, value=None, parent: "ABItem" = None, ABItem_type=None):
        self.children = {}
        self.index = []

        self.name = name
        self.value = value
        self.parent = parent
        self.type = ABItem_type

        self.sorted = True

    def sort(self):
        branches = []
        other = []
        for i in self.index:
            if self.children[i].type == "branch":
                branches.append(i)
            else:
                other.append(i)
        self.index = branches + other
        self.sorted = True

    @property
    def path(self) -> [str]:
        return self.parent.path + [self.name] if self.parent else []

    @property
    def rank(self) -> int:
        """Return the rank of the ABItem within the parent. Returns -1 if there is no parent."""
        if self.parent is None:
            return -1
        return self.parent.child_rank(self.name)

    def ranked_child(self, rank: int) -> "ABItem":
        """Return the child with the given rank"""
        if not self.sorted:
            self.sort()
        return self.children[self.index[rank]]

    def child_rank(self, name) -> int:
        """Return the rank of a child with the given name"""
        if not self.sorted:
            self.sort()
        return self.index.index(name)

    def get(self, path: [str]):
        if not path:
            return self
        name = path.pop(0)
        return self.children[name].get(path)

    def sub(self, name, value=None, type=None):
        if name in self.children:
            return self.children[name]

        sub = self.__class__(name, value, self, type)
        self.put(sub, [name])
        return sub

    def put(self, ABItem: "ABItem", path):
        name = path.pop(0)
        if path:
            sub = self.sub(name, type="branch")
            sub.put(ABItem, path)
        else:
            self.children[name] = ABItem
            self.index.append(name)
            self.sorted = False

            ABItem.parent = self

