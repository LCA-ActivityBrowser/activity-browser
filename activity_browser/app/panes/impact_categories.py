from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import app, app
from activity_browser.ui import widgets, core, delegates


class ImpactCategoriesPane(widgets.ABAbstractPane):
    title = "Impact Categories"
    unique = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = ImpactCategoriesModel(parent=self)
        self.view = ImpactCategoriesView()
        self.view.setModel(self.model)

        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.view.setDragEnabled(True)
        self.view.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.search = widgets.ABLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.search.textChangedDebounce.connect(self.view.setAllFilter)

        self.build_layout()
        self.connect_signals()
        self.load()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.search)
        layout.addWidget(self.view)
        layout.setContentsMargins(5, 0, 5, 5)

        self.setLayout(layout)

    def connect_signals(self):
        app.signals.meta.methods_changed.connect(self.sync)
        app.signals.project.changed.connect(self.sync)
        app.signals.database_read_only_changed.connect(self.sync)

    def load(self):
        df = self.build_df()
        self.model.set_dataframe(df)
        self.model.group(["_method_name"])
        # self.view.setColumnHidden(1, True)
        # self.view.setColumnHidden(2, True)
        # self.view.setColumnHidden(3, True)
        # self.view.sortByColumn(1, Qt.SortOrder.AscendingOrder)

    def sync(self):
        df = self.build_df()
        self.model.set_dataframe(df)
        self.model.group(["_method_name"])

    def build_df(self):
        df = pd.DataFrame(bd.methods.values())
        df["_method_name"] = bd.methods.keys()

        df["name"] = df["_method_name"].apply(lambda x: x[-1])

        cols = ["name", "unit", "num_cfs", "_method_name"]

        if df.empty:
            return pd.DataFrame(columns=cols)

        return df[cols]


class ImpactCategoriesView(widgets.ABNewTreeView):
    defaultColumnDelegates = {
        "groups": delegates.ListDelegate,
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(app.actions.MethodNew),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.MethodOpen, p.selected_impact_categories,
                               text="Open impact category" if len(p.selected_impact_categories) == 1 else "Open impact categories",
                               enable=len(p.selected_impact_categories) > 0
                               ),
            lambda m, p: m.add(app.actions.MethodDelete, p.selected_impact_categories,
                               text="Delete impact category" if len(
                                   p.selected_impact_categories) == 1 else "Delete impact categories",
                               enable=len(p.selected_impact_categories) > 0
                               ),
            lambda m, p: m.add(app.actions.MethodDuplicate, p.selected_impact_categories,
                               text="Duplicate impact category",
                               enable=len(p.selected_impact_categories) == 1
                               ),
            lambda m, p: m.add(app.actions.MethodRename, p.selected_impact_categories,
                               text="Rename impact category",
                               enable=len(p.selected_impact_categories) == 1
                               ),
        ]

    @property
    def selected_impact_categories(self):
        if not self.selectedIndexes():
            return []
        
        indices = [i for i in self.selectedIndexes() if i.column() == 0]
        impact_categories = []

        for index in indices:
            impact_categories.extend(self.model().get_impact_categories(index))

        return list(set(impact_categories))

    def mouseDoubleClickEvent(self, event) -> None:
        if self.selected_impact_categories:
            app.actions.MethodOpen.run(self.selected_impact_categories)


class ImpactCategoriesModel(core.ABTreeModel):
    """
    A model representing the data for the impact categories.
    """

    def indexDragEnabled(self, index: QtCore.QModelIndex) -> bool:
        """Enable drag for all items."""
        return True

    def mimeData(self, indices: list[QtCore.QModelIndex]):
        """
        Returns the mime data for the given indices.

        Args:
            indices (list[QtCore.QModelIndex]): The indices to get the mime data for.

        Returns:
            core.ABMimeData: The mime data.
        """
        data = core.ABMimeData()
        names = []

        for index in indices:
            names += self.get_impact_categories(index)

        data.setPickleData("application/bw-methodnamelist", list(set(names)))
        return data

    def get_impact_categories(self, index: QtCore.QModelIndex):
        """
        Get all impact category method names for the given index.
        
        For leaf nodes (full depth paths), returns the single method name.
        For branch nodes (partial depth paths), returns all child method names.
        
        Args:
            index: The index to get impact categories for.
            
        Returns:
            list: List of method name tuples.
        """
        if not index.isValid():
            return []
        
        node = index.internalPointer()
        
        if not isinstance(node, core.TreeNode):
            return []
        
        # If this is a leaf node, return its method name
        if node.is_leaf:
            row = self.row(index)
            if row is not None:
                return [row["_method_name"]]
            return []
        
        # If this is a branch node, collect all child method names recursively
        ics = []
        for i, child_node in enumerate(node.children):
            if i >= node.loaded_count:
                break  # Only process loaded children
            child_index = self.createIndex(i, 0, child_node)
            ics += self.get_impact_categories(child_index)
        
        return ics

