from logging import getLogger

import pandas as pd

from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import Qt

import bw2data as bd
import bw_functional as bf

from activity_browser import signals, actions
from activity_browser.bwutils import AB_metadata, refresh_node
from activity_browser.ui import widgets as ABwidgets
from activity_browser.ui.web import GraphNavigatorWidget

from .activity_data import ActivityData
from .views import ExchangeView
from .models import ExchangeModel

log = getLogger(__name__)

NODETYPES = {
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}

EXCHANGE_MAP = {
    "natural resource": "biosphere", "emission": "biosphere", "inventory indicator": "biosphere",
    "economic": "biosphere", "social": "biosphere", "product": "technosphere",
    "processwithreferenceproduct": "technosphere", "waste": "technosphere",
}


class ActivityDetails(QtWidgets.QWidget):
    _populate_later_flag = False

    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        super().__init__(parent)
        self.activity = bd.get_activity(activity)

        # widgets
        self.activity_data_grid = ActivityData(self)
        self.tabs = QtWidgets.QTabWidget(self)

        # tabs
        self.exchanges_tab = ExchangesTab(activity, self)
        self.tabs.addTab(self.exchanges_tab, "Exchanges")

        self.description_tab = DescriptionTab(activity, self)
        self.tabs.addTab(self.description_tab, "Description")

        self.graph_explorer = GraphNavigatorWidget(self, key=self.activity.key)
        self.tabs.addTab(self.graph_explorer, "Graph")

        self.parameters_tab = QtWidgets.QLabel("WORK IN PROGRESS")
        self.tabs.addTab(self.parameters_tab, "Parameters")

        self.consumer_tab = ConsumersTab(activity, self)
        self.tabs.addTab(self.consumer_tab, "Consumers")

        self.explorer = QtWidgets.QLabel("WORK IN PROGRESS")
        self.tabs.addTab(self.explorer, "Activity Explorer")

        self.build_layout()
        self.sync()
        self.connect_signals()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # layout.addWidget(toolbar)
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(ABwidgets.ABHLine(self))
        layout.addWidget(self.tabs)

        self.setLayout(layout)

    def connect_signals(self):
        signals.node.deleted.connect(self.on_node_deleted)
        signals.database.deleted.connect(self.on_database_deleted)
        signals.meta.databases_changed.connect(self.syncLater)
        signals.parameter.recalculated.connect(self.syncLater)
        signals.node.changed.connect(self.syncLater)

    def on_node_deleted(self, node):
        if node.id == self.activity.id:
            self.deleteLater()

    def on_database_deleted(self, name):
        if name == self.activity["database"]:
            self.deleteLater()

    def syncLater(self):
        def slot():
            self._populate_later_flag = False
            self.sync()
            self.thread().eventDispatcher().awake.disconnect(slot)

        if self._populate_later_flag:
            return

        self._populate_later_flag = True
        self.thread().eventDispatcher().awake.connect(slot)

    def sync(self):
        self.activity = refresh_node(self.activity)
        # update the object name to be the activity name
        self.setObjectName(self.activity["name"])

        self.activity_data_grid.sync()
        self.exchanges_tab.sync()
        self.description_tab.sync()
        self.consumer_tab.sync()


class ExchangesTab(QtWidgets.QWidget):
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        super().__init__(parent)

        self.activity = refresh_node(activity)

        # Output Table
        self.output_view = ExchangeView(self)
        self.output_model = ExchangeModel(self)
        self.output_view.setModel(self.output_model)

        # Input Table
        self.input_view = ExchangeView(self)
        self.input_model = ExchangeModel(self)
        self.input_view.setModel(self.input_model)

        self.build_layout()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 1)

        layout.addWidget(QtWidgets.QLabel("<b>⠀Output:</b>"))
        layout.addWidget(self.output_view)
        layout.addWidget(QtWidgets.QLabel("<b>⠀Input:</b>"))
        layout.addWidget(self.input_view)

        self.setLayout(layout)

    def sync(self) -> None:
        """Populate the various tables and boxes within the Activity Detail tab"""
        self.activity = refresh_node(self.activity)

        # fill in the values of the ActivityTab widgets, excluding the ActivityDataGrid which is populated separately
        production = self.activity.production()
        technosphere = self.activity.technosphere()
        biosphere = self.activity.biosphere()

        inputs = ([x for x in production if x["amount"] < 0] +
                  [x for x in technosphere if x["amount"] >= 0] +
                  [x for x in biosphere if (x.input["type"] != "emission" and x["amount"] >= 0) or (x.input["type"] == "emission" and x["amount"] < 0)])

        outputs = ([x for x in production if x["amount"] >= 0] +
                   [x for x in technosphere if x["amount"] < 0] +
                   [x for x in biosphere if (x.input["type"] == "emission" and x["amount"] >= 0) or (x.input["type"] != "emission" and x["amount"] < 0)])

        self.output_model.setDataFrame(self.build_df(outputs))
        self.input_model.setDataFrame(self.build_df(inputs))

    def build_df(self, exchanges) -> pd.DataFrame:
        cols = ["key", "unit", "name", "location", "substitute", "substitution_factor", "allocation_factor",
                "properties", "processor"]
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "formula", "uncertainty",])
        act_df = AB_metadata.get_metadata(exc_df["input"].unique(), cols)

        df = exc_df.merge(
            act_df,
            left_on="input",
            right_on="key"
        ).drop(columns=["key"])

        if not df["substitute"].isna().all():
            df = df.merge(
                AB_metadata.dataframe[["key", "name"]].rename({"name": "substitute_name"}, axis="columns"),
                left_on="substitute",
                right_on="key",
                how="left",
            ).drop(columns=["key"])
        else:
            df.drop(columns=["substitute", "substitution_factor"], inplace=True)

        if not act_df.properties.isna().all():
            props_df = act_df[act_df.properties.notna()]
            props_df = pd.DataFrame(list(props_df.get("properties")), index=props_df.key)
            props_df.rename(lambda col: f"property_{col}", axis="columns", inplace=True)

            df = df.merge(
                props_df,
                left_on="input",
                right_index=True,
                how="left",
            )

        df["_allocate_by"] = self.activity.get("allocation")
        df["_activity_type"] = self.activity.get("type")
        df["_exchange"] = exchanges

        df.drop(columns=["properties"], inplace=True)
        df.rename({"input": "_input_key", "substitute": "_substitute_key", "processor": "_processor_key"}, axis="columns", inplace=True)

        cols = ["amount", "unit", "name", "location"]
        cols += ["substitute_name", "substitution_factor"] if "substitute_name" in df.columns else []
        cols += ["allocation_factor"]
        cols += [col for col in df.columns if col.startswith("property")]
        cols += ["formula", "uncertainty"]
        cols += [col for col in df.columns if col.startswith("_")]

        return df[cols]


class DescriptionTab(QtWidgets.QTextEdit):
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        self.activity = refresh_node(activity)
        super().__init__(parent, self.activity.get("comment", ""))

    def sync(self):
        self.activity = refresh_node(self.activity)
        self.setText(self.activity.get("comment", ""))
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def focusOutEvent(self, e):
        if self.toPlainText() == self.activity.get("comment", ""):
            return
        actions.ActivityModify.run(self.activity, "comment", self.toPlainText())


class ConsumersTab(QtWidgets.QWidget):
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        super().__init__(parent)

        self.activity = refresh_node(activity)

        self.view = ABwidgets.ABTreeView(self)
        self.model = ABwidgets.ABAbstractItemModel(self)
        self.view.setModel(self.model)

        self.build_layout()
        self.sync()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 1)
        layout.addWidget(self.view)
        self.setLayout(layout)

    def sync(self):
        self.activity = refresh_node(self.activity)
        exchanges = []
        if isinstance(self.activity, bf.Process):
            for function in self.activity.functions():
                exchanges += list(function.upstream())
        else:
            exchanges = list(self.activity.upstream())

        self.model.setDataFrame(pd.DataFrame(exchanges))
