from loguru import logger

import pandas as pd

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

from activity_browser.ui import delegates, core
from .item_model import ABItemModel




class ABNewTreeView(QtWidgets.QTreeView):
    # fired when the filter is applied, fires False when an exception happens during querying
    filtered: QtCore.SignalInstance = QtCore.Signal(bool)

    defaultColumnDelegates = {}

    class HeaderMenu(QtWidgets.QMenu):
        def __init__(self, pos: QtCore.QPoint, view: "ABNewTreeView"):
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

            self.addAction(QtGui.QIcon(), "Group by column", lambda: model.group([col_name]))
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
        self.setIndentation(10)
        self.setUniformRowHeights(True)
        self.setItemDelegate(delegates.StringDelegate(self))

        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        self.setSelectionBehavior(QtWidgets.QTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QTreeView.SelectionMode.ExtendedSelection)

        self.header().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.header().customContextMenuRequested.connect(self.showHeaderMenu)

        self.columnFilters: dict[str, str] = {}  # dict[column_name, query] for filtering the dataframe
        self.allFilter: str = ""  # filter applied to the entire dataframe

    def setModel(self, model):
        super().setModel(model)

        self.setColumnWidth(0, 30)
        self.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)

        model.modelAboutToBeReset.connect(self.clearColumnDelegates)
        model.modelReset.connect(self.setDefaultColumnDelegates)
        model.layoutChanged.connect(self.updateIndexColumnVisibility)
        model.layoutChanged.connect(self.updateBranchSpanning)

        self.setDefaultColumnDelegates()
        self.updateIndexColumnVisibility()
        self.updateBranchSpanning()

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
            # self.model().filtered_columns.add(col_index)
        elif column_name in self.columnFilters:
            del self.columnFilters[column_name]
            # self.model().filtered_columns.discard(col_index)

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
        logger.debug(f"{self.__class__.__name__} built query: {query}")

        return query

    def applyFilter(self):
        query = self.buildQuery()
        try:
            self.model().filter("ABNewTreeView", query)
            self.filtered.emit(True)
        except Exception as e:
            logger.info(f"{self.__class__.__name__} {type(e).__name__} in query: {e}")
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
            elif col_name.startswith("property_"):
                self.setItemDelegateForColumn(i, self.propertyDelegate)

    def updateIndexColumnVisibility(self):
        """Hide the index column (column 0) if the dataframe index is only one level deep."""
        model = self.model()
        if model is None:
            return
        
        # Check if model has the df attribute (ABTreeModel style)
        if hasattr(model, 'df') and hasattr(model.df, 'index'):
            # Hide index column if it's only one level deep
            hide_index = model.df.index.nlevels == 1
            self.setColumnHidden(0, hide_index)
    
    def updateBranchSpanning(self):
        """Enable spanning for branch nodes so they span across all columns."""
        model = self.model()
        if model is None or not hasattr(model, 'isBranchNode'):
            return
        
        # Recursively set spanning for all branch nodes
        self._setSpanningRecursive(QtCore.QModelIndex())
    
    def _setSpanningRecursive(self, parent: QtCore.QModelIndex):
        """Recursively set first column spanning for branch nodes."""
        model = self.model()
        if model is None:
            return
        
        row_count = model.rowCount(parent)
        for row in range(row_count):
            index = model.index(row, 0, parent)
            if not index.isValid():
                continue
            
            # Check if this is a branch node
            if hasattr(model, 'isBranchNode') and model.isBranchNode(index):
                self.setFirstColumnSpanned(row, parent, True)
                # Recursively process children
                self._setSpanningRecursive(index)
            else:
                self.setFirstColumnSpanned(row, parent, False)

