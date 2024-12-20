from logging import getLogger

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
    "columns": ["name", "activity", "activity type", "location", "unit"],
    "visible_columns": ["name", "activity", "activity type", "location", "unit"],
}


NODETYPES = {
    "all_nodes": [],
    "processes": ["process", "multifunctional", "processwithreferenceproduct"],
    "products": ["product", "processwithreferenceproduct"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic"],
}


class DatabaseExplorer(QtWidgets.QWidget):

    def __init__(self, parent, db_name: str):
        super().__init__(parent)
        self.database = bd.Database(db_name)
        self.model = NodeModel(self)

        # Create the QTableView and set the model
        self.table_view = NodeView(self)
        self.table_view.setModel(self.model)
        self.model.setDataFrame(AB_metadata.get_database_metadata(db_name))
        self.table_view.restoreSate(self.get_state_from_settings())

        self.search = QtWidgets.QLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.search.textChanged.connect(self.table_view.setAllFilter)

        self.tab_bar = QtWidgets.QTabBar(self)
        self.tab_bar.setShape(QtWidgets.QTabBar.RoundedEast)

        self.tab_bar.addTab("All Nodes")
        self.tab_bar.addTab("Processes")
        self.tab_bar.addTab("Products")
        self.tab_bar.addTab("Biosphere")

        self.tab_bar.tabBarClicked.connect(self.switch_types)

        table_layout = QtWidgets.QHBoxLayout()
        table_layout.setSpacing(0)
        table_layout.addWidget(self.table_view)
        table_layout.addWidget(self.tab_bar)
        table_layout.setAlignment(self.tab_bar, QtCore.Qt.AlignmentFlag.AlignTop)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.search)
        layout.addLayout(table_layout)

        # Set the table view as the central widget of the window
        self.setLayout(layout)

        # connect signals
        signals.database.delete.connect(self.deleteLater)
        AB_metadata.synced.connect(self.sync)
        self.table_view.query_changed.connect(self.search_error)

    def sync(self):
        self.model.setDataFrame(AB_metadata.get_database_metadata(self.database.name))

    def switch_types(self, index) -> None:
        node_map = ["all_nodes", "processes", "products", "biosphere"]
        key = node_map[index]
        self.table_view.setNodeTypes(NODETYPES[key])
        return

    def event(self, event):
        if event.type() == QtCore.QEvent.DeferredDelete:
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


class NodeViewMenuFactory(ui.widgets.ABTreeView.menuFactoryClass):

    def createMenu(self, pos: QtCore.QPoint):
        """Designed to be passed to customContextMenuRequested.connect"""
        if self.view.indexAt(pos).row() == -1:
            menu = NodeViewContextMenu.init_none(self.view)
        else:
            menu = NodeViewContextMenu.init_single(self.view)
        menu.exec_(self.view.mapToGlobal(pos))


class NodeView(ui.widgets.ABTreeView):
    query_changed: SignalInstance = Signal(bool)
    menuFactoryClass = NodeViewMenuFactory

    def __init__(self, parent: DatabaseExplorer):
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


class NodeViewContextMenu(QtWidgets.QMenu):
    def __init__(self, parent: NodeView):
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
    def init_none(cls, parent: NodeView):
        menu = cls(parent)

        menu.clear()
        menu.addAction(menu.process_new)

        return menu

    @classmethod
    def init_single(cls, parent: NodeView):
        menu = cls(parent)

        menu.activity_open.setText(f"Open activity")
        menu.activity_graph.setText(f"Open activity in Graph Explorer")
        menu.activity_duplicate.setText(f"Duplicate activity")
        menu.activity_delete.setText(f"Delete activity")

        return menu

    @classmethod
    def init_multiple(cls, parent: NodeView):
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


class NodeModel(ui.widgets.ABAbstractItemModel):

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

    def createItems(self) -> list[ui.widgets.ABDataItem]:
        items = []
        for index, data in self.dataframe.to_dict(orient="index").items():
            if data["type"] in ["process", "multifunctional", "readonly_process"]:
                items.append(ProcessItem(index, data))
            elif data["type"] in NODETYPES["products"]:
                items.append(ProductItem(index, data))
            elif data["type"] in NODETYPES["biosphere"]:
                items.append(BiosphereItem(index, data))
            else:
                items.append(ui.widgets.ABDataItem(index, data))
        return items


class ProcessItem(ui.widgets.ABDataItem):

    def __init__(self, index, data):
        super().__init__(index, data)
        self.deferred_child_keys = []
        self.deferred_child_values = {}
        self.loaded = False

    def has_children(self) -> bool:
        return True

    def children(self):
        if not self.loaded:
            self.deferred_load()

        return self._child_items

    def decorationData(self, key):
        if key != "name":
            return
        if self["type"] in ["process", "multifunctional"]:
            return ui.icons.qicons.process
        elif self["type"] == "readonly_process":
            return ui.icons.qicons.readonly_process

    def deferred_load(self):
        import bw2data as bd

        self.loaded = True

        act = bd.get_activity(key=self.data["key"])
        try:
            products = [x.input for x in act.production()]
        except UnknownObject:
            log.error(f"Broken exchanges for product: {self.data["name"]}")
            return

        for product in products:
            data = dict(product)
            data["key"] = product.key
            item = ProductItem(product.id, data)
            item.set_parent(self)


class ProductItem(ui.widgets.ABDataItem):
    def decorationData(self, key):
        if key != "name":
            return
        if self["type"] == "product":
            return ui.icons.qicons.product
        elif self["type"] == "processwithreferenceproduct":
            return ui.icons.qicons.processproduct


class BiosphereItem(ui.widgets.ABDataItem):
    def decorationData(self, key):
        if key != "name":
            return
        return ui.icons.qicons.biosphere


