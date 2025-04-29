from logging import getLogger

import pandas as pd

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

from .item_model import ABItemModel

log = getLogger(__name__)


class ABTreeView(QtWidgets.QTreeView):
    # fired when the filter is applied, fires False when an exception happens during querying
    filtered: QtCore.SignalInstance = QtCore.Signal(bool)

    defaultColumnDelegates = {}

    class HeaderMenu(QtWidgets.QMenu):
        def __init__(self, pos: QtCore.QPoint, view: "ABTreeView"):
            super().__init__(view)

            model = view.model()

            col_index = view.columnAt(pos.x())
            col_name = model.columns()[col_index]

            search_box = QtWidgets.QLineEdit(self)
            search_box.setText(view.columnFilters.get(col_name, ""))
            search_box.setPlaceholderText("Search")
            search_box.selectAll()
            search_box.textChanged.connect(lambda query: view.setColumnFilter(col_name, query))
            widget_action = QtWidgets.QWidgetAction(self)
            widget_action.setDefaultWidget(search_box)
            self.addAction(widget_action)

            self.addAction(QtGui.QIcon(), "Group by column", lambda: model.group(col_index))
            self.addAction(QtGui.QIcon(), "Ungroup", model.ungroup)
            self.addAction(QtGui.QIcon(), "Clear column filter", lambda: view.setColumnFilter(col_name, ""))
            self.addAction(QtGui.QIcon(), "Clear all filters",
                lambda: [view.setColumnFilter(name, "") for name in list(view.columnFilters.keys())],
            )
            self.addSeparator()

            def toggle_slot(action: QtWidgets.QAction):
                index = action.data()
                hidden = view.isColumnHidden(index)
                view.setColumnHidden(index, not hidden)

            view_menu = QtWidgets.QMenu(view)
            view_menu.setTitle("View")
            self.view_actions = []

            for i in range(1, len(model.columns())):
                action = QtWidgets.QAction(model.columns()[i])
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(i))
                action.setData(i)
                view_menu.addAction(action)
                self.view_actions.append(action)

            view_menu.triggered.connect(toggle_slot)

            self.addMenu(view_menu)

            search_box.setFocus()

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view):
            super().__init__(view)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setUniformRowHeights(True)

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        self.setSelectionBehavior(QtWidgets.QTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QTreeView.SelectionMode.ExtendedSelection)

        header = self.header()
        header.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.showHeaderMenu)

        self.expanded_paths = set()
        self.expanded.connect(lambda index: self.expanded_paths.add(tuple(index.internalPointer().path())))
        self.collapsed.connect(lambda index: self.expanded_paths.discard(tuple(index.internalPointer().path())))

        self.columnFilters: dict[str, str] = {}  # dict[column_name, query] for filtering the dataframe
        self.allFilter: str = ""  # filter applied to the entire dataframe

    def setModel(self, model):
        if not isinstance(model, ABItemModel):
            raise TypeError("Model must be an instance of ABItemModel")
        super().setModel(model)

        model.modelReset.connect(self.expand_after_reset)
        model.modelAboutToBeReset.connect(self.clearColumnDelegates)
        model.modelReset.connect(self.setDefaultColumnDelegates)

        self.setDefaultColumnDelegates()

    def model(self) -> ABItemModel:
        return super().model()

    # === Functionality related to contextmenus

    def showContextMenu(self, pos):
        self.ContextMenu(pos, self).exec_(self.mapToGlobal(pos))

    def showHeaderMenu(self, pos):
        self.HeaderMenu(pos, self).exec_(self.mapToGlobal(pos))

    def setColumnFilter(self, column_name: str, query: str):
        """
        Set a filter for a specific column using a string query. If the query is empty remove the filter from the column
        """
        col_index = self.model().columns().index(column_name)

        if query:
            self.columnFilters[column_name] = query
            self.model().filtered_columns.add(col_index)
        elif column_name in self.columnFilters:
            del self.columnFilters[column_name]
            self.model().filtered_columns.discard(col_index)

        self.applyFilter()

    # === Functionality related to filtering

    def setAllFilter(self, query: str):
        self.allFilter = query
        self.applyFilter()

    def buildQuery(self) -> str:
        queries = ["(index == index)"]

        # query for the column filters
        for col in list(self.columnFilters):
            if col not in self.model().columns():
                del self.columnFilters[col]

        for col, query in self.columnFilters.items():
            q = f"({col}.astype('str').str.contains('{self.format_query(query)}'))"
            queries.append(q)

        # query for the all filter
        if self.allFilter.startswith('='):
            queries.append(f"({self.allFilter[1:]})")
        else:
            all_queries = []
            formatted_filter = self.format_query(self.allFilter)

            for i, col in enumerate(self.model().columns()):
                if self.isColumnHidden(i):
                    continue
                all_queries.append(f"(`{col}`.astype('str').str.contains('{formatted_filter}', False))")

            q = f"({' | '.join(all_queries)})"
            queries.append(q)

        query = " & ".join(queries)
        log.debug(f"{self.__class__.__name__} built query: {query}")

        return query

    def applyFilter(self):
        query = self.buildQuery()
        try:
            self.model().setQuery(query)
            self.filtered.emit(True)
        except Exception as e:
            log.info(f"{self.__class__.__name__} {type(e).__name__} in query: {e}")
            self.filtered.emit(False)

    @staticmethod
    def format_query(query: str) -> str:
        return query.translate(str.maketrans({'(': '\\(', ')': '\\)', "'": "\\'"}))

    # === Functionality related to setting the column delegates
    def clearColumnDelegates(self):
        for i in range(self.model().columnCount()):
            self.setItemDelegateForColumn(i, None)

    def setDefaultColumnDelegates(self):
        columns = self.model().columns()
        for i, col_name in enumerate(columns):
            if col_name in self.defaultColumnDelegates:
                delegate = self.defaultColumnDelegates[col_name](self)
                self.setItemDelegateForColumn(i, delegate)
            # elif col_name.startswith("property_"):
            #     self.setItemDelegateForColumn(i, self.propertyDelegate)

    # === Functionality related to saving and restoring the View's state

    def saveState(self) -> dict:
        if not self.model():
            return {}

        cols = self.model().columns()

        return {
            "columns": cols,
            "grouped_columns": [cols[i] for i in self.model().grouped_columns],
            "visible_columns": [cols[i] for i in range(len(cols)) if not self.isColumnHidden(i)],

            "expanded_paths": list(self.expanded_paths),

            "filters": self.columnFilters,
            "sort_column": cols[self.model().sort_column],
            "sort_ascending": self.model().sort_order == Qt.SortOrder.AscendingOrder,

            "header_state": bytearray(self.header().saveState()).hex()
        }

    def restoreSate(self, state: dict, dataframe: pd.DataFrame):
        if not self.model():
            log.debug(f"{self.__class__.__name__}: Model must first be set on the treeview before using restoreState")
            return

        columns = list(dataframe.columns)

        self.model().beginResetModel()

        self.expanded_paths = set(tuple(p) for p in state.get("expanded_paths", []))
        self.columnFilters = {col: q for col, q in state.get("filters", {}).items() if col in columns}

        self.model().dataframe = dataframe

        self.model().grouped_columns = [columns.index(name) for name in state.get("grouped_columns", []) if name in columns]
        self.model().filtered_columns = {columns.index(name) for name in self.columnFilters if name in columns}

        self.model().sort_column = columns.index(state.get("sort_column")) if state.get("sort_column") in columns else 0
        self.model().sort_order = Qt.SortOrder.AscendingOrder if state.get("sort_ascending") else Qt.SortOrder.DescendingOrder

        self.model()._query = self.buildQuery()

        self.model().endResetModel()

        match = True
        for i, col in enumerate(state.get("columns", [])):
            if i > len(columns) - 1:
                match = False
                break
            if columns[i] != col:
                match = False
                break

        if match:
            self.header().restoreState(bytearray.fromhex(state.get("header_state", "")))

        for i, col in enumerate(columns):
            self.setColumnHidden(i, col not in state.get("visible_columns", [col]))

        self.expand_after_reset()

    def expand_after_reset(self):
        indices = []
        for path in self.expanded_paths:
            try:
                indices.append(self.model().indexFromPath(list(path)))
            except KeyError:
                continue

        for index in indices:
            self.expand(index)

