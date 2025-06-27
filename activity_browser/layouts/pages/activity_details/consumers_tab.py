from qtpy import QtWidgets

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import actions, bwutils
from activity_browser.ui import widgets, icons


class ConsumersTab(QtWidgets.QWidget):
    """
    A widget that displays consumers related to a specific activity.

    Attributes:
        activity (tuple | int | bd.Node): The activity to display consumers for.
        view (ConsumersView): The view displaying the consumers.
        model (ConsumersModel): The model containing the data for the consumers.
    """
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        """
        Initializes the ConsumersTab widget.

        Args:
            activity (tuple | int | bd.Node): The activity to display consumers for.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.activity = bwutils.refresh_node(activity)

        self.view = ConsumersView(self)
        self.model = ConsumersModel(self)
        self.view.setModel(self.model)

        self.build_layout()
        self.sync()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 1)
        layout.addWidget(self.view)
        self.setLayout(layout)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.activity = bwutils.refresh_node(self.activity)
        exchanges = []
        if isinstance(self.activity, bf.Process):
            for product in self.activity.products():
                exchanges += list(product.upstream())
        else:
            exchanges = list(self.activity.upstream())

        self.model.setDataFrame(self.build_df(exchanges))

    def build_df(self, exchanges: list[bd.Edge]) -> pd.DataFrame:
        """
        Builds a DataFrame from the given exchanges.

        Args:
            exchanges (list): The list of exchanges to build the DataFrame from.

        Returns:
            pd.DataFrame: The DataFrame containing the exchanges data.
        """
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
    """
    A view that displays the consumers in a tree structure.
    """
    def mouseDoubleClickEvent(self, event) -> None:
        """
        Handles the mouse double-click event.

        Args:
            event: The mouse event.
        """
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ConsumersItem)]
        keys = list({i["_consumer_key"] for i in items})
        if keys:
            actions.ActivityOpen.run(keys)


class ConsumersItem(widgets.ABDataItem):
    """
    An item representing a consumer in the tree view.
    """
    def decorationData(self, col, key):
        """
        Provides decoration data for the item.

        Args:
            col: The column index.
            key: The key for which to provide decoration data.

        Returns:
            The decoration data for the item.
        """
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


class ConsumersModel(widgets.ABItemModel):
    """
    A model representing the data for the consumers.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = ConsumersItem
