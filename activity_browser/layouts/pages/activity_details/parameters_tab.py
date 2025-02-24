from qtpy import QtWidgets, QtCore

import pandas as pd
import peewee as pw

import bw2data as bd
from bw2data.parameters import ActivityParameter, DatabaseParameter, ProjectParameter, Group

from activity_browser import signals
from activity_browser.ui import widgets as abwidgets
from activity_browser.ui.tables import delegates
from activity_browser.bwutils import refresh_node, AB_metadata


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
        data = self.get_project_params()
        data.update(self.get_database_params())
        data.update(self.get_activity_params())

        columns = ["name", "scope", "amount", "formula", "uncertainty type"]
        df = pd.DataFrame.from_dict(data, orient="index", columns=columns).reset_index(drop=True)
        df.rename({"uncertainty type": "uncertainty"}, axis=1, inplace=True)

        return df

    def get_activity_params(self) -> dict:
        data = {}
        try:
            group_name = ActivityParameter.get((ActivityParameter.database == self.activity["database"]) &
                                               (ActivityParameter.code == self.activity["code"])).group
            group_deps: list = Group.get(Group.name == group_name).order
            group_deps.append(group_name)

            for dep in group_deps:
                for name, param in ActivityParameter.load(dep).items():
                    key = (dep, name)
                    param["name"] = name
                    param["group"] = dep
                    param["scope"] = "This activity" if dep == group_name else f"Group: {dep}"
                    data[key] = param
        except pw.DoesNotExist:
            # no activity parameters (yet)
            pass
        return data

    def get_database_params(self) -> dict:
        data = {}
        for name, param in DatabaseParameter.load(self.activity["database"]).items():
            key = (self.activity["database"], name)
            param["name"] = name
            param["group"] = self.activity["database"]
            param["scope"] = f"Database: {self.activity['database']}"
            data[key] = param
        return data

    def get_project_params(self) -> dict:
        data = {}
        for name, param in ProjectParameter.load().items():
            key = ("project", name)
            param["name"] = name
            param["group"] = "project"
            param["scope"] = "Current project"
            data[key] = param
        return data


class ParametersView(abwidgets.ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "name": delegates.StringDelegate,
        "formula": delegates.StringDelegate,
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

