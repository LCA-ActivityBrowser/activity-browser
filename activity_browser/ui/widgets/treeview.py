from qtpy import QtWidgets, QtCore, QtGui

from .abstractitemmodel import ABAbstractItemModel


class ABTreeView(QtWidgets.QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setUniformRowHeights(True)

        header = self.header()
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.header_popup)

        self.expanded_paths = set()
        self.expanded.connect(lambda index: self.expanded_paths.add(tuple(index.internalPointer().path)))
        self.collapsed.connect(lambda index: self.expanded_paths.discard(tuple(index.internalPointer().path)))

    def setModel(self, model):
        if not isinstance(model, ABAbstractItemModel):
            raise TypeError("Model must be an instance of ABAbstractItemModel")
        super().setModel(model)

        self.setColumnHidden(0, True)
        model.grouped.connect(lambda groups: self.setColumnHidden(0, not groups))
        model.modelReset.connect(self.expand_after_reset)

    def expand_after_reset(self):
        indices = [self.model().indexFromPath(list(path)) for path in self.expanded_paths]
        for index in indices:
            self.expand(index)

    def header_popup(self, pos: QtCore.QPoint):
        col = self.columnAt(pos.x())
        if col == 0:
            menu = self.group_col_menu()
        else:
            menu = self.col_menu(col)
        menu.exec_(self.mapToGlobal(pos))

    def col_menu(self, column: int):
        menu = QtWidgets.QMenu(self)

        search_box = QtWidgets.QLineEdit(menu)
        search_box.setText(self.model().filters.get(self.model().headerData(column), ""))
        search_box.setPlaceholderText("Search")

        search_box.textChanged.connect(lambda q: self.model().filter(q, column))
        widget_action = QtWidgets.QWidgetAction(menu)
        widget_action.setDefaultWidget(search_box)
        menu.addAction(widget_action)

        menu.addAction(
            QtGui.QIcon(),
            "Group by column",
            lambda: self.model().group(column),
        )
        menu.addSeparator()
        menu.addMenu(self.view_menu())
        return menu

    def group_col_menu(self):
        menu = QtWidgets.QMenu(self)
        menu.addAction(
            QtGui.QIcon(),
            "Ungroup",
            self.model().ungroup,
        )
        return menu

    def view_menu(self) -> QtWidgets.QMenu:

        def toggle_slot(action: QtWidgets.QAction):
            index = action.data()
            hidden = self.isColumnHidden(index)
            self.setColumnHidden(index, not hidden)

        menu = QtWidgets.QMenu(self)
        menu.setTitle("View")
        self.view_actions = []

        for i in range(1, len(self.model().dataframe.columns)):
            action = QtWidgets.QAction(self.model().headerData(i))
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(i))
            action.setData(i)
            menu.addAction(action)
            self.view_actions.append(action)

        menu.triggered.connect(toggle_slot)

        return menu
