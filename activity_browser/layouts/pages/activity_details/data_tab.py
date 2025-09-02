from qtpy import QtWidgets, QtCore

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import actions
from activity_browser.bwutils import refresh_node, database_is_locked
from activity_browser.ui import widgets, delegates


class DataTab(QtWidgets.QWidget):
    """
    A widget that displays the data structure of a specific activity.

    Attributes:
        activity (tuple | int | bd.Node): The activity to display data for.
        data_view (DataView): The view displaying the data.
        data_model (DataModel): The model containing the data.
    """
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        """
        Initializes the DataTab widget.

        Args:
            activity (tuple | int | bd.Node): The activity to display data for.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.activity = refresh_node(activity)

        # Data TreeView
        self.data_view = DataView(self)
        self.data_model = DataModel(self)
        self.data_view.setModel(self.data_model)

        self.data_model.setDataFrame(self.build_df())
        self.data_model.group(2)
        self.data_view.setColumnHidden(2, True)
        self.data_view.expandAll()

        self.build_layout()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.data_view)
        self.setLayout(layout)

    def sync(self) -> None:
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.activity = refresh_node(self.activity)
        self.data_model.setDataFrame(self.build_df())

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the activity data.

        Returns:
            pd.DataFrame: The DataFrame containing the activity data.
        """
        df = pd.Series(self.activity.as_dict()).to_frame()
        df["name"] = self.activity["name"] + " (" + str(self.activity["id"]) + ")"
        df["_activity_id"] = self.activity.id
        df["_activity_db"] = self.activity["database"]

        if isinstance(self.activity, bf.Process):
            for product in self.activity.products():
                fn_df = pd.DataFrame.from_dict(product.as_dict(), orient="index")
                fn_df["name"] = product["name"] + " (" + str(product["id"]) + ")"
                fn_df["_activity_id"] = product.id
                fn_df["_activity_db"] = product["database"]
                df = pd.concat([df, fn_df])

        df = df.reset_index()
        df = df.rename({"index": "field", 0: "value"}, axis=1)
        df = df.sort_values(["name", "field"], ignore_index=True)

        cols = ["field", "value", "name", "_activity_id", "_activity_db"]
        return df[cols]


class DataView(widgets.ABTreeView):
    """
    A view that displays the data in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "key": delegates.StringDelegate,
        "value": delegates.NewFormulaDelegate,
    }


class DataItem(widgets.ABDataItem):
    """
    An item representing a data entry in the tree view.
    """
    def flags(self, col: int, key: str):
        """
        Returns the item flags for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the flags.

        Returns:
            QtCore.Qt.ItemFlags: The item flags.
        """
        flags = super().flags(col, key)

        if key == "value" and not database_is_locked(self["_activity_db"]):
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def displayData(self, col: int, key: str):
        """
        Returns the display data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the display data.

        Returns:
            str: The display data.
        """
        if key == "value":
            data = self[key]
            if isinstance(data, str):
                return f"'{data}'"
            return str(data)

        return super().displayData(col, key)

    def setData(self, col: int, key: str, value) -> bool:
        """
        Sets the data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to set the data.
            value: The value to set.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if key in ["value"]:
            value = eval(value)
            actions.ActivityModify.run(self["_activity_id"], self["field"], value)

        return False


class DataModel(widgets.ABItemModel):
    """
    A model representing the data for the activity.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = DataItem
