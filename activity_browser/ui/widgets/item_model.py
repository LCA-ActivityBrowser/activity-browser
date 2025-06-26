import pandas as pd
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt, Signal, SignalInstance

from activity_browser.ui.icons import qicons

from .item import ABAbstractItem, ABBranchItem, ABDataItem


class ABItemModel(QtCore.QAbstractItemModel):
    grouped: SignalInstance = Signal(list)

    dataItemClass = ABDataItem
    branchItemClass = ABBranchItem

    def __init__(self, parent=None, dataframe=None):
        super().__init__(parent)

        if dataframe is None:
            dataframe = pd.DataFrame()

        self.dataframe: pd.DataFrame = dataframe  # DataFrame containing the visible data
        self.root: ABBranchItem = self.branchItemClass("root")  # root ABItem for the object tree
        self.grouped_columns: [int] = list()  # list of columns that are currently being grouped
        self.filtered_columns: [int] = set()  # set of all columns that have filters applied
        self.sort_column: int = 0  # column that is currently sorted
        self.sort_order: Qt.SortOrder = Qt.SortOrder.AscendingOrder
        self._query = ""  # Pandas query currently applied to the dataframe

        self.setDataFrame(self.dataframe)

    def columns(self):
        return [col for col in self.dataframe.columns if not str(col).startswith("_")]

    def headers(self):
        return self.columns()

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
        return len(self.columns())

    def data(self, index: QtCore.QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """
        Get the data associated with a specific index and role
        """
        if not index.isValid() or not isinstance(index.internalPointer(), ABAbstractItem):
            return None

        item: ABAbstractItem = index.internalPointer()
        col = index.column()
        key = self.columns()[col]

        # redirect to the item's displayData method
        if role == Qt.ItemDataRole.DisplayRole:
            return item.displayData(col, key)

        # redirect to the item's fontData method
        if role == Qt.ItemDataRole.FontRole:
            return item.fontData(col, key)

        # redirect to the item's decorationData method
        if role == Qt.ItemDataRole.DecorationRole:
            return item.decorationData(col, key)

        if role == Qt.ItemDataRole.BackgroundRole:
            return item.backgroundData(col, key)

        if role == Qt.ItemDataRole.ForegroundRole:
            return item.foregroundData(col, key)

        # else return None
        return None

    def setData(self, index: QtCore.QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or not isinstance(index.internalPointer(), ABAbstractItem):
            return False

        if role == Qt.ItemDataRole.EditRole:
            success = index.internalPointer().setData(index.column(), self.columns()[index.column()], value)

            if success:
                self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
            return success

        return False

    def headerData(self, section, orientation=Qt.Orientation.Horizontal, role=Qt.ItemDataRole.DisplayRole):
        if orientation != Qt.Orientation.Horizontal:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if section == 0 and self.grouped_columns:
                return " > ".join([self.headers()[column] for column in self.grouped_columns] + [self.headers()[0]])
            return self.headers()[section]

        if role == Qt.ItemDataRole.FontRole and section in self.filtered_columns:
            font = QtGui.QFont()
            font.setUnderline(True)
            return font

        if role == Qt.ItemDataRole.DecorationRole and section in self.filtered_columns:
            return qicons.filter

    def flags(self, index):
        if not index.isValid() or not isinstance(index.internalPointer(), ABAbstractItem):
            return Qt.ItemFlag.NoItemFlags
        if index.column() > len(self.columns()) - 1:
            return Qt.ItemFlag.NoItemFlags

        return index.internalPointer().flags(index.column(), self.columns()[index.column()])

    def endResetModel(self):
        """
        Reset the model based on dataframe, query and grouped columns. Should be called to reflect the changes of
        changing the dataframe, grouped columns or query string.
        """
        # if self.dataframe is None or self.dataframe.empty:
        #     return

        # apply any queries to the dataframe
        if q := self.query():
            df = self.dataframe.query(q).reset_index(drop=True).copy()
        else:
            df = self.dataframe.copy()

        if self.sort_column - 1 >= len(self.columns()):
            # apply the sorting
            df.sort_values(
                by=self.columns()[self.sort_column],
                ascending=(self.sort_order == Qt.SortOrder.AscendingOrder),
                inplace=True, ignore_index=True
            )

        # rebuild the ABItem tree
        self.root = self.branchItemClass("root")
        items = self.createItems(df)

        # if no grouping of Entries, just append everything as a direct child of the root ABItem
        if not self.grouped_columns:
            for i, item in enumerate(items):
                item.set_parent(self.root)
        # else build paths based on the grouped columns and create an ABItem tree
        else:
            column_names = [self.columns()[column] for column in self.grouped_columns]

            for i, *paths in df[column_names].itertuples():
                joined_path = []

                for path in paths:
                    joined_path.extend(path) if isinstance(path, (list, tuple)) else joined_path.append(path)

                joined_path.append(i)
                self.root.put(items[df.index.get_loc(i)], joined_path)

        super().endResetModel()

    def createItems(self, dataframe=None) -> list["ABAbstractItem"]:
        if dataframe is None:
            dataframe = self.dataframe
        return [self.dataItemClass(index, data) for index, data in dataframe.to_dict(orient="index").items()]

    def setDataFrame(self, dataframe: pd.DataFrame):
        self.beginResetModel()
        self.dataframe = dataframe
        self.endResetModel()

    def sort(self, column: int, order=Qt.SortOrder.AscendingOrder):
        if column + 1 > len(self.columns()):
            return
        if column == self.sort_column and order == self.sort_order:
            return

        self.beginResetModel()

        self.sort_column = column
        self.sort_order = order

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



