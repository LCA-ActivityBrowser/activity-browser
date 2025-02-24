from logging import getLogger

import pandas as pd

from qtpy import QtCore, QtWidgets, QtGui

import bw2data as bd
import bw_functional as bf

from activity_browser import signals, actions
from activity_browser.bwutils import AB_metadata, refresh_node
from activity_browser.ui import widgets as ABwidgets

from .activity_header import ActivityHeader
from .graph_tab import GraphTab
from .exchanges_tab import ExchangesTab
from .parameters_tab import ParametersTab
from .views import ConsumersView
from .models import ConsumersModel

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
        self.activity_data_grid = ActivityHeader(self)
        self.tabs = QtWidgets.QTabWidget(self)

        # tabs
        self.exchanges_tab = ExchangesTab(activity, self)
        self.tabs.addTab(self.exchanges_tab, "Exchanges")

        self.description_tab = DescriptionTab(activity, self)
        self.tabs.addTab(self.description_tab, "Description")

        self.graph_explorer = GraphTab(activity, self)
        self.tabs.addTab(self.graph_explorer, "Graph")

        self.parameters_tab = ParametersTab(activity, self)
        self.tabs.addTab(self.parameters_tab, "Parameters")

        self.consumer_tab = ConsumersTab(activity, self)
        self.tabs.addTab(self.consumer_tab, "Consumers")

        self.explorer = QtWidgets.QLabel("WORK IN PROGRESS")
        self.tabs.addTab(self.explorer, "Data")

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

        self.view = ConsumersView(self)
        self.model = ConsumersModel(self)
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

        self.model.setDataFrame(self.build_df(exchanges))

    def build_df(self, exchanges):
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "output"])
        input_df = AB_metadata.get_metadata(exc_df["input"].unique(), ["name", "type", "unit", "key"])
        output_df = AB_metadata.get_metadata(exc_df["output"].unique(), ["name", "type", "key"])

        df = exc_df.merge(
            input_df.rename({"name": "producer", "type": "_producer_type"}, axis="columns"),
            left_on="input",
            right_on="key",
        ).drop(columns=["key"])

        df = df.merge(
            output_df.rename({"name": "consumer", "type": "_consumer_type"}, axis="columns"),
            left_on="output",
            right_on="key",
        ).drop(columns=["key"])

        df = df.rename({"input": "_producer_key", "output": "_consumer_key"}, axis="columns")

        cols = ["amount", "unit", "producer", "consumer"]
        cols += [col for col in df.columns if col.startswith("_")]

        return df[cols]
