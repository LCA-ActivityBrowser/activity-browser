from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
import pandas as pd
import bw2data as bd
from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import refresh_parameter, database_is_locked
from activity_browser.bwutils.utils import Parameter


class ParametersSection(QtWidgets.QWidget):
    """
    A widget section that displays all parameters in the current project.

    This section shows a tree view of parameters organized by scope:
    - Project parameters
    - Database parameters (grouped by database)
    - Activity parameters (grouped by activity group)

    Attributes:
        model (ProjectParametersModel): The model containing the data for the parameters.
        view (ProjectParametersView): The view displaying the parameters.
    """

    def __init__(self, parent=None):
        """
        Initializes the ParametersSection widget.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        # Parameters tree view
        self.model = ProjectParametersModel(parent=self)
        self.view = ProjectParametersView()
        self.view.setModel(self.model)
        self.view.setUniformRowHeights(True)

        self.build_layout()
        self.connect_signals()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.setLayout(layout)

    def connect_signals(self):
        """
        Connects signals to their respective slots.
        """
        app.signals.metadata.synced.connect(self.sync)

        app.signals.parameter.changed.connect(self.sync)
        app.signals.parameter.recalculated.connect(self.sync)
        app.signals.parameter.deleted.connect(self.sync)

    def sync(self):
        """
        Synchronizes the widget with the current state of parameters.
        """
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

        # Database parameters
        for param in DatabaseParameter.select():
            row = self._parameter_to_row(param, f"{param.database}", param.database)
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

        return df.sort_values(by="_param_type", key=lambda c: c.map({"project": 0, "database": 1, "activity": 2}))

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

