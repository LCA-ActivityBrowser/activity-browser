from loguru import logger

from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd
from bw2data.parameters import ParameterizedExchange
from bw2data.backends import ExchangeDataset

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import database_is_locked
from activity_browser.bwutils.utils import Parameter


class ParameterizedExchangesSection(QtWidgets.QWidget):
    """
    A widget section that displays all parameterized exchanges in the current project.

    Attributes:
        model (ParameterizedExchangesModel): The model containing the data for the exchanges.
        view (ParameterizedExchangesView): The view displaying the exchanges.
    """

    def __init__(self, parent=None):
        """
        Initializes the ParameterizedExchangesSection widget.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        # Parameterized exchanges table view
        self.model = ParameterizedExchangesModel(parent=self)
        self.view = ParameterizedExchangesView()
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
        app.signals.metadata.synced.connect(self.sync)
        app.signals.parameter.changed.connect(self.sync)
        app.signals.parameter.recalculated.connect(self.sync)
        app.signals.parameter.deleted.connect(self.sync)
        # app.signals.project.changed.connect(self.sync)
        # app.signals.meta.databases_changed.connect(self.sync)

    def sync(self):
        """
        Synchronizes the widget with the current state of parameterized exchanges.
        """
        logger.debug(f"Syncing {self.__class__.__name__}: {id(self)}")

        df = self.build_exchanges_df()
        self.model.set_dataframe(df)

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

