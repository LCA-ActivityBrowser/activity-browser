# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore, QtWidgets

from ..tables import ExchangeTable
from ..widgets import ActivityDataGrid, DetailsGroupBox


class ActivityDetailsTab(QtWidgets.QWidget):
    def __init__(self, parent=None, activity=None):
        super(ActivityDetailsTab, self).__init__(parent)
        self.parent = parent

        self.details_widget = self.get_details_widget()

        vlayout = QtWidgets.QVBoxLayout()
        vlayout.setAlignment(QtCore.Qt.AlignTop)
        vlayout.addWidget(self.details_widget)

        self.setLayout(vlayout)

        if activity:
            self.populate(activity)

    def get_details_widget(self):
        self.production = ExchangeTable(self, production=True)
        self.inputs = ExchangeTable(self)
        self.flows = ExchangeTable(self, biosphere=True)
        self.upstream = ExchangeTable(self)

        layout = QtWidgets.QVBoxLayout()
        self.metadata = ActivityDataGrid()
        layout.addWidget(self.metadata)

        # splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        tables = [
            (self.production, "Products:"),
            (self.inputs, "Technosphere Inputs:"),
            (self.flows, "Biosphere flows:"),
            (self.upstream, "Downstream consumers:"),
        ]

        for table, label in tables:
            layout.addWidget(DetailsGroupBox(label, table))

        # layout.addWidget(splitter)
        layout.addStretch()
        widget = QtWidgets.QWidget(self)
        widget.setLayout(layout)

        return widget

    def populate(self, key):
        self.activity = bw.get_activity(key)

        self.production.set_queryset(key[0], self.activity.production())
        self.inputs.set_queryset(key[0], self.activity.technosphere())
        self.flows.set_queryset(key[0], self.activity.biosphere())
        self.upstream.set_queryset(key[0], self.activity.upstream(), upstream=True)
        self.metadata.populate(self.activity)
