from qtpy import QtWidgets, QtCore

import pandas as pd
import peewee as pw

import bw2data as bd
from bw2data.parameters import ActivityParameter, DatabaseParameter, ProjectParameter, Group

from activity_browser import signals, actions
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

        translated = []

        for name, param in data.items():
            row = param._asdict()
            row["uncertainty"] = param.data.get("uncertainty type")
            row["formula"] = param.data.get("formula")

            if param.param_type == "project":
                row["scope"] = f"Current project"
            elif param.param_type == "database":
                row["scope"] = f"Database: {self.activity['database']}"
            elif param.group == f"{self.activity.id}":
                row["scope"] = "This activity"
            else:
                row["scope"] = f"Group: {param.group}"

            translated.append(row)

        columns = ["name", "scope", "amount", "formula", "uncertainty"]
        return pd.DataFrame(translated, columns=columns)


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

    def setData(self, col: int, key: str, value) -> bool:
        if key in ["amount", "formula"]:
            if key == "formula" and not str(value).strip():
                actions.ExchangeFormulaRemove.run([self.exchange])
                return True

            actions.ExchangeModify.run(self.exchange, {key.lower(): value})
            return True

        if key in ["unit", "name", "location", "substitution_factor", "allocation_factor"]:
            act = self.exchange.input
            actions.ActivityModify.run(act.key, key.lower(), value)

        if key.startswith("property_"):
            act = self.exchange.input
            prop_key = key[9:]
            props = act["properties"]
            props[prop_key].update({"amount": value})

            actions.ActivityModify.run(act.key, "properties", props)

        return False


class ParametersModel(abwidgets.ABAbstractItemModel):
    dataItemClass = ParametersItem

