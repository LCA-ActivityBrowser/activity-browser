from PySide6.QtCore import QModelIndex
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import pandas as pd

from bw2io.importers.base_lci import LCIImporter

from activity_browser.ui import widgets, core, delegates, icons
from activity_browser.ui.delegates import CardDelegate


class ImportPreviewEdgeTab(QtWidgets.QWidget):
    standardEdgeColumns = ["type", "amount", "unit", "input", "name", "location", "database", "formula"]

    def __init__(self, importer: LCIImporter, parent=None):
        super().__init__(parent)
        self.importer = importer
        self.simple = True

        layout = QtWidgets.QVBoxLayout(self)

        self.edge_model = ImportPreviewEdgeModel(parent=self)
        self.edge_model.set_dataframe(self.build_df())

        self.edge_view = ImportPreviewEdgeView(parent=self)
        self.edge_view.setUniformRowHeights(False)
        self.edge_view.setModel(self.edge_model)
        self.edge_view.setColumnWidth(0, 0)
        self.edge_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)

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
        layout.addWidget(self.edge_view)

        self.sync()

    def sync(self):
        """Synchronize the view based on simple/detailed mode."""
        self.edge_view.header().setHidden(self.simple)
        self.edge_view.viewport().setBackgroundRole(
            QtGui.QPalette.ColorRole.Window if self.simple else QtGui.QPalette.ColorRole.Base)
        self.edge_view.setFrameShape(
            QtWidgets.QFrame.Shape.NoFrame if self.simple else QtWidgets.QFrame.Shape.StyledPanel)

        df = self.edge_model.df.copy()
        if self.simple and "_exc" in df.columns:
            df.rename(columns={"_exc": "exc"}, inplace=True)
        elif not self.simple and "node" in df.columns:
            df.rename(columns={"exc": "_exc"}, inplace=True)
        self.edge_model.set_dataframe(df)
        self.edge_model.group(["_node"])

        for col in self.edge_model.columns():
            if col == "index":
                continue
            index = self.edge_model.columns().index(col)

            hidden = (self.simple and not col == "exc") or (not self.simple and col == "exc")
            self.edge_view.setColumnHidden(index, hidden)

    def build_df(self):

        exchanges = []
        for node in self.importer.data:
            summary = [
                    node.get("name"),
                    node.get("location"),
                    node.get("database"),
                    node.get("code"),
            ]
            summary = " | ".join([str(part) for part in summary if part])

            for ex in node.get("exchanges", []):
                ex_copy = ex.copy()
                ex_copy["_node"] = summary
                exchanges.append(ex_copy)

        df = pd.DataFrame(exchanges)
        df["exc"] = None

        return df

    def on_mode_switch(self, check: Qt.CheckState):
        """Handle the mode switch between simple and detailed view."""
        self.simple = check == Qt.CheckState.Unchecked
        self.sync()


class ShiftedCardDelegate(delegates.CardDelegate):
    def paint(self, painter, option, index):
        # Adjust the rect to shift content left, compensating for indentation
        adjusted_option = QtWidgets.QStyleOptionViewItem(option)
        adjusted_option.rect.adjust(-28, 0, 0, 0)

        # Call the original paint with adjusted rect
        super().paint(painter, adjusted_option, index)


class ImportPreviewEdgeView(widgets.ABTreeView):
    """View for displaying import preview nodes."""

    defaultColumnDelegates = {
        "exc": ShiftedCardDelegate,
    }


class ImportPreviewEdgeModel(core.ABTreeModel):
    """Model for import preview nodes with node delegate support."""

    def displayData(self, index: QtCore.QModelIndex) -> any:
        if not index.isValid():
            return None

        column_name = self.columns()[index.column()]
        if not column_name == "exc":
            return super().displayData(index)

        row_data = self.row(index).copy()
        row_data.dropna(inplace=True)

        # Build the card information
        title = row_data.get('reference product') or row_data.get('name')
        subtitle = row_data.get('name')
        detail = f"{row_data.get('amount')} {row_data.get('unit')}"

        # Build categories list from unit, location
        categories = []
        if row_data.get("type"):
            categories.append(str(row_data.get("type")))
        if row_data.get("location"):
            categories.append(str(row_data.get("location")))
        if row_data.get("categories"):
            categories.append(", ".join([str(cat) for cat in row_data.get("categories")]))
        if row_data.get("database"):
            categories.append(str(row_data.get("database")))

        return {
            "title": title,
            "subtitle": subtitle,
            "categories": categories if categories else None,
            "detail": detail,
        }


    def decorationData(self, index: QModelIndex) -> QtGui.QIcon:
        if not index.isValid():
            return icons.qicons.empty

        column_name = self.columns()[index.column()]
        if not column_name in ["exc"]:
            return super().decorationData(index)

        linked = self.row(index).get("input") is not None
        if linked:
            return icons.qicons.link
        else:
            return icons.qicons.unlink






