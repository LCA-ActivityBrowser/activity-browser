from logging import getLogger

import pandas as pd
import numpy as np
from peewee import DoesNotExist

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Qt

import bw2data as bd

from activity_browser import project_settings, signals
from activity_browser.bwutils import AB_metadata
from activity_browser.ui import widgets as ABwidgets

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

    def __init__(self, key: tuple, read_only=True, parent=None):
        super().__init__(parent)
        self.read_only = read_only
        self.db_read_only = project_settings.db_is_readonly(db_name=key[0])
        self.key = key
        self.db_name = key[0]
        self.activity = bd.get_activity(key)
        self.database = bd.Database(self.db_name)

        # # Toolbar Layout
        # toolbar = QtWidgets.QToolBar()
        # self.graph_action = toolbar.addAction(
        #     qicons.graph_explorer, "Show in Graph Explorer", self.open_graph
        # )

        # Activity information
        # this contains: activity name, location, database
        self.activity_data_grid = ActivityData(self)

        # Output Table
        self.output_view = ExchangeView(self)
        self.output_model = ExchangeModel(self)
        self.output_view.setModel(self.output_model)

        # Input Table
        self.input_view = ExchangeView(self)
        self.input_model = ExchangeModel(self)
        self.input_view.setModel(self.input_model)

        # Full layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        # layout.addWidget(toolbar)
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(ABwidgets.ABHLine(self))
        layout.addWidget(QtWidgets.QLabel("<b>Output:</b>"))
        layout.addWidget(self.output_view)
        layout.addWidget(QtWidgets.QLabel("<b>Input:</b>"))
        layout.addWidget(self.input_view)

        self.setLayout(layout)

        self.populate()
        self.connect_signals()

    def connect_signals(self):
        # signals.database_read_only_changed.connect(self.db_read_only_changed)

        signals.node.deleted.connect(self.on_node_deleted)
        signals.database.deleted.connect(self.on_database_deleted)

        # signals.node.changed.connect(self.populateLater)
        # signals.edge.changed.connect(self.populateLater)
        # # signals.edge.deleted.connect(self.populate)

        signals.meta.databases_changed.connect(self.populateLater)

        signals.parameter.recalculated.connect(self.populateLater)

    def on_node_deleted(self, node):
        if node.id == self.activity.id:
            self.deleteLater()

    def on_database_deleted(self, name):
        if name == self.activity["database"]:
            self.deleteLater()

    def open_graph(self) -> None:
        signals.open_activity_graph_tab.emit(self.key)

    def populateLater(self):
        def slot():
            self._populate_later_flag = False
            self.populate()

        if self._populate_later_flag:
            return

        self.thread().eventDispatcher().awake.connect(slot, Qt.ConnectionType.SingleShotConnection)
        self._populate_later_flag = True

    def populate(self) -> None:
        """Populate the various tables and boxes within the Activity Detail tab"""
        if self.db_name in bd.databases:
            # Avoid a weird signal interaction in the tests
            try:
                self.activity = bd.get_activity(self.key)  # Refresh activity.
            except DoesNotExist:
                signals.close_activity_tab.emit(self.key)
                return

        # update the object name to be the activity name
        self.setObjectName(self.activity["name"])

        # sync the activity data grid
        self.activity_data_grid.sync()

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
        if not exchanges:
            return pd.DataFrame()

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

