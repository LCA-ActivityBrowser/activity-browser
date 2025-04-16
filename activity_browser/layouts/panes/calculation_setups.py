from qtpy import QtWidgets, QtGui

import bw2data as bd
import pandas as pd

from activity_browser import signals, actions
from activity_browser.ui import widgets, delegates


class CalculationSetupsPane(widgets.ABAbstractPane):
    title = "Calculation Setups"
    hideMode = widgets.ABDockWidget.HideMode.Hide

    def __init__(self, parent):
        super().__init__(parent)
        self.view = CalculationSetupsView()
        self.model = CalculationSetupsModel()
        self.view.setModel(self.model)

        self.view.setAlternatingRowColors(True)
        self.view.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.view.setIndentation(0)

        self.build_layout()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signals to the appropriate slots.
        """
        signals.meta.calculation_setups_changed.connect(self.sync)
        signals.project.changed.connect(self.sync)

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
        Synchronizes the model with the current state of the databases.
        """
        self.model.setDataFrame(self.build_df())
        self.view.resizeColumnToContents(0)
        self.view.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the databases.

        Returns:
            pd.DataFrame: The DataFrame containing the databases data.
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
    A view that displays the databases in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "name": delegates.StringDelegate,
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda menu: menu.add(actions.CSNew),
            lambda menu: menu.add(actions.CSOpen, menu.calculation_setups),
            lambda menu: menu.add(actions.CSDelete, menu.calculation_setups),
            lambda menu: menu.add(actions.CSRename, menu.calculation_setups[0], enable=menu.single_selection),
            lambda menu: menu.addSeparator(),
            lambda menu: menu.add(actions.CSCalculate, menu.calculation_setups[0], enable=menu.single_selection),
        ]

        @property
        def calculation_setups(self):
            return [item["name"] for item in {index.internalPointer() for index in self.parent().selectedIndexes()}]

        @property
        def single_selection(self):
            return len(self.calculation_setups) == 1

    class HeaderMenu(QtWidgets.QMenu):
        """
        A header menu for the DatabasesView. Currently not used.
        """

        def __init__(self, *args, **kwargs):
            super().__init__()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """
        Handles the mouse double click event to toggle the read-only state or select the database.

        Args:
            event (QtGui.QMouseEvent): The mouse double click event.
        """
        if not self.selectedIndexes():
            return

        index = self.indexAt(event.pos())

        actions.CSOpen.run(index.internalPointer()["name"])


class CalculationSetupsItem(widgets.ABDataItem):
    """
    An item representing a database in the tree view.
    """
    def fontData(self, col: int, key: str):
        """
        Provides font data for the item.

        Args:
            col (int): The column index.
            key (str): The key for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the item.
        """
        font = super().fontData(col, key)
        if key == "name":
            font.setWeight(QtGui.QFont.Weight.DemiBold)
        return font


class CalculationSetupsModel(widgets.ABItemModel):
    """
    A model representing the data for the databases.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = CalculationSetupsItem

