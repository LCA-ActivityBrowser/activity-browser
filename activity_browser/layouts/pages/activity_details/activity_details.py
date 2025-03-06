from logging import getLogger

from qtpy import QtCore, QtWidgets

import bw2data as bd

from activity_browser import signals, bwutils
from activity_browser.ui import widgets

from .activity_header import ActivityHeader
from .exchanges_tab import ExchangesTab
from .description_tab import DescriptionTab
from .graph_tab import GraphTab
from .parameters_tab import ParametersTab
from .data_tab import DataTab
from .consumers_tab import ConsumersTab

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

        self.data_tab = DataTab(activity, self)
        self.tabs.addTab(self.data_tab, "Data")

        self.build_layout()
        self.sync()
        self.connect_signals()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # layout.addWidget(toolbar)
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(widgets.ABHLine(self))
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
        self.activity = bwutils.refresh_node_or_none(self.activity)

        if self.activity is None:
            # activity was already deleted
            return

        # update the object name to be the activity name
        self.setObjectName(self.activity["name"])

        self.activity_data_grid.sync()
        self.exchanges_tab.sync()
        self.description_tab.sync()
        self.consumer_tab.sync()
        self.data_tab.sync()


