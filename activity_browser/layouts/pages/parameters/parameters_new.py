from qtpy import QtWidgets, QtCore

import pandas as pd
import bw2data as bd
from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter, ParameterizedExchange
from bw2data.backends import ExchangeDataset

from activity_browser import signals, actions
from activity_browser.ui import widgets, icons, delegates
from activity_browser.bwutils import refresh_parameter, refresh_node, Parameter, database_is_locked, AB_metadata


class ParametersPage(QtWidgets.QWidget):
    """
    A widget that displays all parameters in the current project.

    This page shows a tree view of parameters organized by scope:
    - Project parameters
    - Database parameters (grouped by database)
    - Activity parameters (grouped by activity group)

    Attributes:
        model (ProjectParametersModel): The model containing the data for the parameters.
        view (ProjectParametersView): The view displaying the parameters.
    """

    def __init__(self, parent=None):
        """
        Initializes the ParametersPage widget.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        # Parameters tree view
        self.model = ProjectParametersModel(self.build_df(), self)
        self.view = ProjectParametersView()
        self.view.setModel(self.model)

        # Parameterized exchanges table view
        self.exchanges_model = ParameterizedExchangesModel(self.build_exchanges_df(), self)
        self.exchanges_view = ParameterizedExchangesView()
        self.exchanges_view.setModel(self.exchanges_model)

        self.build_layout()
        self.connect_signals()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()

        # Header with title for parameters
        header_layout = QtWidgets.QHBoxLayout()
        header_label = widgets.ABLabel.demiBold("Parameters")
        header_layout.addWidget(header_label)
        header_layout.addStretch(1)

        layout.addLayout(header_layout)
        layout.addWidget(widgets.ABHLine(self))

        # Add both views in a splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
        
        # Parameters tree
        params_widget = QtWidgets.QWidget()
        params_layout = QtWidgets.QVBoxLayout(params_widget)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.addWidget(self.view)
        splitter.addWidget(params_widget)

        # Parameterized exchanges
        exchanges_widget = QtWidgets.QWidget()
        exchanges_layout = QtWidgets.QVBoxLayout(exchanges_widget)
        exchanges_layout.setContentsMargins(0, 0, 0, 0)
        exchanges_label = widgets.ABLabel.demiBold("Parameterized Exchanges")
        exchanges_layout.addWidget(exchanges_label)
        exchanges_layout.addWidget(self.exchanges_view)
        splitter.addWidget(exchanges_widget)

        layout.addWidget(splitter)
        self.setLayout(layout)

    def connect_signals(self):
        """
        Connects signals to their respective slots.
        """
        AB_metadata.synced.connect(self.sync)
        signals.parameter.changed.connect(self.sync)
        signals.parameter.recalculated.connect(self.sync)
        signals.parameter.deleted.connect(self.sync)
        signals.project.changed.connect(self.sync)
        signals.meta.databases_changed.connect(self.sync)

    def sync(self):
        """
        Synchronizes the widget with the current state of parameters.
        """
        self.model.setDataFrame(self.build_df())
        self.exchanges_model.setDataFrame(self.build_exchanges_df())

        self.view.expandAll()
    
        self.view.resizeColumnToContents(0)
        self.view.resizeColumnToContents(2)
        self.view.resizeColumnToContents(3)

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from all parameters in the project.

        Returns:
            pd.DataFrame: The DataFrame containing the parameters data.
        """
        translated = []

        # Project parameters
        for param in ProjectParameter.select():
            row = self._parameter_to_row(param, "Current project", None)
            translated.append(row)

        # Database parameters
        for param in DatabaseParameter.select():
            row = self._parameter_to_row(param, f"Database: {param.database}", param.database)
            translated.append(row)

        # Activity parameters
        for param in ActivityParameter.select():
            row = self._parameter_to_row(param, f"Group: {param.group}", param.database)
            translated.append(row)

        columns = ["name", "amount", "formula", "uncertainty", "comment", "_parameter", "_scope", "_database", "_group"]
        return pd.DataFrame(translated, columns=columns)

    def _parameter_to_row(self, param, scope_label: str, database: str = None) -> dict:
        """
        Converts a parameter to a row dictionary.

        Args:
            param: The parameter to convert (ProjectParameter, DatabaseParameter, or ActivityParameter).
            scope_label: The label for the scope (e.g., "Current project", "Database: ecoinvent").
            database: The database name (None for project parameters).

        Returns:
            dict: A dictionary representing the parameter row.
        """
        data = param.dict

        # Create Parameter wrapper
        if isinstance(param, ProjectParameter):
            parameter = Parameter(param.name, "project", data.get("amount"), data, "project")
            group = "project"
        elif isinstance(param, DatabaseParameter):
            parameter = Parameter(param.name, param.database, data.get("amount"), data, "database")
            group = param.database
        elif isinstance(param, ActivityParameter):
            parameter = Parameter(param.name, param.group, data.get("amount"), data, "activity")
            group = param.group
        else:
            raise ValueError(f"Unknown parameter type: {type(param)}")

        row = {
            "name": param.name,
            "amount": data.get("amount"),
            "uncertainty": data.get("uncertainty type"),
            "formula": data.get("formula"),
            "comment": data.get("comment"),
            "_parameter": parameter,
            "_scope": scope_label,
            "_database": database,
            "_group": group,
        }

        return row

    def build_exchanges_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from all parameterized exchanges in the project.

        Returns:
            pd.DataFrame: The DataFrame containing the parameterized exchanges data.
        """
        translated = []

        # Get all parameterized exchanges
        for param_exc in ParameterizedExchange.select():
            try:
                exchange = bd.Edge(document=ExchangeDataset.get_by_id(param_exc.exchange))

                # Get keys for input and output
                input_key = exchange.get("input")
                output_key = exchange.get("output")
                
                # Get metadata from metadata store
                input_meta = AB_metadata.get_metadata([input_key], ["name", "unit", "location", "database", "product"]).iloc[0]
                output_meta = AB_metadata.get_metadata([output_key], ["name"]).iloc[0]
                
                row = {
                    "amount": exchange.get("amount"),
                    "unit": input_meta.get("unit"),
                    "from": input_meta.get("product") or input_meta.get("name"),
                    "to": output_meta.get("name"),
                    "database": input_meta.get("database"),
                    "formula": exchange.get("formula"),
                    "comment": exchange.get("comment"),
                    "uncertainty": exchange.get("uncertainty type"),
                    "_exchange": exchange,
                    "_output_key": output_key,
                    "_input_key": input_key,
                }
                translated.append(row)
            except Exception as e:
                # Skip if exchange can't be loaded
                continue

        columns = ["amount", "unit", "from", "to", "database", "formula", "comment", "uncertainty", "_exchange", "_output_key", "_input_key"]
        return pd.DataFrame(translated, columns=columns)


class ProjectParametersView(widgets.ABTreeView):
    """
    A view that displays the project parameters in a tree structure.

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
        A context menu for the ProjectParametersView.

        Attributes:
            del_param_action (QAction): The action to delete a parameter.
        """

        def __init__(self, pos, view: "ProjectParametersView"):
            """
            Initializes the ContextMenu.

            Args:
                pos: The position of the context menu.
                view (ProjectParametersView): The view displaying the parameters.
            """
            super().__init__(view)

            index = view.indexAt(pos)
            if index.isValid() and isinstance(index.internalPointer(), ProjectParametersItem):
                item = index.internalPointer()
                param = item.parameter.to_peewee_model()
                self.del_param_action = actions.ParameterDelete().get_QAction(param)
                if not param.is_deletable() or param.name == "dummy_parameter":
                    self.del_param_action.setEnabled(False)
                self.addAction(self.del_param_action)


class ProjectParametersItem(widgets.ABDataItem):
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
        from activity_browser.bwutils import parameters_in_scope
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

        # Allow editing for all parameters except those in locked databases
        database = self["_database"]
        if database and database_is_locked(database):
            return flags

        if key in ["amount", "formula", "uncertainty", "name", "comment"]:
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


class NewProjectParametersItem(widgets.ABDataItem):
    """
    An item representing a new parameter placeholder in the tree view.
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
            group=self["_group"],
            param_type=self["_param_type"]
        )

        actions.ParameterNewFromParameter.run(parameter)
        return True


class ProjectParametersModel(widgets.ABItemModel):
    """
    A model representing the data for all project parameters.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = ProjectParametersItem

    def __init__(self, dataframe, parent=None):
        """
        Initializes the ProjectParametersModel.

        Args:
            dataframe (pd.DataFrame): The DataFrame containing the parameters data.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent, dataframe)

    def createItems(self, dataframe=None) -> list[widgets.ABAbstractItem]:
        """
        Creates items from the given DataFrame, organized by scope.

        Args:
            dataframe (pd.DataFrame, optional): The DataFrame containing the parameters data. Defaults to None.

        Returns:
            list[widgets.ABAbstractItem]: The list of created items.
        """
        if dataframe is None:
            dataframe = self.dataframe

        items = []

        # Project parameters
        project_branch = self.branchItemClass("Current project")
        project_params = dataframe[dataframe._scope == "Current project"]
        for index, data in project_params.to_dict(orient="index").items():
            self.dataItemClass(index, data, project_branch)

        # Add "New parameter..." placeholder for project
        NewProjectParametersItem(None, {
            "name": "New parameter...",
            "_group": "project",
            "_param_type": "project"
        }, project_branch)

        items.append(project_branch)

        # Database parameters - grouped by database
        # Get all databases, not just those with parameters
        all_databases = set(bd.databases.list)
        database_params = dataframe[dataframe._scope.str.startswith("Database: ", na=False)]
        databases_with_params = set(database_params._database.unique() if len(database_params) > 0 else [])
        
        # Combine databases with and without parameters
        all_databases_sorted = sorted(all_databases)

        for db_name in all_databases_sorted:
            db_branch = self.branchItemClass(f"Database: {db_name}")
            
            # Add existing parameters for this database
            if db_name in databases_with_params:
                db_data = database_params[database_params._database == db_name]
                for index, data in db_data.to_dict(orient="index").items():
                    self.dataItemClass(index, data, db_branch)

            # Add "New parameter..." placeholder if database is not read-only
            if not bd.databases[db_name].get("read_only", True):
                NewProjectParametersItem(None, {
                    "name": "New parameter...",
                    "_group": db_name,
                    "_param_type": "database"
                }, db_branch)

            items.append(db_branch)

        # Activity parameters - grouped by group
        activity_params = dataframe[dataframe._scope.str.startswith("Group: ", na=False)]
        groups = activity_params._group.unique() if len(activity_params) > 0 else []

        for group_name in sorted(groups):
            group_branch = self.branchItemClass(f"Group: {group_name}")
            group_data = activity_params[activity_params._group == group_name]

            for index, data in group_data.to_dict(orient="index").items():
                self.dataItemClass(index, data, group_branch)

            # Add "New parameter..." placeholder if database is not read-only
            db_name = group_data.iloc[0]._database if len(group_data) > 0 else None
            if db_name and db_name in bd.databases and not bd.databases[db_name].get("read_only", True):
                NewProjectParametersItem(None, {
                    "name": "New parameter...",
                    "_group": group_name,
                    "_param_type": "activity"
                }, group_branch)

            items.append(group_branch)

        return items


class ParameterizedExchangesView(widgets.ABTreeView):
    """
    A view that displays parameterized exchanges in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "unit": delegates.StringDelegate,
        "product": delegates.StringDelegate,
        "producer": delegates.StringDelegate,
        "location": delegates.StringDelegate,
        "database": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }

    class ContextMenu(QtWidgets.QMenu):
        """
        A context menu for the ParameterizedExchangesView.
        """
        def __init__(self, pos, view: "ParameterizedExchangesView"):
            """
            Initializes the ContextMenu.

            Args:
                pos: The position of the context menu.
                view (ParameterizedExchangesView): The view displaying the exchanges.
            """
            super().__init__(view)

            index = view.indexAt(pos)
            if index.isValid() and isinstance(index.internalPointer(), ParameterizedExchangesItem):
                item = index.internalPointer()
                
                # Open activity action
                open_action = actions.ActivityOpen.get_QAction([item["_output_key"]])
                open_action.setText("Open activity")
                self.addAction(open_action)


class ParameterizedExchangesItem(widgets.ABDataItem):
    """
    An item representing a parameterized exchange in the tree view.
    """

    @property
    def exchange(self):
        """
        Returns the exchange associated with this item.

        Returns:
            The exchange associated with the item.
        """
        return self["_exchange"]

    @property
    def scoped_parameters(self) -> dict[str, Parameter]:
        """
        Returns the parameters in scope of this exchange.

        Returns:
            dict: The parameters in scope.
        """
        from activity_browser.bwutils import parameters_in_scope
        return parameters_in_scope(node=self["_exchange"].output)

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

        # Check if database is locked
        if database_is_locked(self.exchange.output["database"]):
            return flags

        # Allow editing for specific keys
        if key in ["amount", "formula", "comment"]:
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
        if key in ["amount", "formula", "comment"]:
            if key == "formula" and not str(value).strip():
                actions.ExchangeFormulaRemove.run([self.exchange])
                return True

            actions.ExchangeModify.run(self.exchange, {key.lower(): value})
            return True

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


class ParameterizedExchangesModel(widgets.ABItemModel):
    """
    A model representing the data for parameterized exchanges.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = ParameterizedExchangesItem

    def __init__(self, dataframe, parent=None):
        """
        Initializes the ParameterizedExchangesModel.

        Args:
            dataframe (pd.DataFrame): The DataFrame containing the exchanges data.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent, dataframe)
