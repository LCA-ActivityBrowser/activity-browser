from PySide6.QtCore import QModelIndex
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

from loguru import logger

import pandas as pd

from bw2io.importers.base_lci import LCIImporter

from activity_browser.ui import widgets, core, delegates, icons

from ..node_select_dialog import NodeSelectDialog


class ImportPreviewEdgeTab(QtWidgets.QWidget):
    standardEdgeColumns = ["linked", "type", "amount", "unit", "input", "name", "location", "database", "formula"]

    def __init__(self, importer: LCIImporter, parent=None):
        super().__init__(parent)
        self.importer = importer
        self.simple = True
        self.old_links: dict[tuple[int, int], tuple[str, str] | None] = {}

        layout = QtWidgets.QVBoxLayout(self)

        self.edge_model = ImportPreviewEdgeModel(parent=self)
        self.edge_model.set_dataframe(self.build_df())
        self.edge_model.group(["_node"])

        self.edge_view = ImportPreviewEdgeView(importer, self)
        self.edge_view.setUniformRowHeights(False)
        self.edge_view.setModel(self.edge_model)
        self.edge_view.setColumnWidth(0, 0)

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
        logger.debug(f"Syncing {self.__class__.__name__}: {id(self)}")

        self.edge_view.header().setHidden(self.simple)
        self.edge_view.viewport().setBackgroundRole(
            QtGui.QPalette.ColorRole.Window if self.simple else QtGui.QPalette.ColorRole.Base)
        self.edge_view.setFrameShape(
            QtWidgets.QFrame.Shape.NoFrame if self.simple else QtWidgets.QFrame.Shape.StyledPanel)

        df = self.build_df()

        if self.simple and "_exc" in df.columns:
            df.rename(columns={"_exc": "exc"}, inplace=True)
        elif not self.simple and "node" in df.columns:
            df.rename(columns={"exc": "_exc"}, inplace=True)

        self.edge_model.update_dataframe(df)

        for col in self.edge_model.columns():
            if col == "index":
                continue
            index = self.edge_model.columns().index(col)

            hidden = (self.simple and not col == "exc") or (not self.simple and col == "exc")
            self.edge_view.setColumnHidden(index, hidden)

    def build_df(self):

        exchanges = []
        for node_i, node in enumerate(self.importer.data):
            summary = [
                    node.get("name"),
                    node.get("location"),
                    node.get("database"),
                    node.get("code"),
            ]
            summary = " | ".join([str(part) for part in summary if part])

            for exc_i, exc in enumerate(node.get("exchanges", [])):
                exc = exc.copy()
                exc["_node"] = summary
                exc["_location"] = (node_i, exc_i)
                exchanges.append(exc)

        df = pd.DataFrame(exchanges)
        for col in [col for col in self.standardEdgeColumns if col not in df.columns]:
            df[col] = None
        df["exc"] = None

        def determine_link_status(row):
            input_val = row["input"]
            location = row["_location"]

            if not isinstance(input_val, tuple):
                return "unlinked"
            elif location in self.old_links:
                return "relinked"
            else:
                return "linked"

        df["linked"] = df.apply(determine_link_status, axis=1)

        return df

    def on_mode_switch(self, check: Qt.CheckState):
        """Handle the mode switch between simple and detailed view."""
        self.simple = check == Qt.CheckState.Unchecked
        self.sync()

    def relink_selected_exchanges(self):
        """Open a dialog to link selected exchanges to existing nodes."""
        exchange_locations = self.edge_view.selected_exchanges
        if not exchange_locations:
            return

        dialog = NodeSelectDialog(parent=self)
        if not dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            return

        selected_node = dialog.get_selected_node()

        for loc in exchange_locations:
            node_i, exc_i = loc

            if loc not in self.old_links:
                self.old_links[loc] = self.importer.data[node_i]["exchanges"][exc_i].get("input")

            self.importer.data[node_i]["exchanges"][exc_i]["input"] = (selected_node["database"], selected_node["code"])

        self.sync()


class ShiftedCardDelegate(delegates.CardDelegate):
    """
    Delegate that shifts the card content to the left to compensate for indentation.
    """
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

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.callback(
                text="Link exchange" if len(p.selected_exchanges) == 1 else "Link exchanges",
                func=p.tab.relink_selected_exchanges,
            )
        ]

    def __init__(self, importer: LCIImporter, tab: ImportPreviewEdgeTab):
        super().__init__(tab)
        self.importer = importer
        self.old_links = {}
        self.tab = tab

    @property
    def selected_exchanges(self):
        """
        Returns a list of selected exchange locations as (node_index, exchange_index) tuples. These can be used to
        identify and manipulate the selected exchanges in the importer's data, which is a list of lists.
        """
        return list(set([self.model().get(index, "_location") for index in self.selectedIndexes()]))


class ImportPreviewEdgeModel(core.ABTreeModel):
    """Model for import preview nodes with node delegate support."""

    def displayData(self, index: QtCore.QModelIndex) -> any:
        if not index.isValid():
            return None

        column_name = self.columns()[index.column()]
        if not column_name == "exc" or self.row(index) is None:
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

        linked = self.get(index, "linked")
        if linked == "linked":
            return icons.qicons.link
        elif linked == "unlinked":
            return icons.qicons.unlink
        elif linked == "relinked":
            return icons.qicons.relink
        return icons.qicons.empty

    def indexSelectable(self, index: QModelIndex) -> bool:
        # Don't make the tree column selectable
        if index.column() == 0:
            return False
        return True






