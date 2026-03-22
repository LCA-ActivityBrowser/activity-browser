from qtpy import QtWidgets, QtCore, QtGui

import pandas as pd

from bw2io.importers.base_lci import LCIImporter

from activity_browser.ui import widgets, core

from .node_tab import ImportPreviewNodeTab
from .edge_tab import ImportPreviewEdgeTab


class ImportPreviewDialog(QtWidgets.QDialog):
    def __init__(self, importer: LCIImporter, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Preview")
        self.resize(600, 400)

        self.importer = importer
        self.tabs = QtWidgets.QTabWidget(self)

        self.node_tab = ImportPreviewNodeTab(importer, self)
        self.edge_tab = ImportPreviewEdgeTab(importer, self)

        self.tabs.addTab(self.node_tab, "Nodes")
        self.tabs.addTab(self.edge_tab, "Edges")

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
