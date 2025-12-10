from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt
from loguru import logger

import pandas as pd
import bw2data as bd

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import refresh_node, refresh_parameter, parameters_in_scope, database_is_locked, node_group


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

        self.activity = refresh_node(self.activity)
        df = self.build_df()
        df.reset_index(drop=True, inplace=True)
        self.model.set_dataframe(df)
        self.model.group(["_scope"])
        self.view.expandAll()

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
            row["uncertainty"] = param.uncertainty
            row["formula"] = param.data.get("formula")
            row["comment"] = param.data.get("comment")
            row["_parameter"] = param
            row["_activity"] = self.activity

            if param.param_type == "project":
                row["_scope"] = "Current project"
            elif param.param_type == "database":
                row["_scope"] = "This database"
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

        parameter = row.get("_parameter")
        if parameter is None:
            return False

        if column_name in ["amount", "formula", "name", "comment"]:
            parameter = refresh_parameter(parameter)
            app.actions.ParameterModify.run(parameter, column_name, value)
            return True

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
        row = self.row(index)

        if row is None:
            return None
        
        if not isinstance(row, pd.Series):
            return None

        if column_name == "amount":
            if pd.isna(row.get("formula")) or row.get("formula") is None or row.get("formula") == "":
                return icons.qicons.empty  # empty icon to align the values
            return icons.qicons.parameterized

        return None

    def indexEditable(self, index):
        column_name = self.column_name(index)
        row = self.row(index)

        # Prevent editing if the database is locked
        if row is None or database_is_locked(row.get("_activity", {}).get("database")):
            return False

        # Allow editing for specific columns
        if column_name in ["amount", "formula", "uncertainty", "name", "comment"]:
            return True

        return False
    
    def scoped_parameters(self, index):
        """
        Returns the scoped parameters for the index.

        Args:
            index (QtCore.QModelIndex): The index to get scoped parameters for.

        Returns:
            dict: A dictionary of scoped parameters for the index.
        """
        row = self.row(index)
        if row is None:
            return {}
        return parameters_in_scope(parameter=row.get("_parameter"))
