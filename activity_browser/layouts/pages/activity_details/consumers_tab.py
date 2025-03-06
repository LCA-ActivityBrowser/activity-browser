from qtpy import QtWidgets

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import actions, bwutils
from activity_browser.ui import widgets, icons


class ConsumersTab(QtWidgets.QWidget):
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        super().__init__(parent)

        self.activity = bwutils.refresh_node(activity)

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
        self.activity = bwutils.refresh_node(self.activity)
        exchanges = []
        if isinstance(self.activity, bf.Process):
            for function in self.activity.functions():
                exchanges += list(function.upstream())
        else:
            exchanges = list(self.activity.upstream())

        self.model.setDataFrame(self.build_df(exchanges))

    def build_df(self, exchanges):
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "output"])
        input_df = bwutils.AB_metadata.get_metadata(exc_df["input"].unique(), ["name", "type", "unit", "key"])
        output_df = bwutils.AB_metadata.get_metadata(exc_df["output"].unique(), ["name", "type", "key"])

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


class ConsumersView(widgets.ABTreeView):
    def mouseDoubleClickEvent(self, event) -> None:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ConsumersItem)]
        keys = list({i["_consumer_key"] for i in items})
        if keys:
            actions.ActivityOpen.run(keys)


class ConsumersItem(widgets.ABDataItem):
    def decorationData(self, col, key):
        if key not in ["producer", "consumer"]:
            return

        if key == "producer":
            activity_type = self["_producer_type"]
        else:  # key is "consumer"
            activity_type = self["_consumer_type"]

        if activity_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        if activity_type == "processwithreferenceproduct":
            return icons.qicons.processproduct
        if activity_type == "product":
            return icons.qicons.product
        if activity_type in ["process", "multifunctional", "nonfunctional"]:
            return icons.qicons.process
        if activity_type == "waste":
            return icons.qicons.waste


class ConsumersModel(widgets.ABAbstractItemModel):
    dataItemClass = ConsumersItem




