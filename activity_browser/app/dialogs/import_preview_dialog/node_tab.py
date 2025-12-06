from PySide6.QtCore import QModelIndex
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

from loguru import logger

import pandas as pd

from bw2io.importers.base_lci import LCIImporter

from activity_browser.ui import widgets, core, delegates, icons


class ImportPreviewNodeTab(QtWidgets.QWidget):
    standardNodeColumns = ["type", "name", "product", "exchanges", "unlinked_exchanges", "location", "unit", "categories", "code",
                           "database"]
    standardEdgeColumns = ["type", "amount", "unit", "input", "name", "location", "database", "formula"]

    def __init__(self, importer: LCIImporter, parent=None):
        super().__init__(parent)
        self.importer = importer
        self.simple = True

        layout = QtWidgets.QVBoxLayout(self)

        self.node_model = ImportPreviewNodeModel(parent=self)
        self.node_model.set_dataframe(self.build_df())

        self.node_view = ImportPreviewNodeView(parent=self)
        self.node_view.setModel(self.node_model)

        # Create simple/detailed view toggle
        self.view_toggle = QtWidgets.QCheckBox("Details")
        self.view_toggle.setChecked(not self.simple)
        self.view_toggle.setToolTip("Toggle between simple and detailed view")
        self.view_toggle.checkStateChanged.connect(self.on_mode_switch)

        # Create top bar with toggle
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addStretch()
        top_bar.addWidget(self.view_toggle)

        layout.addLayout(top_bar)
        layout.addWidget(self.node_view)

        self.sync()

    def sync(self):
        """Synchronize the view based on simple/detailed mode."""
        logger.debug(f"Syncing {self.__class__.__name__}: {id(self)}")

        self.node_view.header().setHidden(self.simple)
        self.node_view.viewport().setBackgroundRole(
            QtGui.QPalette.ColorRole.Window if self.simple else QtGui.QPalette.ColorRole.Base)
        self.node_view.setFrameShape(
            QtWidgets.QFrame.Shape.NoFrame if self.simple else QtWidgets.QFrame.Shape.StyledPanel)

        df = self.node_model.df.copy()
        if self.simple and "_node" in df.columns:
            df.rename(columns={"_node": "node"}, inplace=True)
        elif not self.simple and "node" in df.columns:
            df.rename(columns={"node": "_node"}, inplace=True)
        self.node_model.set_dataframe(df)

        for col in self.node_model.columns():
            if col == "index":
                continue
            index = self.node_model.columns().index(col)

            hidden = (self.simple and not col == "node") or (not self.simple and col == "node")
            self.node_view.setColumnHidden(index, hidden)

    def build_df(self):
        node_df = pd.DataFrame(self.importer.data)
        for col in [col for col in self.standardNodeColumns if col not in node_df.columns]:
            node_df[col] = None

        node_df["_exchanges"] = node_df["exchanges"]
        node_df["unlinked_exchanges"] = node_df["exchanges"].apply(
            lambda x: sum(1 for ex in x if not ex.get("input")) if isinstance(x, list) else 0
        )
        node_df["exchanges"] = node_df["exchanges"].apply(lambda x: len(x) if isinstance(x, list) else 0)

        node_df = node_df[
            self.standardNodeColumns +
            [col for col in node_df.columns if col not in self.standardNodeColumns]
            ]
        node_df["_importer_index"] = range(len(node_df))

        node_df["node"] = None

        return node_df

    def on_mode_switch(self, check: Qt.CheckState):
        """Handle the mode switch between simple and detailed view."""
        self.simple = check == Qt.CheckState.Unchecked
        self.sync()


class ImportPreviewNodeView(widgets.ABTreeView):
    """View for displaying import preview nodes."""

    defaultColumnDelegates = {
        "node": delegates.CardDelegate,
    }


class ImportPreviewNodeModel(core.ABTreeModel):
    """Model for import preview nodes with node delegate support."""

    def displayData(self, index: QtCore.QModelIndex) -> any:
        if not index.isValid():
            return None

        column_name = self.columns()[index.column()]
        if not column_name == "node":
            return super().displayData(index)

        row_data = self.row(index).copy()
        row_data.dropna(inplace=True)

        # Get the product or name for title
        title = row_data.get("product") or row_data.get("name")

        # Build subtitle with type and database
        if row_data.get("categories"):
            subtitle = ", ".join([str(cat) for cat in row_data.get("categories")])
        elif row_data.get("product"):
            subtitle = row_data.get("name")
        else:
            excs = row_data.get("exchanges")
            unlinked = row_data.get("unlinked_exchanges")
            nomination = "exchanges" if excs != 1 else "exchange"

            subtitle = f"{excs} {nomination}, {unlinked} unlinked"

        # Build categories list from unit, location
        categories = []
        if row_data.get("unit"):
            categories.append(str(row_data.get("unit")))
        if row_data.get("location"):
            categories.append(str(row_data.get("location")))
        if row_data.get("database"):
            categories.append(str(row_data.get("database")))

        return {
            "title": title,
            "subtitle": subtitle,
            "categories": categories if categories else None,
        }


    def decorationData(self, index: QModelIndex) -> QtGui.QIcon:
        if not index.isValid():
            return icons.qicons.empty

        column_name = self.columns()[index.column()]
        if not column_name in ["node", "type"]:
            return super().decorationData(index)

        node_type = self.get(index, "type")

        if node_type == "product":
            return icons.qicons.product
        if node_type == "waste":
            return icons.qicons.waste
        if node_type == "processwithreferenceproduct":
            return icons.qicons.processproduct
        if node_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        return icons.qicons.process

