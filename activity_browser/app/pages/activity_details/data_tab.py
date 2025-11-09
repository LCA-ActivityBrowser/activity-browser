from qtpy import QtWidgets, QtCore

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import app
from activity_browser.bwutils.commontasks import refresh_node, database_is_locked
from activity_browser.ui import widgets, delegates, core


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
        self.data_model = DataModel(parent=self)
        self.data_view.setModel(self.data_model)

        df = self.build_df()
        df.reset_index(drop=True, inplace=True)
        self.data_model.set_dataframe(df)
        self.data_model.group(["_name"])
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
        df = self.build_df()
        df.reset_index(drop=True, inplace=True)
        self.data_model.set_dataframe(df)
        self.data_model.group(["_name"])
        self.data_view.expandAll()

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the activity data.

        Returns:
            pd.DataFrame: The DataFrame containing the activity data.
        """
        df = pd.Series(self.activity.as_dict()).to_frame()
        df["_name"] = f"{self.activity['name']} {df.get('product', '')} ({self.activity['id']})"
        df["_activity_id"] = self.activity.id
        df["_activity_db"] = self.activity["database"]

        if isinstance(self.activity, bf.Process):
            for product in self.activity.products():
                fn_df = pd.DataFrame.from_dict(product.as_dict(), orient="index")
                fn_df["_name"] = f"{product['name']}: {product.get('product', '')} ({product['id']})"
                fn_df["_activity_id"] = product.id
                fn_df["_activity_db"] = product["database"]
                df = pd.concat([df, fn_df])

        df = df.reset_index()
        df = df.rename({"index": "field", 0: "value"}, axis=1)
        df = df.sort_values(["_name", "field"], ignore_index=True)

        cols = ["field", "value", "_name", "_activity_id", "_activity_db"]
        return df[cols]


class DataView(widgets.ABNewTreeView):
    """
    A view that displays the data in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "field": delegates.StringDelegate,
        "value": delegates.NewFormulaDelegate,
    }


class DataModel(core.ABTreeModel):
    """
    A model representing the data for the activity.
    """
    
    def setData(self, index: QtCore.QModelIndex, value, role: int = QtCore.Qt.ItemDataRole.EditRole) -> bool:
        """
        Sets the data for the given index.

        Args:
            index (QtCore.QModelIndex): The index to set data for.
            value: The value to set.
            role (int): The role for which to set the data.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if role != QtCore.Qt.ItemDataRole.EditRole:
            return False

        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return False

        if column_name == "value":
            value = eval(value)
            app.actions.ActivityModify.run(row.get("_activity_id"), row.get("field"), value)
            return True

        return False
    
    def indexEditable(self, index: QtCore.QModelIndex) -> bool:
        """
        Returns whether the index is editable.

        Args:
            index (QtCore.QModelIndex): The index to check.

        Returns:
            bool: True if the index is editable, False otherwise.
        """
        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return False

        if column_name == "value" and not database_is_locked(row.get("_activity_db")):
            return True
        
        return False
    
    def displayData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides display data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide display data.

        Returns:
            The display data for the index.
        """
        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            # Branch node
            path = index.internalPointer()
            return path[-1] if index.column() == 0 else None

        if column_name == "value":
            data = row.get(column_name)
            if isinstance(data, str):
                return f"'{data}'"
            return str(data)

        return row.get(column_name)
