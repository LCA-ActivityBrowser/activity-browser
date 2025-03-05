from logging import getLogger
from time import time

import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import bw2data as bd

from activity_browser import actions, ui, project_settings, application, signals
from activity_browser.ui import core, widgets
from activity_browser.ui.tables import delegates
from activity_browser.bwutils import AB_metadata

log = getLogger(__name__)


DEFAULT_STATE = {
    "columns": ["activity", "product", "Type", "Unit", "Location"],
    "visible_columns": ["activity", "product", "type", "unit", "location"],
}


NODETYPES = {
    "all_nodes": [],
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}


class DatabaseProductViewer(QtWidgets.QWidget):

    def __init__(self, parent, db_name: str):
        super().__init__(parent)
        self.database = bd.Database(db_name)
        self.model = ProductModel(self)

        # Create the QTableView and set the model
        self.table_view = ProductView(self)
        self.table_view.setModel(self.model)
        self.table_view.restoreSate(self.get_state_from_settings(), self.build_df())

        self.search = widgets.ABLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.search.textChangedDebounce.connect(self.table_view.setAllFilter)

        table_layout = QtWidgets.QHBoxLayout()
        table_layout.setSpacing(0)
        table_layout.addWidget(self.table_view)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addLayout(table_layout)

        # Set the table view as the central widget of the window
        self.setLayout(layout)

        # connect signals
        signals.database.deleted.connect(self.deleteLater)
        AB_metadata.synced.connect(self.sync)
        self.table_view.filtered.connect(self.search_error)

    def sync(self):
        t = time()
        self.model.setDataFrame(self.build_df())
        log.debug(f"Synced DatabaseProductViewer in {time() - t:.2f} seconds")

    def build_df(self) -> pd.DataFrame:
        t = time()
        cols = ["name", "key", "processor", "product", "type", "unit", "location", "id", "categories", "properties"]
        if self.database.name in AB_metadata.databases:
            full_df = AB_metadata.dataframe.loc[self.database.name].reindex(cols, axis="columns")
        else:
            full_df = pd.DataFrame(columns=cols)
        full_df["processor"] = full_df["processor"].astype(object)

        df = full_df.merge(
            full_df[["name", "key"]].rename({"name": "processor_name", "key": "processor_key"}, axis="columns"),
            left_on="processor",
            right_on="processor_key",
            how="left",
        )

        # "activity"
        # node.name by default, but processor.name in case of a Function
        df["activity"] = df["name"]
        df.update(df["processor_name"].rename("activity"))

        # "product"
        # node.name for "product"-types, overwritten by node.product
        df["product_name"] = df[df.type == "product"]["name"]
        df.update(df["product"].rename("product_name"))
        df["product"] = df["product_name"]

        # "activity_key"
        # activity that's opened on double click
        # node.key by default, but node.processor in case of a Function
        df["activity_key"] = df["key"]
        df.update(df["processor"].rename("activity_key"))

        # "function_key"
        # function or product of an activity
        # node.key by default, but function.key
        df["function_key"] = df["key"]

        # drop all processes that have functions
        df = df.drop(df[df.key.isin(df.processor)].index)

        if not df.properties.isna().all():
            props_df = df[df.properties.notna()]
            props_df = pd.DataFrame(list(props_df.get("properties")), index=props_df.key)
            props_df.rename(lambda col: f"property_{col}", axis="columns", inplace=True)

            df = df.merge(
                props_df,
                left_on="key",
                right_index=True,
                how="left",
            )

        cols = ["activity", "product", "type", "unit", "location", "categories", "activity_key", "function_key"]
        cols += [col for col in df.columns if col.startswith("property")]

        log.debug(f"Built DatabaseProductViewer dataframe in {time() - t:.2f} seconds")

        return df[cols]

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.DeferredDelete:
            self.save_state_to_settings()

        return super().event(event)

    def save_state_to_settings(self):
        project_settings.settings["database_explorer"] = project_settings.settings.get("database_explorer", {})
        project_settings.settings["database_explorer"][self.database.name] = self.table_view.saveState()
        project_settings.write_settings()

    def get_state_from_settings(self):
        return DEFAULT_STATE

    def search_error(self, reset=False):
        if reset:
            self.search.setPalette(application.palette())
            return

        palette = self.search.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 128, 128))
        self.search.setPalette(palette)


class ProductView(ui.widgets.ABTreeView):
    defaultColumnDelegates = {
        "categories": delegates.ListDelegate
    }

    class ContextMenu(ui.widgets.ABTreeView.ContextMenu):
        def __init__(self, pos, view: "ProductView"):
            super().__init__(pos, view)
            self.num_products = len(view.selected_products)
            self.num_activities = len(view.selected_activities)

            self.activity_open = actions.ActivityOpen.get_QAction(view.selected_activities)
            self.activity_graph = actions.ActivityGraph.get_QAction(view.selected_activities)

            self.process_new = actions.ActivityNewProcess.get_QAction(view.parent().database.name)

            self.activity_delete = actions.ActivityDelete.get_QAction(view.selected_activities)
            self.product_delete = actions.ActivityDelete.get_QAction(view.selected_products)

            self.copy_sdf = actions.ActivitySDFToClipboard.get_QAction(view.selected_products)

            if view.indexAt(pos).row() == -1:
                self.addAction(self.process_new)
                return

            self.init_open()
            self.addAction(self.process_new)
            #self.addMenu(self.duplicates_menu())
            self.init_delete()
            #self.addAction(self.activity_relink)
            self.addMenu(self.copy_menu())

        def init_open(self):
            if self.num_activities == 0:
                return
            if self.num_activities == 1:
                self.activity_open.setText("Open activity")
                self.activity_graph.setText("Open activity in Graph Explorer")
            else:
                self.activity_open.setText("Open activities")
                self.activity_graph.setText("Open activities in Graph Explorer")

            self.addAction(self.activity_open)
            self.addAction(self.activity_graph)

        def init_delete(self):
            if self.num_activities == 1:
                self.activity_delete.setText("Delete activity")
            if self.num_activities > 1:
                self.activity_delete.setText("Delete activities")
            if self.num_activities > 0:
                self.addAction(self.activity_delete)

            if self.num_products == 1:
                self.product_delete.setText("Delete product")
            if self.num_products > 1:
                self.product_delete.setText("Delete products")
            if self.num_products > 0:
                self.addAction(self.product_delete)

        def duplicates_menu(self):
            menu = QtWidgets.QMenu(self)

            menu.setTitle("Duplicate products")
            menu.setIcon(ui.icons.qicons.copy)

            menu.addAction(self.activity_duplicate)
            menu.addAction(self.activity_duplicate_to_loc)
            menu.addAction(self.activity_duplicate_to_db)
            return menu

        def copy_menu(self):
            menu = QtWidgets.QMenu(self)

            menu.setTitle("Copy to clipboard")
            menu.setIcon(ui.icons.qicons.copy_to_clipboard)

            menu.addAction(self.copy_sdf)
            return menu

    def __init__(self, parent: DatabaseProductViewer):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.SelectionMode.ExtendedSelection)

    def mouseDoubleClickEvent(self, event) -> None:
        if self.selected_activities:
            actions.ActivityOpen.run(self.selected_activities)

    @property
    def selected_products(self) -> [tuple]:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ProductItem)]
        return list({item["function_key"] for item in items if item["function_key"] is not None})

    @property
    def selected_activities(self) -> [tuple]:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ProductItem)]
        return list({item["activity_key"] for item in items if item["activity_key"] is not None})


class ProductItem(ui.widgets.ABDataItem):
    def decorationData(self, col, key):
        if key == "activity" and self["activity"]:
            if self["type"] == "processwithreferenceproduct":
                return ui.icons.qicons.processproduct
            if self["type"] in NODETYPES["biosphere"]:
                return ui.icons.qicons.biosphere
            return ui.icons.qicons.process
        if key == "product":
            if self["type"] in ["product", "processwithreferenceproduct"]:
                return ui.icons.qicons.product
            elif self["type"] == "waste":
                return ui.icons.qicons.waste

    def flags(self, col: int, key: str):
        return super().flags(col, key) | Qt.ItemFlag.ItemIsDragEnabled


class ProductModel(ui.widgets.ABAbstractItemModel):
    dataItemClass = ProductItem

    def mimeData(self, indices: [QtCore.QModelIndex]):
        data = core.ABMimeData()
        keys = set(self.values_from_indices("activity_key", indices))
        keys.update(self.values_from_indices("function_key", indices))
        keys = {key for key in keys if isinstance(key, tuple)}
        data.setPickleData("application/bw-nodekeylist", list(keys))
        return data

    @staticmethod
    def values_from_indices(key: str, indices: list[QtCore.QModelIndex]):
        values = []
        for index in indices:
            item = index.internalPointer()
            if not item or item[key] is None:
                continue
            values.append(item[key])
        return values


