# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore, QtWidgets

from ..tables import ExchangeTable
from ..widgets import ActivityDataGrid, DetailsGroupBox


class ActivityDetailsTab(QtWidgets.QWidget):
    """The data relating to Brightway activities can be viewed and edited through this panel interface
    The interface is a GUI representation of the standard activity data format as determined by Brightway
    This is necessitated as AB does not save its own data structures to disk
    Data format documentation is under the heading "The schema for an LCI dataset in voluptuous is:" at this link:
    https://docs.brightwaylca.org/intro.html#database-is-a-subclass-of-datastore
    Note that all activity data are optional.
    When activities contain exchanges, some fields are required (input, type, amount)
    Each exchange has a type: production, substitution, technosphere, or biosphere
    AB does not yet support 'substitution'. Other exchange types are shown in separate columns on this interface
    Required and other common exchange data fields are hardcoded as column headers in these tables
    More detail available at: https://docs.brightwaylca.org/intro.html#exchange-data-format
    The technosphere products (first table) of the visible activity are consumed by other activities downstream
    The final table of this tab lists these 'Downstream Consumers'
    """

    def __init__(self, parent=None, activity=None):
        super(ActivityDetailsTab, self).__init__(parent)
        self.parent = parent

        self.activity_data = ActivityDataGrid()

        self.production = ExchangeTable(self, tableType="products")
        self.inputs = ExchangeTable(self, tableType="technosphere")
        self.flows = ExchangeTable(self, tableType="biosphere")
        self.upstream = ExchangeTable(self, tableType="technosphere")

        tables = [
            (self.production, "Products:"),
            (self.inputs, "Technosphere Inputs:"),
            (self.flows, "Biosphere flows:"),
            (self.upstream, "Downstream consumers:"),
        ]

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.activity_data)
        for table, label in tables:
            layout.addWidget(DetailsGroupBox(label, table))

        layout.addStretch()
        layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(layout)

        if activity:
            self.populate(activity)

    def populate(self, key):
        self.activity = bw.get_activity(key)

        self.activity_data.populate(self.activity)
        self.production.set_queryset(key[0], self.activity.production())
        self.inputs.set_queryset(key[0], self.activity.technosphere())
        self.flows.set_queryset(key[0], self.activity.biosphere())
        self.upstream.set_queryset(key[0], self.activity.upstream(), upstream=True)

