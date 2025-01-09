from logging import getLogger

import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Signal, SignalInstance

import bw2data as bd
from bw2data.backends import ActivityDataset
from bw2data.errors import UnknownObject

from activity_browser import actions, ui, project_settings, application, signals
from activity_browser.ui import core
from activity_browser.bwutils import AB_metadata

log = getLogger(__name__)


DEFAULT_STATE = {
    "columns": ["process_name", "name", "type", "unit", "location"],
    "visible_columns": ["process_name", "name", "type", "unit", "location"],
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

        self.search = QtWidgets.QLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.search.textChanged.connect(self.table_view.setAllFilter)

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
        self.table_view.query_changed.connect(self.search_error)

    def sync(self):
        self.model.setDataFrame(self.build_df())

    def build_df(self) -> pd.DataFrame:
        df = AB_metadata.get_database_metadata(self.database.name)
        prods = df[df.type.isin(NODETYPES["products"] + NODETYPES["biosphere"])].copy()
        if "processor" in prods.columns:
            prods["process_name"] = df.loc[prods.processor].set_index(prods.index).name
        return prods.dropna(axis=1, how="all")

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.DeferredDelete:
            self.save_state_to_settings()

        return super().event(event)

    def save_state_to_settings(self):
        project_settings.settings["database_explorer"] = project_settings.settings.get("database_explorer", {})
        project_settings.settings["database_explorer"][self.database.name] = self.table_view.saveState()
        project_settings.write_settings()

    def get_state_from_settings(self):
        return project_settings.settings.get("database_explorer", {}).get(self.database.name, DEFAULT_STATE)

    def search_error(self, reset=False):
        if reset:
            self.search.setPalette(application.palette())
            return

        palette = self.search.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 128, 128))
        self.search.setPalette(palette)


class ProductViewMenuFactory(ui.widgets.ABTreeView.menuFactoryClass):

    def createMenu(self, pos: QtCore.QPoint):
        """Designed to be passed to customContextMenuRequested.connect"""
        if self.view.indexAt(pos).row() == -1:
            menu = ProductViewContextMenu.init_none(self.view)
        else:
            menu = ProductViewContextMenu.init_single(self.view)
        menu.exec_(self.view.mapToGlobal(pos))


class ProductView(ui.widgets.ABTreeView):
    query_changed: SignalInstance = Signal(bool)
    menuFactoryClass = ProductViewMenuFactory

    def __init__(self, parent: DatabaseProductViewer):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragOnly)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.ExtendedSelection)

        self.allFilter = ""
        self.nodeTypes = []

    def mouseDoubleClickEvent(self, event) -> None:
        if self.selected_keys:
            actions.ActivityOpen.run(self.selected_keys)

    def setAllFilter(self, query: str):
        self.allFilter = query
        try:
            self.applyFilter()
            self.query_changed.emit(True)
        except Exception as e:
            print(f"Error in query: {type(e).__name__}: {e}")
            self.query_changed.emit(False)

    def setNodeTypes(self, node_types: list):
        self.nodeTypes = node_types
        self.applyFilter()

    def buildQuery(self) -> str:
        if self.nodeTypes:
            node_query = " | ".join([f"(type == '{node_type}')" for node_type in self.nodeTypes])
            node_query = f" & ({node_query})"
        else:
            node_query = ""

        if self.allFilter.startswith('='):
            return super().buildQuery() + f" & ({self.allFilter[1:]})" + node_query

        col_names = [self.model().columns[i] for i in range(1, len(self.model().columns)) if not self.isColumnHidden(i)]

        q = " | ".join([f"(`{col}`.astype('str').str.contains('{self.format_query(self.allFilter)}'))" for col in col_names])
        return super().buildQuery() + f" & ({q})" + node_query if q else super().buildQuery() + node_query

    @property
    def selected_keys(self) -> [tuple]:
        return self.model().get_keys(self.selectedIndexes())


class ProductViewContextMenu(QtWidgets.QMenu):
    def __init__(self, parent: ProductView):
        super().__init__(parent)

        self.activity_open = actions.ActivityOpen.get_QAction(parent.selected_keys)
        self.activity_graph = actions.ActivityGraph.get_QAction(parent.selected_keys)
        self.process_new = actions.ActivityNewProcess.get_QAction(parent.parent().database.name)
        self.activity_delete = actions.ActivityDelete.get_QAction(parent.selected_keys)
        self.activity_relink = actions.ActivityRelink.get_QAction(parent.selected_keys)

        self.activity_duplicate = actions.ActivityDuplicate.get_QAction(parent.selected_keys)
        self.activity_duplicate_to_loc = actions.ActivityDuplicateToLoc.get_QAction(parent.selected_keys[0] if parent.selected_keys else None)
        self.activity_duplicate_to_db = actions.ActivityDuplicateToDB.get_QAction(parent.selected_keys)

        self.copy_sdf = QtWidgets.QAction(ui.icons.qicons.superstructure, "Exchanges for scenario difference file", None)

        self.addAction(self.activity_open)
        self.addAction(self.activity_graph)
        self.addAction(self.process_new)
        self.addMenu(self.duplicates_menu())
        self.addAction(self.activity_delete)
        self.addAction(self.activity_relink)
        self.addMenu(self.copy_menu())

    @classmethod
    def init_none(cls, parent: ProductView):
        menu = cls(parent)

        menu.clear()
        menu.addAction(menu.process_new)

        return menu

    @classmethod
    def init_single(cls, parent: ProductView):
        menu = cls(parent)

        menu.activity_open.setText(f"Open activity")
        menu.activity_graph.setText(f"Open activity in Graph Explorer")
        menu.activity_duplicate.setText(f"Duplicate activity")
        menu.activity_delete.setText(f"Delete activity")

        return menu

    @classmethod
    def init_multiple(cls, parent: ProductView):
        menu = cls(parent)

        menu.activity_open.setText(f"Open activities")
        menu.activity_graph.setText(f"Open activities in Graph Explorer")
        menu.activity_duplicate.setText(f"Duplicate activities")
        menu.activity_delete.setText(f"Delete activities")

        menu.activity_duplicate_to_loc.setEnabled(False)
        menu.activity_relink.setEnabled(False)

        return menu

    def duplicates_menu(self):
        menu = QtWidgets.QMenu(self)

        menu.setTitle(f"Duplicate activities")
        menu.setIcon(ui.icons.qicons.copy)

        menu.addAction(self.activity_duplicate)
        menu.addAction(self.activity_duplicate_to_loc)
        menu.addAction(self.activity_duplicate_to_db)
        return menu

    def copy_menu(self):
        menu = QtWidgets.QMenu(self)

        menu.setTitle(f"Copy to clipboard")
        menu.setIcon(ui.icons.qicons.copy_to_clipboard)

        menu.addAction(self.copy_sdf)
        return menu


class ProductModel(ui.widgets.ABAbstractItemModel):

    def mimeData(self, indices: [QtCore.QModelIndex]):
        data = core.ABMimeData()
        data.setPickleData("application/bw-nodekeylist", self.get_keys(indices))
        return data

    def get_keys(self, indices: list[QtCore.QModelIndex]):
        keys = []
        for index in indices:
            item = index.internalPointer()
            if not item:
                continue
            keys.append(item["key"])
        return list(set(keys))

    def createItems(self, dataframe=None) -> list[ui.widgets.ABDataItem]:
        items = []
        for index, data in dataframe.to_dict(orient="index").items():
            if data["type"] in NODETYPES["products"]:
                items.append(ProductItem(index, data))
            elif data["type"] in NODETYPES["biosphere"]:
                items.append(BiosphereItem(index, data))
            else:
                items.append(ui.widgets.ABDataItem(index, data))
        return items


class ProductItem(ui.widgets.ABDataItem):
    def decorationData(self, col, key):
        if key == "name":
            if self["type"] == "product":
                return ui.icons.qicons.product
            elif self["type"] == "waste":
                return ui.icons.qicons.waste
            elif self["type"] == "processwithreferenceproduct":
                return ui.icons.qicons.processproduct
        if key == "process_name":
            return ui.icons.qicons.process


class BiosphereItem(ui.widgets.ABDataItem):
    def decorationData(self, col, key):
        if key != "name":
            return
        return ui.icons.qicons.biosphere


