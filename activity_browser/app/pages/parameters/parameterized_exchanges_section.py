from loguru import logger

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd
from bw2data.parameters import ParameterizedExchange
from bw2data.backends import ExchangeDataset

from activity_browser import app
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.bwutils.commontasks import (
    database_is_locked,
    exchange_consumer_parts,
    exchange_label,
    exchange_product_name,
)
from activity_browser.bwutils.uncertainty import uncertainty_cell_summary
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
        self._populate_later_flag = False

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
        app.signals.metadata.synced.connect(self.syncLater)
        app.signals.parameter.changed.connect(self.syncLater)
        app.signals.parameter.recalculated.connect(self.syncLater)
        app.signals.parameter.deleted.connect(self.syncLater)
        app.signals.project.changed.connect(self.syncLater)
        app.signals.meta.databases_changed.connect(self.syncLater)
        app.signals.edge.changed.connect(self.syncLater)

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
        Synchronizes the widget with the current state of parameterized exchanges.
        """
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

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

                input_key = exchange.get("input")
                output_key = exchange.get("output")

                input_meta = app.metadata.get_metadata(
                    [input_key], ["name", "unit", "location", "database", "product"]
                ).iloc[0]

                product = exchange_product_name(input_key)
                process, location, database = exchange_consumer_parts(output_key)

                u = getattr(exchange, "uncertainty", None)
                if not isinstance(u, dict):
                    u = {}
                row = {
                    "amount": exchange.get("amount"),
                    "unit": input_meta.get("unit"),
                    "product": product,
                    "process": process,
                    "location": location,
                    "database": database,
                    "formula": exchange.get("formula"),
                    "comment": exchange.get("comment"),
                    "uncertainty": uncertainty_cell_summary(u),
                    "_exchange_label": exchange_label(input_key, output_key, include_database=True),
                    "_exchange": exchange,
                    "_output_key": output_key,
                    "_input_key": input_key,
                }
                translated.append(row)
            except Exception:
                # Skip if exchange can't be loaded
                continue

        columns = [
            "amount", "unit", "product", "process", "location", "database",
            "formula", "comment", "uncertainty",
            "_exchange_label", "_exchange", "_output_key", "_input_key",
        ]
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
        "process": delegates.StringDelegate,
        "location": delegates.StringDelegate,
        "database": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)

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
            if index.isValid() and not view.model().isBranchNode(index):
                row = view.model().row(index)
                if row is not None:
                    output_key = row.get("_output_key")
                    exchange = row.get("_exchange")
                    if output_key and exchange is not None:
                        action = QtGui.QAction("Open process", view)
                        action.triggered.connect(
                            lambda: app.actions.ActivityOpen.run(
                                [output_key], focus_exchange=exchange
                            )
                        )
                        self.addAction(action)


class ParameterizedExchangesModel(core.ABTreeModel):
    """
    A model representing the data for parameterized exchanges.
    """

    _TOOLTIP_COLUMNS = frozenset({"unit", "product", "process", "location", "database"})

    def __init__(self, parent=None):
        """
        Initializes the ParameterizedExchangesModel.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(df=pd.DataFrame(), parent=parent, enable_sorting=True)

    def toolTipData(self, index: QtCore.QModelIndex):
        column_name = self.column_name(index)
        if column_name in self._TOOLTIP_COLUMNS:
            return self.get(index, "_exchange_label")
        return None

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

        if column_name == "uncertainty":
            if database_is_locked(exchange.output[0]):
                return False
            if not isinstance(value, dict):
                return False
            app.actions.ExchangeUncertaintyModify.run([exchange], uncertainty_dict=value)
            return True

        return False

    def uncertainty_editor_initial(self, index: QtCore.QModelIndex) -> dict:
        initial = super().uncertainty_editor_initial(index)
        if initial:
            return initial
        row = self.row(index)
        if row is None:
            return {}
        ex = row.get("_exchange")
        if ex is None:
            return {}
        u = getattr(ex, "uncertainty", None)
        if isinstance(u, dict):
            return dict(u)
        return {}

    def uncertainty_editor_read_only(self, index: QtCore.QModelIndex) -> bool:
        if self.column_name(index) != "uncertainty":
            return False
        row = self.row(index)
        if row is None:
            return True
        ex = row.get("_exchange")
        if ex is None:
            return True
        return database_is_locked(ex.output[0])

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

        exchange = row.get("_exchange")
        if exchange is None:
            return False

        db = exchange.output[0]
        # Locked DB: uncertainty column stays openable (read-only dialog), like exchanges tab.
        if database_is_locked(db):
            return column_name == "uncertainty"

        if column_name in ["amount", "formula", "comment", "uncertainty"]:
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
