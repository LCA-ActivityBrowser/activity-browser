# -*- coding: utf-8 -*-
import brightway2 as bw
from PyQt5 import QtCore, QtWidgets

from ..style import style_activity_tab
from ..tables import ExchangeTable
from ..widgets import ActivityDataGrid, DetailsGroupBox
from ...signals import signals


class ActivityTab(QtWidgets.QTabWidget):
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

    def __init__(self, activity_key, parent=None, read_only=True, db_read_only=True):
        super(ActivityTab, self).__init__(parent)
        self.parent = parent
        self.read_only = read_only
        self.db_read_only = db_read_only
        self.activity_key = activity_key
        self.activity = bw.get_activity(activity_key)

        # checkbox for enabling editing of activity, default=read-only
        self.edit_act_ch = QtWidgets.QCheckBox('Edit Activity', parent=self)
        self.edit_act_ch.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px;}")
        self.edit_act_ch.setChecked(not self.read_only)
        self.db_name = self.activity_key[0]
        self.edit_act_ch.clicked.connect(
            lambda checked: self.act_read_only_changed(read_only=not checked))

        self.db_read_only_changed(db_name=self.db_name, db_read_only=self.db_read_only)
        # activity-specific data as shown at the top
        self.activity_data_grid = ActivityDataGrid(read_only=self.read_only, parent=self)

        # exchange data shown after the activity data which it relates to, in tables depending on exchange type
        self.production = ExchangeTable(self, tableType="products")
        self.inputs = ExchangeTable(self, tableType="technosphere")
        self.flows = ExchangeTable(self, tableType="biosphere")
        self.upstream = ExchangeTable(self, tableType="technosphere")

        self.exchange_tables = [
            (self.production, "Products:"),
            (self.inputs, "Technosphere Inputs:"),
            (self.flows, "Biosphere flows:"),
            (self.upstream, "Downstream consumers:"),
        ]

        # arrange activity data and exchange data into desired vertical layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.addWidget(self.edit_act_ch)
        layout.addWidget(self.activity_data_grid)
        for table, label in self.exchange_tables:
            layout.addWidget(DetailsGroupBox(label, table))

        self.set_exchange_tables_read_only()

        layout.addStretch()
        layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(layout)

        self.populate(self.activity_key)

        self.update_tooltips()
        self.update_style()
        self.connect_signals()

    def populate(self, key):
        #  fill in the values of the ActivityTab widgets, excluding the ActivityDataGrid which is populated separately
        # todo: add count of results for each exchange table, to label above each table
        self.production.set_queryset(key[0], self.activity.production())
        self.inputs.set_queryset(key[0], self.activity.technosphere())
        self.flows.set_queryset(key[0], self.activity.biosphere())
        self.upstream.set_queryset(key[0], self.activity.upstream(), upstream=True)

    def act_read_only_changed(self, read_only):
        """ When read_only=False specific data fields in the tables below become editable
                When read_only=True these same fields become read-only"""
        self.read_only = read_only
        self.activity_data_grid.read_only = read_only
        self.activity_data_grid.set_activity_fields_read_only()
        self.set_exchange_tables_read_only()
        self.activity_data_grid.populate_database_combo(parent=self)

        self.update_tooltips()
        self.update_style()

    def set_exchange_tables_read_only(self):
        """the user should not be able to edit the exchange tables when read_only
                EditTriggers turned off to prevent DoubleClick editing
                DragDropMode set to NoDragDrop prevents exchanges dropped on the table to add"""

        for table, label in self.exchange_tables:
            if self.read_only:
                table.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
                table.setDragDropMode(QtWidgets.QTableWidget.NoDragDrop)
            else:
                table.setEditTriggers(QtWidgets.QTableWidget.DoubleClicked)
                table.setDragDropMode(QtWidgets.QTableWidget.DropOnly)

    def db_read_only_changed(self, db_name, db_read_only):
        """ If database of open activity is set to read-only, the read-only checkbox cannot now be unchecked by user """
        if db_name == self.activity_key[0]:
            self.db_read_only = db_read_only

            # if activity was editable, but now the database is read-only, read_only state must be changed to false.
            if not self.read_only and self.db_read_only:
                self.edit_act_ch.setChecked(False)
                self.act_read_only_changed(read_only=True)

            # update checkbox to greyed-out or not
            self.edit_act_ch.setEnabled(not self.db_read_only)
            self.update_tooltips()

        else:  # on read-only state change for a database different to the open activity...
            # update values in database list to ensure activity cannot be duplicated to read-only db
            self.activity_data_grid.populate_database_combo(parent=self)


    def update_tooltips(self):
        if self.db_read_only:
            self.edit_act_ch.setToolTip("The database this activity belongs to is read-only."
                                         " Enable database editing with checkbox in databases list")
        else:
            if self.read_only:
                self.edit_act_ch.setToolTip("Click to enable editing. Edits are saved automatically")
            else:
                self.edit_act_ch.setToolTip("Click to prevent further edits. Edits are saved automatically")

    def update_style(self):
        if self.read_only:
            self.setStyleSheet(style_activity_tab.style_sheet_read_only)
        else:
            self.setStyleSheet(style_activity_tab.style_sheet_editable)

    def update_activity_values(self, key, field, value):
        # ensures when user updates a field, the activityTab property is also updated (else de-synced)
        if key == self.activity_key:
            self.activity[field] = value

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.db_read_only_changed)
        signals.activity_modified.connect(self.update_activity_values)