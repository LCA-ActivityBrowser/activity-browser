from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import actions, signals
from activity_browser.ui import widgets, icons, delegates
from activity_browser.bwutils import AB_metadata

from .impact_category_header import ImpactCategoryHeader


class ImpactCategoryDetailsPage(QtWidgets.QWidget):
    def __init__(self, name: tuple, parent=None):
        super().__init__(parent)
        self.name = name
        self.impact_category = bd.Method(name)
        self.is_editable = False

        self.setObjectName(" | ".join(name))

        self.header = ImpactCategoryHeader(self)

        self.model = CharacterizationFactorsModel(self)
        self.view = CharacterizationFactorsView(self)
        self.view.setModel(self.model)

        self.build_layout()
        self.connect_signals()
        self.sync()

        # resizing name and categories columns
        self.view.resizeColumnToContents(0)
        self.view.resizeColumnToContents(1)

    def connect_signals(self):
        signals.method.renamed.connect(self.on_method_renamed)
        signals.method.deleted.connect(self.on_method_deleted)
        signals.meta.methods_changed.connect(self.sync)

    def on_method_renamed(self, old_name, new_name):
        if self.name == old_name:
            self.name = new_name
            self.setObjectName(" | ".join(new_name))
            self.setWindowTitle(" | ".join(new_name))

    def on_method_deleted(self, method):
        if method.name == self.name:
            self.deleteLater()

    def sync(self):
        if self.name not in bd.methods:
            self.deleteLater()
            return

        self.impact_category = bd.Method(self.name)
        self.model.setDataFrame(self.build_df())
        self.header.sync()

    def on_editable_changed(self, is_editable):
        """
        Called when the editable checkbox state changes.
        Updates the editable state and refreshes the model.
        """
        self.is_editable = is_editable
        # Trigger a model reset to update the item flags
        self.model.beginResetModel()
        self.model.endResetModel()

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.header)
        layout.addWidget(widgets.ABHLine(self))
        layout.addWidget(self.view)
        self.setLayout(layout)

    def build_df(self):
        df = pd.DataFrame(self.impact_category.load(), columns=["id", "data"])
        df["amount"] = df["data"].apply(lambda x: x if isinstance(x, (float, int)) else x.get("amount"))
        df["uncertainty"] = df["data"].apply(lambda x: 0 if isinstance(x, (float, int)) else x.get("uncertainty type"))

        other = AB_metadata.dataframe[["id", "name", "categories", "database", "unit"]]

        df = df.merge(other, left_on="id", right_on="id").rename(columns={"id": "_id", "data": "_cf"})
        df["_impact_category_name"] = [self.name for i in range(len(df))]

        cols = ["name", "categories", "database", "amount", "unit", "uncertainty", "_id", "_impact_category_name", "_cf"]
        return df[cols]


class CharacterizationFactorsView(widgets.ABTreeView):
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "categories": delegates.ListDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m: m.add(actions.CFRemove, m.impact_category_name, m.char_factors,
                            enable=bool(m.char_factors) and m.is_editable,
                            text="Remove characterization factor(s)"),
        ]

        @property
        def is_editable(self):
            return self.parent().parent().is_editable

        @property
        def impact_category_name(self):
            return self.parent().parent().name

        @property
        def char_factors(self):
            indexes = self.parent().selectedIndexes()
            return [(idx.internalPointer()["_id"], idx.internalPointer()["_cf"]) 
                    for idx in indexes if idx.isValid() and idx.column() == 0]

    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSortingEnabled(True)

    def dragEnterEvent(self, event):
        """Handle drag enter event for biosphere flows."""
        if not self.parent().is_editable:
            return

        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            event.accept()

    def dropEvent(self, event):
        """Handle drop event to add new characterization factors."""
        keys = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        
        # Filter to only biosphere flows
        biosphere_keys = []
        for key in keys:
            try:
                node = bd.get_node(id=key)
                if node.get("type") in ["emission", "natural resource", "inventory indicator", "economic", "social"]:
                    biosphere_keys.append(key)
            except:
                pass

        if biosphere_keys:
            actions.CFNew.run(self.parent().name, biosphere_keys)




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
        
        # Get the parent page to check if it's editable
        try:
            parent_page = self.model.parent()
            if parent_page and hasattr(parent_page, 'is_editable'):
                if not parent_page.is_editable:
                    return flags
        except:
            pass
        
        if key in ["amount", "uncertainty"]:
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
