from qtpy import QtWidgets, QtCore

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import actions
from activity_browser.bwutils import refresh_node, AB_metadata
from activity_browser.ui import widgets
from activity_browser.ui.tables import delegates


class DataTab(QtWidgets.QWidget):
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        super().__init__(parent)

        self.activity = refresh_node(activity)

        # Data TreeView
        self.data_view = DataView(self)
        self.data_model = DataModel(self)
        self.data_view.setModel(self.data_model)

        self.data_model.setDataFrame(self.build_df())
        self.data_model.group(2)
        self.data_view.setColumnHidden(2, True)

        self.build_layout()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.data_view)
        self.setLayout(layout)

    def sync(self) -> None:
        """Populate the various tables and boxes within the Activity Detail tab"""
        self.activity = refresh_node(self.activity)
        self.data_model.setDataFrame(self.build_df())

    def build_df(self) -> pd.DataFrame:
        df = pd.DataFrame.from_dict(self.activity.as_dict(), orient="index")
        df["name"] = self.activity["name"]
        df["_activity_id"] = self.activity.id

        if isinstance(self.activity, bf.Process):
            for function in self.activity.functions():
                fn_df = pd.DataFrame.from_dict(function.as_dict(), orient="index")
                fn_df["name"] = function["name"]
                fn_df["_activity_id"] = function.id
                df = pd.concat([df, fn_df])

        df = df.reset_index()
        df = df.rename({"index": "field", 0: "value"}, axis=1)
        df = df.sort_values(["name", "field"], ignore_index=True)

        cols = ["field", "value", "name", "_activity_id"]
        return df[cols]


class DataView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "key": delegates.StringDelegate,
        "value": delegates.NewFormulaDelegate,
    }


class DataItem(widgets.ABDataItem):

    def flags(self, col: int, key: str):
        flags = super().flags(col, key)
        if key == "value":
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def displayData(self, col: int, key: str):
        if key == "value":
            data = self[key]
            if isinstance(data, str):
                return f"'{data}'"
            return str(data)

        return super().displayData(col, key)

    def setData(self, col: int, key: str, value) -> bool:
        if key in ["value"]:
            value = eval(value)
            actions.ActivityModify.run(self["_activity_id"], self["field"], value)

        return False


class DataModel(widgets.ABAbstractItemModel):
    dataItemClass = DataItem

