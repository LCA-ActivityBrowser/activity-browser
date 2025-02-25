from qtpy import QtWidgets, QtCore

import pandas as pd
import peewee as pw

import bw2data as bd
from bw2data.parameters import ActivityParameter, DatabaseParameter, ProjectParameter, Group

from activity_browser import signals
from activity_browser.ui import widgets as abwidgets
from activity_browser.ui.tables import delegates
from activity_browser.bwutils import refresh_node, parameters_in_node_scope


class ParametersTab(QtWidgets.QWidget):
    def __init__(self, activity, parent=None):
        super().__init__(parent)
        self.activity = refresh_node(activity)

        self.model = ParametersModel(self, self.build_df())
        self.model.group(1)
        self.view = ParametersView()
        self.view.setModel(self.model)

        self.build_layout()
        self.connect_signals()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)

        self.setLayout(layout)

    def connect_signals(self):
        signals.parameter.recalculated.connect(self.sync)

    def sync(self):
        self.activity = refresh_node(self.activity)
        self.model.setDataFrame(self.build_df())

    def build_df(self) -> pd.DataFrame:
        data = parameters_in_node_scope(self.activity)

        for param in data.values():
            if param["type"] == "project":
                param["scope"] = f"Current project"
            elif param["type"] == "database":
                param["scope"] = f"Database: {self.activity['database']}"
            elif param["group"] == f"{self.activity.id}":
                param["scope"] = "This activity"
            else:
                param["scope"] = f"Group: {param['group']}"

        columns = ["name", "scope", "amount", "formula", "uncertainty type"]
        df = pd.DataFrame.from_dict(data, orient="index", columns=columns).reset_index(drop=True)
        df.rename({"uncertainty type": "uncertainty"}, axis=1, inplace=True)

        return df


class ParametersView(abwidgets.ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "name": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }


class ParametersItem(abwidgets.ABDataItem):
    def flags(self, col: int, key: str):
        flags = super().flags(col, key)
        if key in ["amount", "formula", "uncertainty"]:
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags


class ParametersModel(abwidgets.ABAbstractItemModel):
    dataItemClass = ParametersItem

