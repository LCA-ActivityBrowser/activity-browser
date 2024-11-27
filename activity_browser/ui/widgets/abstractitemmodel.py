import pandas as pd
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt, Signal, SignalInstance


class ABAbstractItemModel(QtCore.QAbstractItemModel):
    grouped: SignalInstance = Signal(list)

    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe
        self.dataframe_ = dataframe
        self.entries = Entry("root")
        self.grouped_columns = []
        self.filters = {}
        self.ready = False
        self.columns = [""] + list(self.dataframe.columns)

        for i in range(len(self.dataframe)):
            self.entries.put(i, [i])

    def index(self, row: int, column: int, parent: QtCore.QModelIndex = ...) -> QtCore.QModelIndex:
        """
        Create a QModelIndex based on a specific row, column and parent. Sets the associated Entry as
        internalPointer. This will be the root Entry if the parent is invalid.
        """
        # get the parent Entry, or the root Entry if the parent is invalid
        parent = parent.internalPointer() if parent.isValid() else self.entries

        # get the child Entry from the parent with the same rank as the specified row
        child = parent.ranked_child(row)

        # create and return a QModelIndex
        return self.createIndex(row, column, child)

    def indexFromPath(self, path: [str]) -> QtCore.QModelIndex:
        """
        Create a QModelIndex based on a specific path for the Entry tree. The index column will be 0.
        """
        # get the Entry for that specific path
        child = self.entries.get(path)

        # create and return a QModelIndex with the child's rank as row and 0 as column
        return self.createIndex(child.rank, 0, child)

    def parent(self, child: QtCore.QModelIndex) -> QtCore.QModelIndex:
        """
        Return the parent of a QModelIndex.
        """
        if not child.isValid():
            return QtCore.QModelIndex()

        # get the Entry from the QModelIndex
        child = child.internalPointer()

        # try to get the parent Entry from the child
        try:
            parent = child.parent
        # return an invalid/empty QModelIndex if this fails
        except:
            return QtCore.QModelIndex()

        # if the parent is the root Entry return an invalid/empty QModelIndex
        if parent == self.entries:
            return QtCore.QModelIndex()

        # create and return a QModelIndex with the child's rank as row and 0 as column
        return self.createIndex(parent.rank, 0, parent)

    def setReady(self):
        """
        Flag the model as ready, which means that it will display it's true data instead of showing up as empty

        Compatibility for a bug in Qt where it iterates over all the indexes on first initiation in a QTabWidget
        """
        self.beginResetModel()
        self.ready = True
        self.endResetModel()

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        """
        Return the number of rows within the model
        """
        # return 0 if the ready flag is not set to True, compatibility for a Qt bug
        if not self.ready:
            return 0
        # if the parent is the top of the table, the rowCount is the number of children for the root Entry
        if not parent.isValid():
            value = len(self.entries.children)
        # else it's the number of children within the Entry saved within the internalPointer
        elif isinstance(parent.internalPointer(), Entry):
            value = len(parent.internalPointer().children)
        # this shouldn't happen, but a failsafe
        else:
            value = 0
        return value

    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        """
        Return the number of columns within the model
        """
        return len(self.columns)

    def data(self, index: QtCore.QModelIndex, role=Qt.DisplayRole):
        """
        Get the data associated with a specific index and role
        """
        if not index.isValid() or not isinstance(index.internalPointer(), Entry):
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
        entry: Entry = index.internalPointer()
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

        if role == Qt.FontRole and self.filters.get(self.columns[section], False):
            font = QtGui.QFont()
            font.setUnderline(True)
            return font

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsDragEnabled

    def dataframeIndices(self, entry: QtCore.QModelIndex, recursive=True) -> [int]:
        if isinstance(entry, QtCore.QModelIndex):
            entry = entry.internalPointer()
        if not isinstance(entry, Entry):
            raise ValueError("Invalid entry")

        df_indices = []

        # add own pandas index
        if isinstance(entry.value, int):
            df_indices.append(entry.value)

        if recursive:
            for child in entry.children.values():
                df_indices.extend(self.dataframeIndices(child))

        return df_indices

    def resolveIndex(self, index: QtCore.QModelIndex) -> pd.DataFrame:
        df_indices = self.dataframeIndices(index)
        return self.dataframe.iloc[df_indices]

    def sort(self, column: int, order=Qt.AscendingOrder):
        self.layoutAboutToBeChanged.emit()

        column_name = self.dataframe.columns[column]
        self.dataframe.sort_values(by=column_name, ascending=order == Qt.AscendingOrder, inplace=True, ignore_index=True)

        if self.grouped_columns:
            self.regroup()

        self.layoutChanged.emit()

    def group(self, column: int):
        self.grouped_columns.append(column)
        self.regroup()

    def regroup(self):
        self.beginResetModel()

        self.entries = Entry("root")

        column_names = [self.columns[column] for column in self.grouped_columns]

        for i, *paths in self.dataframe[column_names].itertuples():
            joined_path = []

            for path in paths:
                joined_path.extend(path) if isinstance(path, (list, tuple)) else joined_path.append(path)

            joined_path.append(i)
            self.entries.put(i, joined_path)

        self.endResetModel()
        self.grouped.emit(self.grouped_columns)

    def ungroup(self):
        self.beginResetModel()
        self.entries = Entry("root")
        for i in range(len(self.dataframe)):
            self.entries.put(i, [i])
        self.grouped_columns = []
        self.grouped.emit(self.grouped_columns)
        self.endResetModel()

    def filter(self, query: str = None, column: int = None):
        if query is not None:
            column_name = self.columns[column] if column else "name"
            if query:
                self.filters[column_name] = query
            else:
                del self.filters[column_name]

        # Create a filter for each column and combine them with OR
        filter_condition = pd.Series([True] * len(self.dataframe_))  # Start with all False
        for col, query in self.filters.items():
            filter_condition = filter_condition & self.dataframe_[col].astype(str).str.contains(query, case=False)

        # Apply the combined filter condition to the DataFrame
        self.dataframe = self.dataframe_[filter_condition].reset_index(drop=True)

        self.regroup()


class Entry:
    def __init__(self, name, value=None, parent: "Entry" = None, entry_type=None):
        self.children = {}
        self.index = []

        self.name = name
        self.value = value
        self.parent = parent
        self.type = entry_type

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
        """Return the rank of the entry within the parent. Returns -1 if there is no parent."""
        if self.parent is None:
            return -1
        return self.parent.child_rank(self.name)

    def ranked_child(self, rank: int) -> "Entry":
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
        self.children[name] = sub
        self.index.append(name)

        self.sorted = False

        return sub

    def put(self, value, path):
        name = path.pop(0)
        if path:
            sub = self.sub(name, type="branch")
            sub.put(value, path)
        else:
            self.sub(name, value)

