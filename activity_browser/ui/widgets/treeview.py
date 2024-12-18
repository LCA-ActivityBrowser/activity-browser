import re
from qtpy import QtWidgets, QtCore, QtGui

from .abstractitemmodel import ABAbstractItemModel


class ABTreeViewMenuFactory:

    def __init__(self, view: "ABTreeView"):
        self.view = view

    @property
    def model(self):
        return self.view.model()

    def createMenu(self, pos: QtCore.QPoint):
        """Designed to be passed to customContextMenuRequested.connect"""
        QtWidgets.QMenu(self.view).exec_(self.view.mapToGlobal(pos))

    def createHeaderMenu(self, pos: QtCore.QPoint):
        """Designed to be passed to customContextMenuRequested.connect"""
        col = self.view.columnAt(pos.x())
        menu = self._header_menu_standard(col)
        menu.exec_(self.view.mapToGlobal(pos))

    def _header_menu_standard(self, column: int):
        menu = QtWidgets.QMenu(self.view)
        col_name = self.model.columns[column]

        search_box = QtWidgets.QLineEdit(menu)
        search_box.setText(self.view.columnFilters.get(col_name, ""))
        search_box.setPlaceholderText("Search")
        search_box.selectAll()

        search_box.textChanged.connect(lambda query: self.view.setColumnFilter(col_name, query))
        widget_action = QtWidgets.QWidgetAction(menu)
        widget_action.setDefaultWidget(search_box)
        menu.addAction(widget_action)

        menu.addAction(
            QtGui.QIcon(),
            "Group by column",
            lambda: self.model.group(column),
        )
        menu.addAction(
            QtGui.QIcon(),
            "Ungroup",
            self.model.ungroup,
        )
        menu.addAction(
            QtGui.QIcon(),
            "Clear column filter",
            lambda: self.view.setColumnFilter(col_name, ""),
        )
        menu.addAction(
            QtGui.QIcon(),
            "Clear all filters",
            lambda: [self.view.setColumnFilter(name, "") for name in list(self.view.columnFilters.keys())],
        )
        menu.addSeparator()
        menu.addMenu(self._header_menu_standard_view())

        search_box.setFocus()
        return menu

    def _header_menu_standard_view(self):
        def toggle_slot(action: QtWidgets.QAction):
            index = action.data()
            hidden = self.view.isColumnHidden(index)
            self.view.setColumnHidden(index, not hidden)

        menu = QtWidgets.QMenu(self.view)
        menu.setTitle("View")
        self.view_actions = []

        for i in range(1, len(self.model.columns)):
            action = QtWidgets.QAction(self.model.columns[i])
            action.setCheckable(True)
            action.setChecked(not self.view.isColumnHidden(i))
            action.setData(i)
            menu.addAction(action)
            self.view_actions.append(action)

        menu.triggered.connect(toggle_slot)

        return menu


class ABTreeView(QtWidgets.QTreeView):
    menuFactoryClass = ABTreeViewMenuFactory

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setUniformRowHeights(True)
        self.menuFactory = self.menuFactoryClass(self)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menuFactory.createMenu)

        header = self.header()
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.menuFactory.createHeaderMenu)

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

            "header_state": bytearray(self.header().saveState()).hex()
        }

    def restoreSate(self, state: dict) -> bool:
        if not self.model():
            return False

        columns = [col for col in state.get("columns", []) if col in self.model().columns]
        columns = columns + [col for col in self.model().columns if col not in columns]

        self.model().beginResetModel()
        self.model().columns = columns
        self.model().grouped_columns = [columns.index(name) for name in state.get("grouped_columns", [])]
        self.model().current_query = state.get("current_query", "")
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

