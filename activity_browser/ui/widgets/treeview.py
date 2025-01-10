import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui

from .abstractitemmodel import ABAbstractItemModel


class ABTreeView(QtWidgets.QTreeView):

    class HeaderMenu(QtWidgets.QMenu):
        def __init__(self, pos: QtCore.QPoint, view: "ABTreeView"):
            super().__init__(view)

            model = view.model()

            col_index = view.columnAt(pos.x())
            col_name = model.columns[col_index]

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

            for i in range(1, len(model.columns)):
                action = QtWidgets.QAction(model.columns[i])
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

        header = self.header()
        header.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self.showHeaderMenu)

        self.expanded_paths = set()
        self.expanded.connect(lambda index: self.expanded_paths.add(tuple(index.internalPointer().path())))
        self.collapsed.connect(lambda index: self.expanded_paths.discard(tuple(index.internalPointer().path())))

        self.columnFilters: dict[str, str] = {}  # dict[column_name, query] for filtering the dataframe

    def setModel(self, model):
        if not isinstance(model, ABAbstractItemModel):
            raise TypeError("Model must be an instance of ABAbstractItemModel")
        super().setModel(model)

        model.modelReset.connect(self.expand_after_reset)

    def model(self) -> ABAbstractItemModel:
        return super().model()

    def showContextMenu(self, pos):
        self.ContextMenu(pos, self).exec_(self.mapToGlobal(pos))

    def showHeaderMenu(self, pos):
        self.HeaderMenu(pos, self).exec_(self.mapToGlobal(pos))

    def setColumnFilter(self, column_name: str, query: str):
        if query:
            self.columnFilters[column_name] = query
            self.model().filtered_columns.add(self.model().columns.index(column_name))
        elif column_name in self.columnFilters:
            del self.columnFilters[column_name]
            self.model().filtered_columns.discard(self.model().columns.index(column_name))
        self.applyFilter()

    def buildQuery(self) -> str:
        q = " & ".join([f"({col}.astype('str').str.contains('{self.format_query(q)}'))" for col, q in self.columnFilters.items()])
        return "(index == index)" if not q else f"({q})"

    def applyFilter(self):
        self.model().setQuery(self.buildQuery())

    @staticmethod
    def format_query(query: str) -> str:
        return query.translate(str.maketrans({'(': '\\(', ')': '\\)', "'": "\\'"}))

    def saveState(self) -> dict:
        if not self.model():
            return {}

        return {
            "columns": self.model().columns,
            "grouped_columns": [self.model().columns[i] for i in self.model().grouped_columns],
            "current_query": self.model().query(),

            "expanded_paths": list(self.expanded_paths),
            "visible_columns": [self.model().columns[i] for i in range(len(self.model().columns)) if not self.isColumnHidden(i)],
            "filters": self.columnFilters,
            "sort_column": self.model().sort_column,
            "sort_ascending": self.model().sort_order == QtCore.Qt.SortOrder.AscendingOrder,

            "header_state": bytearray(self.header().saveState()).hex()
        }

    def restoreSate(self, state: dict, dataframe: pd.DataFrame) -> bool:
        if not self.model():
            return False
        self.model().beginResetModel()

        columns = state.get("columns", []) + [col for col in dataframe.columns if col not in state.get("columns", [])]

        self.model().dataframe = dataframe
        self.model().columns = columns
        self.model().grouped_columns = [columns.index(name) for name in state.get("grouped_columns", [])]
        self.model()._query = state.get("current_query", self.model()._query)
        self.model().sort_column = state.get("sort_column", self.model().sort_column)
        self.model().sort_order = QtCore.Qt.SortOrder.AscendingOrder if state.get("sort_ascending") else QtCore.Qt.SortOrder.DescendingOrder
        self.model().endResetModel()

        self.expanded_paths = set(tuple(p) for p in state.get("expanded_paths", []))
        self.columnFilters = state.get("filters", {})
        for column_name in self.columnFilters:
            self.model().filtered_columns.add(self.model().columns.index(column_name))

        for col_name in [col for col in columns if col not in state.get("visible_columns", columns)]:
            self.setColumnHidden(columns.index(col_name), True)

        self.header().restoreState(bytearray.fromhex(state.get("header_state", "")))
        self.expand_after_reset()

        return True

    def expand_after_reset(self):
        indices = []
        for path in self.expanded_paths:
            try:
                indices.append(self.model().indexFromPath(list(path)))
            except KeyError:
                continue

        for index in indices:
            self.expand(index)

