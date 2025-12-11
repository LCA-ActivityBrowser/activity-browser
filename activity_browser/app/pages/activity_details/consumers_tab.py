from qtpy import QtWidgets
from loguru import logger

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import app
from activity_browser.bwutils.commontasks import refresh_node
from activity_browser.ui import widgets, icons, core


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

        self.activity = refresh_node(activity)

        self.view = ConsumersView(self)
        self.model = ConsumersModel(parent=self, enable_sorting=True)
        self.view.setModel(self.model)
        self.view.setSortingEnabled(True)

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
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

        self.activity = refresh_node(self.activity)
        exchanges = []
        if isinstance(self.activity, bf.Process):
            for product in self.activity.products():
                exchanges += list(product.upstream())
        else:
            exchanges = list(self.activity.upstream())

        df = self.build_df(exchanges)
        df.reset_index(drop=True, inplace=True)
        self.model.set_dataframe(df)

    def build_df(self, exchanges: list[bd.Edge]) -> pd.DataFrame:
        """
        Builds a DataFrame from the given exchanges.

        Args:
            exchanges (list): The list of exchanges to build the DataFrame from.

        Returns:
            pd.DataFrame: The DataFrame containing the exchanges data.
        """
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "output"])
        input_df = app.metadata.get_metadata(exc_df["input"].unique(), ["name", "type", "unit", "key"])
        output_df = app.metadata.get_metadata(exc_df["output"].unique(), ["name", "type", "key"])

        df = exc_df.merge(
            input_df.rename({"name": "product", "type": "_product_type"}, axis="columns"),
            left_on="input",
            right_on="key",
        ).drop(columns=["key"])

        df = df.merge(
            output_df.rename({"name": "consumer", "type": "_consumer_type"}, axis="columns"),
            left_on="output",
            right_on="key",
        ).drop(columns=["key"])

        df = df.rename({"input": "_product_key", "output": "_consumer_key"}, axis="columns")

        cols = ["amount", "unit", "product", "consumer"]
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
        indexes = self.selectedIndexes()
        if not indexes:
            return super().mouseDoubleClickEvent(event)
        
        keys = self.model().values_from_indices("_consumer_key", indexes)
        if keys:
            app.actions.ActivityOpen.run(keys)


class ConsumersModel(core.ABTreeModel):
    """
    A model representing the data for the consumers.
    """
    
    def decorationData(self, index):
        """
        Provides decoration data for the model.

        Args:
            index: The index for which to provide decoration data.

        Returns:
            The decoration data for the model.
        """
        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return None

        if column_name not in ["product", "consumer"]:
            return None

        if column_name == "product":
            activity_type = row.get("_product_type")
        else:  # column_name == "consumer"
            activity_type = row.get("_consumer_type")

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

        return None
