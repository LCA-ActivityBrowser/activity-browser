from qtpy import QtWidgets, QtGui

import bw2data as bd
import pandas as pd

from activity_browser import signals, actions
from activity_browser.ui import widgets, delegates


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
        self.view = CalculationSetupsView()
        self.model = CalculationSetupsModel()
        self.view.setModel(self.model)

        self.view.setAlternatingRowColors(True)

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
        Synchronizes the model with the current state of the calculation setups.
        """
        self.model.setDataFrame(self.build_df())
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
            lambda menu: menu.add(actions.CSNew),
            lambda menu: menu.add(actions.CSOpen, menu.calculation_setups,
                                  enable=bool(menu.calculation_setups)),
            lambda menu: menu.add(actions.CSDelete, menu.calculation_setups,
                                  enable=bool(menu.calculation_setups)),
            lambda menu: menu.add(actions.CSRename, menu.calculation_setups[0] if menu.single_selection else None,
                                  enable=menu.single_selection),
            lambda menu: menu.addSeparator(),
            lambda menu: menu.add(actions.CSCalculate, menu.calculation_setups[0] if menu.single_selection else None,
                                  enable=menu.single_selection),
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """
        Handles the mouse double click event to open the selected calculation setups.

        Args:
            event (QtGui.QMouseEvent): The mouse double click event.
        """
        if not self.selectedIndexes():
            return

        index = self.indexAt(event.pos())

        actions.CSOpen.run(index.internalPointer()["name"])


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

        actions.CSNew.run(functional_units=functional_units)


class CalculationSetupsItem(widgets.ABDataItem):
    """
    An item representing a calculation setup in the tree view.
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

