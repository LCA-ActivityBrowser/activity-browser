from qtpy import QtWidgets, QtCore

import pandas as pd

from activity_browser import signals, actions
from activity_browser.ui import widgets, icons
from activity_browser.ui.tables import delegates
from activity_browser.bwutils import refresh_node, refresh_parameter, parameters_in_scope, Parameter


class ParametersTab(QtWidgets.QWidget):
    def __init__(self, activity, parent=None):
        super().__init__(parent)
        self.activity = refresh_node(activity)

        self.model = ParametersModel(self, self.build_df())
        self.model.group(1)
        self.view = ParametersView()
        self.view.setModel(self.model)
        self.view.expandAll()

        self.view.resizeColumnToContents(0)
        self.view.hideColumn(1)
        self.view.resizeColumnToContents(3)

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
        data = parameters_in_scope(self.activity)

        translated = []

        for name, param in data.items():
            row = param._asdict()
            row["uncertainty"] = param.data.get("uncertainty type")
            row["formula"] = param.data.get("formula")
            row["_parameter"] = param

            if param.param_type == "project":
                row["scope"] = f"Current project"
            elif param.param_type == "database":
                row["scope"] = f"Database: {self.activity['database']}"
            elif param.group == f"{self.activity.id}":
                row["scope"] = "This activity"
            else:
                row["scope"] = f"Group: {param.group}"

            translated.append(row)

        columns = ["name", "scope", "amount", "formula", "uncertainty", "_parameter"]
        return pd.DataFrame(translated, columns=columns)


class ParametersView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "name": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }


class ParametersItem(widgets.ABDataItem):

    @property
    def scoped_parameters(self):
        return parameters_in_scope(parameter=self["_parameter"])

    @property
    def parameter(self) -> Parameter:
        return refresh_parameter(self["_parameter"])

    def flags(self, col: int, key: str):
        flags = super().flags(col, key)
        if key in ["amount", "formula", "uncertainty", "name"]:
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(self, col: int, key: str, value) -> bool:
        if key in ["amount", "formula", "name"]:
            actions.ParameterModify.run(self.parameter, key, value)

        return False

    def decorationData(self, col, key):
        if key not in ["amount"] or not self.displayData(col, key):
            return

        if key == "amount":
            if pd.isna(self["formula"]) or self["formula"] is None:
                return icons.qicons.empty  # empty icon to align the values
            return icons.qicons.parameterized


class ParametersModel(widgets.ABAbstractItemModel):
    dataItemClass = ParametersItem

