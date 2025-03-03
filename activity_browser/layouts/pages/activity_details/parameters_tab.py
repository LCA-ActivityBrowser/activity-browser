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

        self.model = ParametersModel(self.build_df(), self.activity, self)
        self.view = ParametersView()
        self.view.setModel(self.model)
        self.view.expandAll()

        self.view.resizeColumnToContents(0)
        # self.view.hideColumn(1)
        self.view.resizeColumnToContents(3)

        self.build_layout()
        self.connect_signals()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)

        self.setLayout(layout)

    def connect_signals(self):
        signals.parameter.recalculated.connect(self.sync)
        signals.parameter.deleted.connect(self.sync)

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
                row["_scope"] = f"Current project"
            elif param.param_type == "database":
                row["_scope"] = f"This database"
            elif param.group == f"{self.activity.id}":
                row["_scope"] = "This activity"
            else:
                row["_scope"] = f"Group: {param.group}"

            translated.append(row)

        columns = ["name", "amount", "formula", "uncertainty", "_parameter", "_scope"]
        return pd.DataFrame(translated, columns=columns)


class ParametersView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "name": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view: "ParametersView"):
            super().__init__(view)

            index = view.indexAt(pos)
            if index.isValid() and isinstance(index.internalPointer(), ParametersItem):
                item = index.internalPointer()
                param = item.parameter.to_peewee_model()
                self.del_param_action = actions.ParameterDelete().get_QAction(param)
                if not param.is_deletable() or param.name == "dummy_parameter":
                    self.del_param_action.setEnabled(False)
                self.addAction(self.del_param_action)


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

    def displayData(self, col: int, key: str):
        return super().displayData(col, key)

    def decorationData(self, col, key):
        if key not in ["amount"] or not self.displayData(col, key):
            return

        if key == "amount":
            if pd.isna(self["formula"]) or self["formula"] is None or self["formula"] == "":
                return icons.qicons.empty  # empty icon to align the values
            return icons.qicons.parameterized


class NewParametersItem(widgets.ABDataItem):
    def flags(self, col: int, key: str):
        flags = super().flags(col, key)
        if key == "name":
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def fontData(self, col: int, key: str):
        font = super().fontData(col, key)
        font.setItalic(True)
        return font

    def setData(self, col: int, key: str, value) -> bool:
        if key != "name" or value == "":
            return False

        parameter = Parameter(
            name=value,
            group=self["_parameter"]["group"],
            param_type=self["_parameter"]["param_type"]
        )

        actions.ParameterNewFromParameter.run(parameter)
        return True


class ParametersModel(widgets.ABAbstractItemModel):
    dataItemClass = ParametersItem

    def __init__(self, dataframe, activity, parent=None):
        self.activity = activity
        super().__init__(parent, dataframe)

    def createItems(self, dataframe=None) -> list[widgets.ABAbstractItem]:
        if dataframe is None:
            dataframe = self.dataframe

        items = []
        for scope in ["Current project", "This database", "This activity"]:
            branch = self.branchItemClass(scope)

            for index, data in dataframe.loc[dataframe._scope == scope].to_dict(orient="index").items():
                self.dataItemClass(index, data, branch)

            if scope == "Current project":
                group, param_type = "project", "project"
            elif scope == "This database":
                group, param_type = self.activity["database"], "database"
            else:
                group, param_type = self.activity.id, "activity"

            NewParametersItem(None, {"name": "New parameter", "_parameter": {
                "group": group, "param_type": param_type
            }}, branch)

            items.append(branch)

        return items

