from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import actions, signals
from activity_browser.ui import widgets, icons, delegates
from activity_browser.bwutils import AB_metadata


class ImpactCategoryDetailsPage(QtWidgets.QWidget):
    def __init__(self, name: tuple, parent=None):
        super().__init__(parent)
        self.name = name
        self.impact_category = bd.Method(name)

        self.setObjectName(" | ".join(name))

        self.model = CharacterizationFactorsModel(self, self.build_df())
        self.view = CharacterizationFactorsView(self)
        self.view.setModel(self.model)

        # resizing name and categories columns
        self.view.resizeColumnToContents(0)
        self.view.resizeColumnToContents(1)

        self.build_layout()
        self.connect_signals()

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


class CharacterizationFactorsModel(widgets.ABItemModel):
    dataItemClass = ExchangesItem
