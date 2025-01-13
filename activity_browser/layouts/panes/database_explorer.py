from logging import getLogger

import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Signal, SignalInstance

import bw2data as bd

from activity_browser import actions, ui, project_settings, application, signals
from activity_browser.ui import core
from activity_browser.bwutils import AB_metadata

log = getLogger(__name__)


DEFAULT_STATE = {
    "columns": ["Activity", "Product", "Type", "Unit", "Location"],
    "visible_columns": ["Activity", "Product", "Type", "Unit", "Location"],
}


NODETYPES = {
    "all_nodes": [],
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}


class DatabaseExplorer(QtWidgets.QWidget):

    def __init__(self, db_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database Explorer")

        self.database = bd.Database(db_name)
        self.model = NodeModel(self)

        # Create the QTableView and set the model
        self.table_view = NodeView(self)
        self.table_view.setModel(self.model)
        self.model.setDataFrame(pd.DataFrame.from_dict(bd.Database(db_name).load(), orient="index"))

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
        full_df = AB_metadata.get_database_metadata(self.database.name)

        expected = ["processor", "product", "type", "unit", "location", "id", "categories"]
        for column_name in expected:
            if column_name not in full_df.columns:
                full_df[column_name] = None

        with_processor = full_df[full_df.processor.isin(full_df.key)].copy()
        with_processor["process_name"] = full_df.loc[with_processor.processor].set_index(with_processor.index).name
        with_processor["process_id"] = full_df.loc[with_processor.processor].set_index(with_processor.index).id

        no_processor = full_df[full_df.processor.isin(full_df.key) == False].copy()
        no_processor.drop(no_processor[no_processor.key.isin(with_processor.processor)].index, inplace=True)
        no_processor.drop(no_processor[no_processor.type == "readonly_process"].index, inplace=True)

        final = pd.DataFrame({
            "Activity": list(with_processor["process_name"]) + list(no_processor["name"]),
            "Product": list(with_processor["name"]) + list(no_processor["product"]),
            "Type": list(with_processor["type"]) + list(no_processor["type"]),
            "Unit": list(with_processor["unit"]) + list(no_processor["unit"]),
            "Location": list(with_processor["location"]) + list(no_processor["location"]),
            "Categories": list(with_processor["categories"]) + list(no_processor["categories"]),
            "Product Key": list(with_processor["key"]) + [None] * len(no_processor),
            "Product ID": list(with_processor["id"]) + [None] * len(no_processor),
            "Activity Key": list(with_processor["processor"]) + list(no_processor["key"]),
            "Activity ID": list(with_processor["process_id"]) + list(no_processor["id"]),
        })

        if "properties" in with_processor.columns:
            for key, props in with_processor["properties"].dropna().items():
                if not isinstance(props, dict):
                    continue

                for prop, value in props.items():
                    final.loc[final["Product Key"] == key, f"Property: {prop}"] = value

        return final

    def event(self, event):
        if event.type() == QtCore.QEvent.Type.DeferredDelete:
            self.save_state_to_settings()

        return super().event(event)

    def search_error(self, reset=False):
        if reset:
            self.search.setPalette(application.palette())
            return

        palette = self.search.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 128, 128))
        self.search.setPalette(palette)


class NodeView(ui.widgets.ABTreeView):
    query_changed: SignalInstance = Signal(bool)

    def __init__(self, parent: DatabaseExplorer):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.SelectionMode.ExtendedSelection)

        self.allFilter = ""

    # def mouseDoubleClickEvent(self, event) -> None:
    #     if self.selected_activities:
    #         actions.ActivityOpen.run(self.selected_activities)

    def setAllFilter(self, query: str):
        self.allFilter = query
        try:
            self.applyFilter()
            self.query_changed.emit(True)
        except Exception as e:
            print(f"Error in query: {type(e).__name__}: {e}")
            self.query_changed.emit(False)

    def buildQuery(self) -> str:
        node_query = ""

        if self.allFilter.startswith('='):
            return super().buildQuery() + f" & ({self.allFilter[1:]})" + node_query

        col_names = [self.model().columns[i] for i in range(len(self.model().columns)) if not self.isColumnHidden(i)]

        q = " | ".join([f"(`{col}`.astype('str').str.contains('{self.format_query(self.allFilter)}', False))" for col in col_names])
        return super().buildQuery() + f" & ({q})" + node_query if q else super().buildQuery() + node_query


class NodeModel(ui.widgets.ABAbstractItemModel):

    def createItems(self, dataframe=None) -> list[ui.widgets.ABDataItem]:
        items = []
        for index, data in dataframe.to_dict(orient="index").items():
            items.append(NodeItem(index, data))
        return items

    def mimeData(self, indices: [QtCore.QModelIndex]):
        data = core.ABMimeData()
        keys = set(self.values_from_indices("Activity Key", indices))
        keys.update(self.values_from_indices("Product Key", indices))
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


class NodeItem(ui.widgets.ABDataItem):
    pass

