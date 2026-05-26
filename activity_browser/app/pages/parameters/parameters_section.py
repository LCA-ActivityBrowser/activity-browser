from loguru import logger

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd
from bw2data.parameters import ProjectParameter, DatabaseParameter, ActivityParameter, Group

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import refresh_parameter, database_is_locked, parameters_in_scope
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
        self._populate_later_flag = False

        # Parameters tree view
        self.model = ProjectParametersModel(parent=self)
        self.view = ProjectParametersView()
        self.view.setSortingEnabled(False)
        self.view.setUniformRowHeights(True)

        self.view.setModel(self.model)

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
        app.signals.metadata.synced.connect(self.syncLater)
        app.signals.project.changed.connect(self.syncLater)
        app.signals.meta.databases_changed.connect(self.syncLater)
        app.signals.database.deleted.connect(self.syncLater)

        app.signals.parameter.changed.connect(self.syncLater)
        app.signals.parameter.recalculated.connect(self.syncLater)
        app.signals.parameter.deleted.connect(self.syncLater)

    def syncLater(self):
        """
        Schedules a sync operation to be performed later.
        """

        def slot():
            self._populate_later_flag = False
            self.sync()
            self.thread().eventDispatcher().awake.disconnect(slot)

        if self._populate_later_flag:
            return

        self._populate_later_flag = True
        self.thread().eventDispatcher().awake.connect(slot)

    def sync(self):
        """
        Synchronizes the widget with the current state of parameters.
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
        for db_name in bd.databases.list:

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
        groups = Group.select()
        non_act = ["project"] + bd.databases.list

        for group_name in [group.name for group in groups if group.name not in non_act]:
            param = None

            for param in act_params.where(ActivityParameter.group == group_name):
                row = self._parameter_to_row(param, f"Group: {group_name}", param.database)
                translated.append(row)

            if param is None:
                # No parameters in this group: broken group
                translated.append({
                    "name": "Broken parameter group",
                    "_scope": f"Group: {group_name}",
                    "_database": None,
                    "_group": group_name,
                    "_param_type": "activity",
                    "_class": "broken",
                })
                continue

            if not database_is_locked(param.database):
                translated.append({
                    "name": "New parameter...",
                    "_scope": f"Group: {group_name}",
                    "_database": param.database,
                    "_group": group_name,
                    "_param_type": "activity",
                    "_class": "new",
                })

        columns = ["name", "amount", "formula", "uncertainty", "comment", "_parameter", "_scope", "_database", "_group", "_param_type", "_class"]
        df = pd.DataFrame(translated, columns=columns)
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
        menuSetup = [
            lambda m, p: m.add(app.actions.ParameterDelete, p.selected_parameters(),
                               text="Delete parameter(s)",
                               enable=(all([p.deletable for p in p.selected_parameters()])
                                      and len(p.selected_parameters()) > 0)
                                      and all([not database_is_locked(p.data['database'])
                                               for p in p.selected_parameters()
                                               if p.param_type != "project"
                                               ])
                               ),
            lambda m, p: m.add(app.actions.ParameterGroupDelete, p.selected_groups(),
                               text="Delete parameter group(s)",
                               enable=(len(p.selected_groups()) > 0
                                       and all([g not in ["project"] + list(bd.databases)
                                                for g in p.selected_groups()])
                                       and all([not database_is_locked(p.data['database'])
                                                for p in p.selected_parameters()
                                                if p.param_type != "project"
                                                ])
                                       )
                               ),
        ]

    def selected_parameters(self):
        """
        Returns a list of selected parameters in the view.

        Returns:
            list: A list of selected Parameter objects.
        """
        selected = []
        for index in self.selectedIndexes():
            parameter = self.model().get(index, "_parameter")
            if parameter is not None and not pd.isna(parameter) and parameter not in selected:
                selected.append(parameter)

        return selected

    def selected_groups(self):
        """
        Returns a list of selected parameter groups in the view.

        Returns:
            list: A list of selected parameter group names.
        """
        selected = set()
        for index in self.selectedIndexes():
            group = self.model().get(index, "_group")
            group and selected.add(group)

        return list(selected)

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
            database = row.get("_database")
            if not pd.isna(database) and database_is_locked(database):
                return False
            parameter = refresh_parameter(parameter)
            app.actions.ParameterUncertaintyModify.run(parameter.to_peewee_model(), uncertainty_dict=value)

            return True

        return False

    def uncertainty_editor_read_only(self, index: QtCore.QModelIndex) -> bool:
        if self.column_name(index) != "uncertainty":
            return False
        database = self.get(index, "_database")
        if pd.isna(database):
            return False
        return database_is_locked(database)

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

        # Check if database is locked (uncertainty remains openable read-only)
        database = self.get(index, "_database")
        if not pd.isna(database) and database_is_locked(database):
            return column_name == "uncertainty"

        # Prevent editing broken parameters
        if self.get(index, "_class") == "broken":
            return False

        # "New parameter..." placeholder: only the name cell is editable
        if self.get(index, "_class") == "new" and column_name != "name":
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

