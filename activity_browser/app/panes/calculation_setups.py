from qtpy import QtWidgets, QtGui
from loguru import logger

import bw2data as bd
import pandas as pd

from activity_browser import app
from activity_browser.ui import widgets, delegates, core


class CalculationSetupsPane(widgets.ABAbstractPane):
    title = "Calculation Setups"
    unique = True

    def __init__(self, parent):
        """
        Initializes the CalculationSetupsPane.

        This constructor sets up the view and model for displaying calculation setups,
        configures the view's appearance and behavior, and builds the layout while
        connecting necessary signals.

        Args:
            parent (QtWidgets.QWidget): The parent widget for this pane.
        """
        super().__init__(parent)
        self.model = CalculationSetupsModel(parent=self)
        self.view = CalculationSetupsView()
        self.view.setModel(self.model)

        self.view.setAlternatingRowColors(True)

        self.build_layout()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signals to the appropriate slots.
        """
        app.signals.meta.calculation_setups_changed.connect(self.sync)

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(5, 0, 5, 5)
        self.setLayout(layout)

    def sync(self):
        """
        Synchronizes the model with the current state of the calculation setups.
        """
        logger.debug(f"Syncing {self.__class__.__name__}: {id(self)}")
        df = self.build_df()
        self.model.set_dataframe(df)
        self.view.resizeColumnToContents(0)

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the calculation setups.

        Returns:
            pd.DataFrame: The DataFrame containing the calculation setups data.
        """
        data = []
        for cs in bd.calculation_setups:
            data.append(
                {
                    "name": cs,
                    "functional_units": len(bd.calculation_setups[cs].get("inv", [])),
                    "impact_categories": len(bd.calculation_setups[cs].get("ia", [])),
                }
            )

        cols = ["name", "functional_units", "impact_categories"]

        return pd.DataFrame(data, columns=cols)


class CalculationSetupsView(widgets.ABTreeView):
    """
    A view that displays the calculation setups in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "name": delegates.StringDelegate,
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(app.actions.CSNew),
            lambda m, p: m.add(app.actions.CSOpen, p.calculation_setups,
                                  enable=bool(p.calculation_setups)),
            lambda m, p: m.add(app.actions.CSDelete, p.calculation_setups,
                                  enable=bool(p.calculation_setups)),
            lambda m, p: m.add(app.actions.CSRename, p.calculation_setups[0] if p.single_selection else None,
                                  enable=p.single_selection),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.CSCalculate, p.calculation_setups[0] if p.single_selection else None,
                                  enable=p.single_selection),
        ]

    @property
    def calculation_setups(self):
        if not self.selectedIndexes():
            return []
        names = self.model().values_from_indices("name", self.selectedIndexes())
        return list(set(names))

    @property
    def single_selection(self):
        return len(self.calculation_setups) == 1

    class HeaderMenu(QtWidgets.QMenu):
        """
        A header menu for the DatabasesView. Currently not used.
        """

        def __init__(self, *args, **kwargs):
            super().__init__()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """
        Handles the mouse double click event to open the selected calculation setups.

        Args:
            event (QtGui.QMouseEvent): The mouse double click event.
        """
        index = self.indexAt(event.pos())

        if not index.isValid():
            return

        row = self.model().row(index)
        if row is None:
            return

        app.actions.CSOpen.run(row["name"])


    def dragMoveEvent(self, event) -> None:
        pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
            for key in keys:
                act = bd.get_node(key=key)
                if act["type"] not in bd.labels.product_node_types + ["processwithreferenceproduct"]:
                    keys.remove(key)

            if not keys:
                return

            event.accept()

    def dropEvent(self, event) -> None:
        event.accept()

        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        for key in keys:
            act = bd.get_node(key=key)
            if act["type"] not in bd.labels.product_node_types + ["processwithreferenceproduct"]:
                keys.remove(key)

        functional_units = [{key: 1.0} for key in keys]

        app.actions.CSNew.run(functional_units=functional_units)


class CalculationSetupsModel(core.ABTreeModel):
    """
    A model representing the data for the calculation setups.
    """

    def fontData(self, index):
        """
        Provides font data for the model.

        Args:
            index: The index for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the index.
        """
        column_name = self.column_name(index)

        if column_name == "name":
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            return font

        return None

