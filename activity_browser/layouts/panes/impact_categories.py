import datetime

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import signals, actions, project_settings, bwutils
from activity_browser.ui import widgets, core
from activity_browser.ui.tables import delegates


class ImpactCategories(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = ImpactCategoriesView()
        self.model = ImpactCategoriesModel()
        self.view.setModel(self.model)

        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.view.setDragEnabled(True)
        self.view.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)

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

        self.setLayout(layout)
        self.setMinimumHeight(150)

    def connect_signals(self):
        signals.meta.methods_changed.connect(self.sync)
        signals.project.changed.connect(self.sync)
        signals.database_read_only_changed.connect(self.sync)

    def load(self):
        self.model.setDataFrame(self.build_df())
        self.model.group(1)
        self.view.setColumnHidden(1, True)

    def sync(self):
        self.model.setDataFrame(self.build_df())

    def build_df(self):
        df = pd.DataFrame.from_dict(bd.methods, orient="index")
        df.index = df.index.to_flat_index()
        df.index.name = "_method_name"
        df = df.reset_index()

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

    @property
    def selected_impact_categories(self):
        return [x.internalPointer()["_method_name"] for x in self.selectedIndexes()]

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


class ImpactCategoriesModel(widgets.ABAbstractItemModel):
    dataItemClass = ImpactCategoriesItem

    def mimeData(self, indices: [QtCore.QModelIndex]):
        """
        Returns the mime data for the given indices.

        Args:
            indices (list[QtCore.QModelIndex]): The indices to get the mime data for.

        Returns:
            core.ABMimeData: The mime data.
        """
        data = core.ABMimeData()
        names = set([x.internalPointer()["_method_name"] for x in indices])
        data.setPickleData("application/bw-methodnamelist", list(names))
        return data

