from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import signals, actions
from activity_browser.ui import widgets, core, delegates


class ImpactCategoriesPane(widgets.ABAbstractPane):
    title = "Impact Categories"
    unique = True

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = ImpactCategoriesView()
        self.model = ImpactCategoriesModel()
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
        signals.meta.methods_changed.connect(self.sync)
        signals.project.changed.connect(self.sync)
        signals.database_read_only_changed.connect(self.sync)

    def load(self):
        self.model.setDataFrame(self.build_df())
        self.model.group(1)
        self.view.setColumnHidden(1, True)
        self.view.setColumnHidden(2, True)
        self.view.setColumnHidden(3, True)
        self.view.sortByColumn(1, Qt.SortOrder.AscendingOrder)

    def sync(self):
        self.model.setDataFrame(self.build_df())

    def build_df(self):
        df = pd.DataFrame(bd.methods.values())
        df["_method_name"] = bd.methods.keys()

        df["name"] = df["_method_name"].apply(lambda x: x[-1])
        df["groups"] = df["_method_name"].apply(lambda x: x[:-1])

        cols = ["name", "groups", "unit", "num_cfs", "_method_name"]

        if df.empty:
            return pd.DataFrame(columns=cols)

        return df[cols]


class ImpactCategoriesView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "groups": delegates.ListDelegate,
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(actions.MethodOpen, p.selected_impact_categories,
                               text="Open impact category" if len(p.selected_impact_categories) == 1 else "Open impact categories",
                               enable=len(p.selected_impact_categories) > 0
                               ),
            lambda m, p: m.add(actions.MethodDelete, p.selected_impact_categories,
                               text="Delete impact category" if len(
                                   p.selected_impact_categories) == 1 else "Delete impact categories",
                               enable=len(p.selected_impact_categories) > 0
                               ),
            lambda m, p: m.add(actions.MethodDuplicate, p.selected_impact_categories,
                               text="Duplicate impact category",
                               enable=len(p.selected_impact_categories) == 1
                               ),
            lambda m, p: m.add(actions.MethodRename, p.selected_impact_categories,
                               text="Rename impact category",
                               enable=len(p.selected_impact_categories) == 1
                               ),
        ]

        @staticmethod
        def get_functional_unit_amount(key):
            from activity_browser.bwutils import refresh_node
            excs = list(refresh_node(key).upstream(["production"]))
            exc = excs[0] if len(excs) == 1 else {}
            return exc.get("amount", 1.0)

        @property
        def database_name(self):
            return self.parent().parent().database.name

    @property
    def selected_impact_categories(self):
        indices = [i for i in self.selectedIndexes() if i.column() == 0]
        impact_categories = []

        for index in indices:
            impact_categories.extend(self.model().get_impact_categories(index))

        return list(set(impact_categories))

    def mouseDoubleClickEvent(self, event) -> None:
        if self.selected_impact_categories:
            actions.MethodOpen.run(self.selected_impact_categories)


class ImpactCategoriesItem(widgets.ABDataItem):
    def flags(self, col: int, key: str):
        """
        Returns the item flags for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the flags.

        Returns:
            QtCore.Qt.ItemFlags: The item flags.
        """
        return super().flags(col, key) | Qt.ItemFlag.ItemIsDragEnabled


class ImpactCategoriesBranchItem(widgets.ABBranchItem):
    def flags(self, col: int, key: str):
        """
        Returns the item flags for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the flags.

        Returns:
            QtCore.Qt.ItemFlags: The item flags.
        """
        return super().flags(col, key) | Qt.ItemFlag.ItemIsDragEnabled


class ImpactCategoriesModel(widgets.ABItemModel):
    dataItemClass = ImpactCategoriesItem
    branchItemClass = ImpactCategoriesBranchItem

    def mimeData(self, indices: [QtCore.QModelIndex]):
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
        if isinstance(index.internalPointer(), self.dataItemClass):
            return [index.internalPointer()["_method_name"]]

        ics = []
        for i, child in enumerate(index.internalPointer().children().values()):
            child_index = self.createIndex(i, 0, child)
            ics += self.get_impact_categories(child_index)
        return ics

