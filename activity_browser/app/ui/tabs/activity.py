# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore, QtWidgets

from ..tables import ExchangeTable
from ..widgets import ActivityDataGrid, DetailsGroupBox


class ActivityTab(QtWidgets.QWidget):
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

    def __init__(self, parent=None, activity=None, read_only=True):
        super(ActivityTab, self).__init__(parent)
        self.parent = parent
        self.read_only = read_only
        # checkbox for enabling editing of activity, default=read-only
        # lambda for user-check defined in Populate function, after required variables are in scope
        self.read_only_ch = QtWidgets.QCheckBox('Read-Only', parent=self)
        self.read_only_ch.setChecked(self.read_only)

        # activity-specific data as shown at the top
        self.activity_data = ActivityDataGrid(read_only=self.read_only)

        # exchange data shown after the activity data which it relates to, in tables depending on exchange type
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

        # arrange activity data and exchange data into desired vertical layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.read_only_ch)
        layout.addWidget(self.activity_data)
        for table, label in tables:
            if read_only:
                table.setEnabled(False)
            layout.addWidget(DetailsGroupBox(label, table))

        layout.addStretch()
        layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(layout)

        if activity:
            self.populate(activity)

    def populate(self, key):
        self.activity = bw.get_activity(key)

        self.read_only_ch.clicked.connect(
            lambda checked, key=self.activity.key: self.readOnlyStateChanged(checked, key))

        self.activity_data.populate(self.activity)
        # todo: add count of results for each exchange table, to label above each table
        self.production.set_queryset(key[0], self.activity.production())
        self.inputs.set_queryset(key[0], self.activity.technosphere())
        self.flows.set_queryset(key[0], self.activity.biosphere())
        self.upstream.set_queryset(key[0], self.activity.upstream(), upstream=True)

    def readOnlyStateChanged(self, checked, key):
        """
        When checked=False specific data fields in the tables below become editable
        When checked=True these same fields become read-only
        """
        print("ro state change hit for:", checked, key)
        ActivityDataGrid.set_activity_fields_read_only(self.activity_data, read_only=checked)
        self.set_exchange_tables_read_only(read_only=checked)
        #todo: save RO state to file

    def set_exchange_tables_read_only(self, read_only=True):
        self.read_only = read_only
        # user cannot edit these fields if they are read-only
        self.production.setEnabled(not self.read_only)
        self.inputs.setEnabled(not self.read_only)
        self.flows.setEnabled(not self.read_only)
        self.upstream.setEnabled(not self.read_only)
