from qtpy import QtWidgets, QtCore, QtGui

import pandas as pd

from bw2io.importers.base_lci import LCIImporter

from activity_browser.ui import widgets, core


class ImportPreviewDialog(QtWidgets.QDialog):
    standardNodeColumns = ["type", "name", "exchanges", "location", "unit", "categories", "code", "database"]
    standardEdgeColumns = ["type", "amount", "unit", "name", "location", "database", "formula"]

    def __init__(self, importer: LCIImporter, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Preview")
        self.resize(600, 400)

        self.importer = importer

        layout = QtWidgets.QVBoxLayout(self)

        node_df = pd.DataFrame(importer.data)
        node_df["exchanges"] = node_df["exchanges"].apply(lambda x: len(x) if isinstance(x, list) else 0)
        node_df = node_df[
            [col for col in self.standardNodeColumns if col in node_df.columns] +
            [col for col in node_df.columns if col not in self.standardNodeColumns]
        ]

        self.node_model = core.ABTreeModel(node_df)
        self.node_view = widgets.ABTreeView()
        self.node_view.setModel(self.node_model)

        self.exchanges_model = core.ABTreeModel()
        self.exchanges_view = widgets.ABTreeView()
        self.exchanges_view.setModel(self.exchanges_model)
        self.exchanges_view.setHidden(True)

        self.node_view.clicked.connect(self.on_node_selected)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)

        layout.addWidget(self.node_view)
        layout.addWidget(self.exchanges_view)

        layout.addWidget(button_box)

    def on_node_selected(self, index: QtCore.QModelIndex):
        exchanges = self.importer.data[index.row()].get('exchanges', [])

        if not exchanges:
            self.exchanges_view.setHidden(True)
            return
        self.exchanges_view.setHidden(False)

        df = pd.DataFrame(exchanges)
        df = df[
            [col for col in self.standardEdgeColumns if col in df.columns] +
            [col for col in df.columns if col not in self.standardEdgeColumns]
        ]

        self.exchanges_model.set_dataframe(df)