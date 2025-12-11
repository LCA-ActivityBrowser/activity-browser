from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
from loguru import logger

import pandas as pd
import bw2data as bd

from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter, Group, ParameterBase

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import refresh_node, refresh_parameter, parameters_in_scope, database_is_locked, node_group
from activity_browser.bwutils.utils import Parameter


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

        self.view = ParametersView(self)
        self.model = ParametersModel(tab=self)
        self.view.setModel(self.model)

        self.build_layout()
        self.connect_signals()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 1)
        layout.addWidget(self.view)

        self.setLayout(layout)

    def connect_signals(self):
        """
        Connects signals to their respective slots.
        """
        app.signals.parameter.changed.connect(self.sync)
        app.signals.parameter.recalculated.connect(self.sync)
        app.signals.parameter.deleted.connect(self.sync)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

        df = self.build_df()
        self.model.set_dataframe(df, group=["_param_type", "_scope"])
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

        translated.append({
            "name": "New parameter...",
            "_group": "project",
            "_param_type": "project",
            "_class": "new",
        })

        # Database parameters
        db_params = DatabaseParameter.select()
        db_name = self.activity["database"]

        for param in db_params.where(DatabaseParameter.database == db_name):
            row = self._parameter_to_row(param, db_name, db_name)
            translated.append(row)

        if not database_is_locked(db_name):
            translated.append({
                "name": "New parameter...",
                "_scope": db_name,
                "_database": db_name,
                "_group": db_name,
                "_param_type": "database",
                "_class": "new",
            })

        # Activity parameters
        act_params = ActivityParameter.select()
        group_name = node_group(self.activity) or str(self.activity.id)

        for param in act_params.where(ActivityParameter.group == group_name):
            row = self._parameter_to_row(param, f"Group: {group_name}", param.database)
            translated.append(row)

        if not database_is_locked(self.activity["database"]):
            translated.append({
                "name": "New parameter...",
                "_scope": f"Group: {group_name}",
                "_database": self.activity["database"],
                "_group": group_name,
                "_param_type": "activity",
                "_class": "new",
            })

        columns = ["name", "amount", "formula", "uncertainty", "comment", "_parameter", "_scope", "_database", "_group",
                   "_param_type", "_class"]
        df = pd.DataFrame(translated, columns=columns)

        df["_activity"] = [self.activity for i in range(len(df))]
        return df

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
            "_class": "instantiated",
        }

        return row


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

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m: m.add(app.actions.ParameterDelete, m.parameters, enable=bool(m.parameters) and not m.locked),
        ]

        @property
        def locked(self):
            table_view: ParametersView = self.parent()
            return database_is_locked(table_view.activity["database"])
        
        @property
        def activity(self):
            table_view: ParametersView = self.parent()
            return table_view.activity
        
        @property
        def parameters(self):
            table_view: ParametersView = self.parent()
            table_model: ParametersModel = table_view.model()
            
            selected_indices = table_view.selectedIndexes()
            params = table_model.values_from_indices("_parameter", selected_indices)
            # Convert to peewee models
            return [p.to_peewee_model() for p in params if p is not None]
    
    def __init__(self, parent):
        """
        Initializes the ParametersView.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        self.setSortingEnabled(True)

    @property
    def activity(self):
        """
        Returns the activity associated with the view.

        Returns:
            The activity associated with the view.
        """
        return self.parent().activity


class ParametersModel(core.ABTreeModel):
    """
    A model representing the data for the parameters.
    """
    def __init__(self, tab: ParametersTab):
        super().__init__(parent=tab)
        self.tab = tab
    
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
        if row.get("_class") == "new":
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
            formula = self.get(index, "formula")
            formula = isinstance(formula, str) and formula.strip()

            return icons.qicons.parameterized if formula else icons.qicons.empty

        return None

    def fontData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides font data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the index.
        """
        param_class = self.get(index, "_class")
        if param_class == "new":
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.ExtraLight)
            return font

        if param_class == "broken":
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.Bold)
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

        # Prevent editing broken parameters
        if self.get(index, "_class") == "broken":
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
        parameter = self.get(index, "_parameter")
        if parameter is None or isinstance(parameter, float):  # NaN check
            return {}

        return parameters_in_scope(parameter=parameter)
