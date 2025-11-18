from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
import pandas as pd
import bw2data as bd
from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter, ParameterizedExchange
from bw2data.backends import ExchangeDataset

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import refresh_parameter, database_is_locked
from activity_browser.bwutils.utils import Parameter


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
        self.model = ProjectParametersModel(parent=self)
        self.view = ProjectParametersView()
        self.view.setModel(self.model)

        # Parameterized exchanges table view
        self.exchanges_model = ParameterizedExchangesModel(parent=self)
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
        app.signals.metadata.synced.connect(self.sync)
        app.signals.parameter.changed.connect(self.sync)
        app.signals.parameter.recalculated.connect(self.sync)
        app.signals.parameter.deleted.connect(self.sync)
        app.signals.project.changed.connect(self.sync)
        app.signals.meta.databases_changed.connect(self.sync)

    def sync(self):
        """
        Synchronizes the widget with the current state of parameters.
        """
        df = self.build_df()
        df.reset_index(drop=True, inplace=True)
        self.model.set_dataframe(df)
        self.model.group(["_param_type", "_scope"])
        self.view.expandAll()
        
        exchanges_df = self.build_exchanges_df()
        exchanges_df.reset_index(drop=True, inplace=True)
        self.exchanges_model.set_dataframe(exchanges_df)

        self.view.expandAll()
    
        self.view.resizeColumnToContents(1)
        self.view.resizeColumnToContents(3)
        self.view.resizeColumnToContents(4)

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from all parameters in the project.

        Returns:
            pd.DataFrame: The DataFrame containing the parameters data.
        """
        translated = []

        # Project parameters
        for param in ProjectParameter.select():
            row = self._parameter_to_row(param)
            translated.append(row)

        # Database parameters
        for param in DatabaseParameter.select():
            row = self._parameter_to_row(param, "{param.database}", param.database)
            translated.append(row)

        # Activity parameters
        for param in ActivityParameter.select():
            row = self._parameter_to_row(param, f"Group: {param.group}", param.database)
            translated.append(row)

        columns = ["name", "amount", "formula", "uncertainty", "comment", "_parameter", "_scope", "_database", "_group", "_param_type"]
        df = pd.DataFrame(translated, columns=columns)
        df["_is_new"] = False

        # Add "New parameter..." placeholders
        new_rows = []

        # Add for project
        new_rows.append({
            "name": "New parameter...",
            "_group": "project",
            "_param_type": "project",
            "_is_new": True,
        })

        # Add for each database
        for db_name in sorted(bd.databases.list):
            if not bd.databases[db_name].get("read_only", True):
                new_rows.append({
                    "name": "New parameter...",
                    "_scope": f"{db_name}",
                    "_database": db_name,
                    "_group": db_name,
                    "_param_type": "database",
                    "_is_new": True,
                })

        # Add for each activity group
        activity_params = df[df._scope.str.startswith("group: ", na=False)]
        groups = activity_params._group.unique() if len(activity_params) > 0 else []
        for group_name in sorted(groups):
            group_data = activity_params[activity_params._group == group_name]
            db_name = group_data.iloc[0]._database if len(group_data) > 0 else None
            if db_name and db_name in bd.databases and not bd.databases[db_name].get("read_only", True):
                new_rows.append({
                    "name": "New parameter...",
                    "_scope": f"group: {group_name}",
                    "_database": db_name,
                    "_group": group_name,
                    "_param_type": "activity",
                    "_is_new": True,
                })

        # Append new rows to dataframe
        if new_rows:
            new_df = pd.DataFrame(new_rows)
            df = pd.concat([df, new_df], ignore_index=True)

        return df.sort_values(by="_param_type", key= lambda c: c.map({"project": 0, "database": 1, "activity": 2}))

    def _parameter_to_row(self, param, scope_label: str = None, database: str = None) -> dict:
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
            param_type = "project"
        elif isinstance(param, DatabaseParameter):
            parameter = Parameter(param.name, param.database, data.get("amount"), data, "database")
            group = param.database
            param_type = "database"
        elif isinstance(param, ActivityParameter):
            parameter = Parameter(param.name, param.group, data.get("amount"), data, "activity")
            group = param.group
            param_type = "activity"
        else:
            raise ValueError(f"Unknown parameter type: {type(param)}")

        row = {
            "name": parameter.name,
            "amount": parameter.amount,
            "uncertainty": parameter.uncertainty,
            "formula": data.get("formula"),
            "comment": data.get("comment"),
            "_param_type": param_type,
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
                input_meta = app.metadata.get_metadata([input_key], ["name", "unit", "location", "database", "product"]).iloc[0]
                output_meta = app.metadata.get_metadata([output_key], ["name"]).iloc[0]
                
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

    class ContextMenu(widgets.ABMenu):
        """
        A context menu for the ProjectParametersView.
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
            if index.isValid() and not view.model().isBranchNode(index):
                row = view.model().row(index)
                if row is not None and not row.get("_is_new"):
                    parameter = row.get("_parameter")
                    if parameter:
                        param = refresh_parameter(parameter).to_peewee_model()
                        self.del_param_action = app.actions.ParameterDelete().get_QAction(param)
                        if not param.is_deletable() or param.name == "dummy_parameter":
                            self.del_param_action.setEnabled(False)
                        self.addAction(self.del_param_action)


class ProjectParametersModel(core.ABTreeModel):
    """
    A model representing the data for all project parameters.
    """

    def __init__(self, parent=None):
        """
        Initializes the ProjectParametersModel.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(df=pd.DataFrame(), parent=parent)

    def setData(self, index: QtCore.QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """
        Sets the data for the given index.

        Args:
            index (QtCore.QModelIndex): The index to set data for.
            value: The value to set.
            role (int): The role for which to set the data.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if role != Qt.ItemDataRole.EditRole:
            return False

        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return False

        # Handle "New parameter..." rows
        if row.get("_is_new"):
            if column_name != "name" or value == "":
                return False

            parameter = Parameter(
                name=value,
                group=row.get("_group"),
                param_type=row.get("_param_type")
            )

            app.actions.ParameterNewFromParameter.run(parameter)
            return True

        # Handle regular parameter edits
        parameter = row.get("_parameter")
        if parameter is None:
            return False

        if column_name in ["amount", "formula", "name", "comment"]:
            parameter = refresh_parameter(parameter)
            app.actions.ParameterModify.run(parameter, column_name, value)

        if column_name == "uncertainty":
            parameter = refresh_parameter(parameter)
            app.actions.ParameterUncertaintyModify.run(parameter.to_peewee_model(), uncertainty_dict=value)

            return True

        return False

    def decorationData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides decoration data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide decoration data.

        Returns:
            The decoration data for the index.
        """
        column_name = self.column_name(index)

        if column_name == "amount":
            return icons.qicons.empty if pd.isna(self.get(index, "formula")) else icons.qicons.parameterized

        return None

    def fontData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides font data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the index.
        """
        if self.get(index, "_is_new"):
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.ExtraLight)
            return font

        return None

    def indexEditable(self, index: QtCore.QModelIndex) -> bool:
        """
        Returns whether the index is editable.

        Args:
            index (QtCore.QModelIndex): The index to check.

        Returns:
            bool: True if the index is editable, False otherwise.
        """
        column_name = self.column_name(index)

        # Check if database is locked
        database = self.get(index, "_database")
        if not pd.isna(database) and database_is_locked(database):
            return False

        # Allow editing for specific columns
        if column_name in ["formula", "uncertainty", "name", "comment"]:
            return True
        
        if column_name == "amount" and not self.get(index, "formula"):
            return True

        return False

    def scoped_parameters(self, index: QtCore.QModelIndex) -> dict[str, Parameter]:
        """
        Returns the parameters in scope of the parameter at the given index.

        Args:
            index (QtCore.QModelIndex): The index to get scoped parameters for.

        Returns:
            dict: The parameters in scope.
        """
        from activity_browser.bwutils.commontasks import parameters_in_scope
        
        row = self.row(index)
        if row is None:
            return {}

        parameter = row.get("_parameter")
        if parameter is None:
            return {}

        return parameters_in_scope(parameter=parameter)


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

    class ContextMenu(widgets.ABMenu):
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
            if index.isValid() and not view.model().isBranchNode(index):
                row = view.model().row(index)
                if row is not None:
                    output_key = row.get("_output_key")
                    if output_key:
                        # Open activity action
                        open_action = app.actions.ActivityOpen.get_QAction([output_key])
                        open_action.setText("Open activity")
                        self.addAction(open_action)


class ParameterizedExchangesModel(core.ABTreeModel):
    """
    A model representing the data for parameterized exchanges.
    """

    def __init__(self, parent=None):
        """
        Initializes the ParameterizedExchangesModel.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(df=pd.DataFrame(), parent=parent)

    def setData(self, index: QtCore.QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """
        Sets the data for the given index.

        Args:
            index (QtCore.QModelIndex): The index to set data for.
            value: The value to set.
            role (int): The role for which to set the data.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if role != Qt.ItemDataRole.EditRole:
            return False

        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return False

        exchange = row.get("_exchange")
        if exchange is None:
            return False

        if column_name in ["amount", "formula", "comment"]:
            if column_name == "formula" and not str(value).strip():
                # Remove formula if empty
                app.actions.ExchangeFormulaRemove.run([exchange])
                return True

            app.actions.ExchangeModify.run(exchange, {column_name.lower(): value})
            return True

        return False

    def decorationData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides decoration data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide decoration data.

        Returns:
            The decoration data for the index.
        """
        column_name = self.column_name(index)

        if column_name == "amount":
            formula = self.get(index, "formula")
            if pd.isna(formula) or formula is None or formula == "":
                return icons.qicons.edit
            return icons.qicons.parameterized

        return None

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

        # Check if database is locked
        exchange = row.get("_exchange")
        if exchange and database_is_locked(exchange.output["database"]):
            return False

        # Allow editing for specific columns
        if column_name in ["amount", "formula", "comment"]:
            return True

        return False

    def scoped_parameters(self, index: QtCore.QModelIndex) -> dict[str, Parameter]:
        """
        Returns the parameters in scope of the exchange at the given index.

        Args:
            index (QtCore.QModelIndex): The index to get scoped parameters for.

        Returns:
            dict: The parameters in scope.
        """
        from activity_browser.bwutils.commontasks import parameters_in_scope
        
        row = self.row(index)
        if row is None:
            return {}

        exchange = row.get("_exchange")
        if exchange is None:
            return {}

        return parameters_in_scope(node=exchange.output)
