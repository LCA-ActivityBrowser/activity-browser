from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import actions, signals
from activity_browser.ui import widgets, icons
from activity_browser.ui.tables import delegates
from activity_browser.bwutils import AB_metadata

from .inventory_tab import InventoryTab


class CalculationResultsPage(QtWidgets.QWidget):
    def __init__(self, cs_name: str, mlca, contributions, montecarlo, parent=None):
        super().__init__(parent)
        self.cs_name, self.mlca, self.contributions, self.mc = cs_name, mlca, contributions, montecarlo
        self.cs = bd.calculation_setups[self.cs_name]

        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.addTab(InventoryTab(self), "Inventory")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(widgets.ABLabel.demiBold("Calculation Results: " + self.cs_name, self))
        layout.addWidget(widgets.ABHLine(self))
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # # self.has_scenarios: bool = data.get("calculation_type") not in ("simple", "regional")
        #
        #
        #
        # # self.method_dict = bc.get_LCIA_method_name_dict(self.mlca.methods)
        # # self.single_func_unit = len(self.mlca.func_units) == 1
        # # self.single_method = len(self.mlca.methods) == 1
        #
        # self.tabs = {
        #     "inventory": InventoryTab(self),
        #     # "results": ResultsTab(self),
        #     # ef=ElementaryFlowContributionTab(self),
        #     # process=ProcessContributionsTab(self),
        #     # ft=FirstTierContributionsTab(self.cs_name, parent=self),
        #     # sankey=SankeyNavigatorWidget(self.cs_name, parent=self),
        #     # tree=TreeNavigatorWidget(self.cs_name, parent=self),
        #     # mc=MonteCarloTab(self),
        #     # gsa=GSATab(self),
        # }
        # self.setup_tabs()
        # self.setCurrentWidget(self.tabs.results)
        # self.currentChanged.connect(self.generate_content_on_click)

    @property
    def has_scenarios(self) -> bool:
        return hasattr(self.mlca, "scenario_names")

    def connect_signals(self):
        signals.method.deleted.connect(self.on_method_deleted)
        signals.meta.methods_changed.connect(self.sync)

    def on_method_deleted(self, method):
        if method.name == self.name:
            self.deleteLater()

    def sync(self):
        self.impact_category = bd.Method(self.name)
        self.model.setDataFrame(self.build_df())

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(widgets.ABLabel.demiBold("Impact Category: " + " - ".join(self.name), self))
        layout.addWidget(widgets.ABHLine(self))
        layout.addWidget(self.view)
        self.setLayout(layout)

    def build_df(self):
        df = pd.DataFrame(self.impact_category.load(), columns=["id", "amount"])
        other = AB_metadata.dataframe[["id", "name", "categories", "database", "unit"]]

        df = df.merge(other, left_on="id", right_on="id").rename(columns={"id": "_id"})
        df["_impact_category_name"] = [self.name for i in range(len(df))]

        cols = ["name", "categories", "database", "amount", "unit", "_id", "_impact_category_name"]
        return df[cols]


class CharacterizationFactorsView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "categories": delegates.ListDelegate,
    }


class ExchangesItem(widgets.ABDataItem):
    def flags(self, col: int, key: str):
        """
        Returns the item flags for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the flags.

        Returns:
            QtCore.Qt.ItemFlags: The item flags.
        """
        flags = super().flags(col, key)
        if key in ["amount"]:
            return flags | Qt.ItemFlag.ItemIsEditable
        return flags

    def decorationData(self, col, key):
        """
        Provides decoration data for the item.

        Args:
            col: The column index.
            key: The key for which to provide decoration data.

        Returns:
            The decoration data for the item.
        """
        if key == "name":
            return icons.qicons.biosphere

    def fontData(self, col: int, key: str):
        """
        Returns the font data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the font data.

        Returns:
            QtGui.QFont: The font data.
        """
        font = super().fontData(col, key)

        # set the font to bold if it's a production/functional exchange
        if key == "name":
            font.setWeight(QtGui.QFont.Weight.DemiBold)
        return font

    def setData(self, col: int, key: str, value) -> bool:
        """
        Sets the data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to set the data.
            value: The value to set.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if key not in ["amount"]:
            return False

        actions.CFAmountModify.run(self["_impact_category_name"], self["_id"], value)


class CharacterizationFactorsModel(widgets.ABAbstractItemModel):
    dataItemClass = ExchangesItem
