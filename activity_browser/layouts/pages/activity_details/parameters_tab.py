from qtpy import QtWidgets, QtCore, QtGui

import pandas as pd
import bw2data as bd

from activity_browser import signals, actions
from activity_browser.ui import widgets, icons, delegates
from activity_browser.bwutils import refresh_node, refresh_parameter, parameters_in_scope, Parameter, database_is_locked
from activity_browser.bwutils import node_group


class ParametersTab(QtWidgets.QWidget):
    """
    A widget that displays parameters related to a specific activity.

    Attributes:
        activity (tuple | int | bd.Node): The activity to display parameters for.
        model (ParametersModel): The model containing the data for the parameters.
        view (ParametersView): The view displaying the parameters.
    """
    def __init__(self, activity, parent=None):
        """
        Initializes the ParametersTab widget.

        Args:
            activity (tuple | int | bd.Node): The activity to display parameters for.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.activity = refresh_node(activity)

        self.model = ParametersModel(self.build_df(), self.activity, self)
        self.view = ParametersView()
        self.view.setModel(self.model)
        self.view.expandAll()

        self.view.resizeColumnToContents(0)
        self.view.resizeColumnToContents(2)

        self.build_layout()
        self.connect_signals()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)

        self.setLayout(layout)

    def connect_signals(self):
        """
        Connects signals to their respective slots.
        """
        signals.parameter.changed.connect(self.sync)
        signals.parameter.recalculated.connect(self.sync)
        signals.parameter.deleted.connect(self.sync)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.activity = refresh_node(self.activity)
        self.model.setDataFrame(self.build_df())

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the parameters in scope of the activity.

        Returns:
            pd.DataFrame: The DataFrame containing the parameters data.
        """
        data = parameters_in_scope(self.activity)

        translated = []

        for name, param in data.items():
            row = param._asdict()
            row["uncertainty"] = param.data.get("uncertainty type")
            row["formula"] = param.data.get("formula")
            row["comment"] = param.data.get("comment")
            row["_parameter"] = param
            row["_activity"] = self.activity

            if param.param_type == "project":
                row["_scope"] = f"Current project"
            elif param.param_type == "database":
                row["_scope"] = f"This database"
            elif param.group == node_group(self.activity):
                row["_scope"] = "This activity"
            else:
                row["_scope"] = f"Group: {param.group}"

            translated.append(row)

        columns = ["name", "amount", "formula", "uncertainty", "comment", "_parameter", "_scope", "_activity"]
        return pd.DataFrame(translated, columns=columns)


class ParametersView(widgets.ABTreeView):
    """
    A view that displays the parameters in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "name": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }

    class ContextMenu(QtWidgets.QMenu):
        """
        A context menu for the ParametersView.

        Attributes:
            del_param_action (QAction): The action to delete a parameter.
        """
        def __init__(self, pos, view: "ParametersView"):
            """
            Initializes the ContextMenu.

            Args:
                pos: The position of the context menu.
                view (ParametersView): The view displaying the parameters.
            """
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
    """
    An item representing a parameter in the tree view.
    """

    @property
    def scoped_parameters(self) -> dict[str, Parameter]:
        """
        Returns the parameters in scope of this item's parameter.

        Returns:
            dict: The parameters in scope.
        """
        return parameters_in_scope(parameter=self["_parameter"])

    @property
    def parameter(self) -> Parameter:
        """
        Returns the parameter associated with this item.

        Returns:
            Parameter: The current parameter.
        """
        return refresh_parameter(self["_parameter"])

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

        if key in ["amount", "formula", "uncertainty", "name", "comment"] and not database_is_locked(self["_activity"]["database"]):
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

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
        if key in ["amount", "formula", "name", "comment"]:
            actions.ParameterModify.run(self.parameter, key, value)

        return False

    def decorationData(self, col, key):
        """
        Provides decoration data for the item.

        Args:
            col: The column index.
            key: The key for which to provide decoration data.

        Returns:
            The decoration data for the item.
        """
        if key not in ["amount"]:
            return

        if key == "amount":
            if pd.isna(self["formula"]) or self["formula"] is None or self["formula"] == "":
                return icons.qicons.empty  # empty icon to align the values
            return icons.qicons.parameterized


class NewParametersItem(widgets.ABDataItem):
    """
    An item representing a new parameter in the tree view.
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
        if key == "name":
            return flags | QtCore.Qt.ItemFlag.ItemIsEditable
        return flags

    def fontData(self, col: int, key: str):
        """
        Returns the font data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the font data.

        Returns:
            QtGui.QFont: The font data.
        """
        font = super().fontData(col, key)
        font.setWeight(font.Weight.ExtraLight)
        return font

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
        if key != "name" or value == "":
            return False

        parameter = Parameter(
            name=value,
            group=self["_parameter"]["group"],
            param_type=self["_parameter"]["param_type"]
        )

        actions.ParameterNewFromParameter.run(parameter)
        return True


class ParametersModel(widgets.ABItemModel):
    """
    A model representing the data for the parameters.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = ParametersItem

    def __init__(self, dataframe, activity, parent=None):
        """
        Initializes the ParametersModel.

        Args:
            dataframe (pd.DataFrame): The DataFrame containing the parameters data.
            activity (tuple | int | bd.Node): The activity to display parameters for.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        self.activity = activity
        super().__init__(parent, dataframe)

    def createItems(self, dataframe=None) -> list[widgets.ABAbstractItem]:
        """
        Creates items from the given DataFrame.

        Args:
            dataframe (pd.DataFrame, optional): The DataFrame containing the parameters data. Defaults to None.

        Returns:
            list[widgets.ABAbstractItem]: The list of created items.
        """
        if dataframe is None:
            # If no DataFrame is provided, use the model's default DataFrame.
            dataframe = self.dataframe

        items = []
        for scope in ["Current project", "This database", "This activity"]:
            # Create a branch item for the current scope.
            branch = self.branchItemClass(scope)

            # Iterate over the rows in the DataFrame that match the current scope.
            for index, data in dataframe.loc[dataframe._scope == scope].to_dict(orient="index").items():
                # Create a data item for each row and add it to the branch.
                self.dataItemClass(index, data, branch)

            # Determine the group and parameter type based on the current scope.
            if scope == "Current project":
                group, param_type = "project", "project"
            elif scope == "This database":
                group, param_type = self.activity["database"], "database"
            else:
                group, param_type = self.activity.id, "activity"

            # If the database is not read-only, add a placeholder for creating a new parameter.
            if not bd.databases[self.activity["database"]].get("read_only", True):
                NewParametersItem(None, {"name": "New parameter...", "_parameter": {
                    "group": group, "param_type": param_type
                }}, branch)

            # Add the branch to the list of items.
            items.append(branch)

        # Return the list of created items.
        return items
