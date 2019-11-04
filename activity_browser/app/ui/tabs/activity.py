# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Slot

from ..style import style_activity_tab
from ..tables import (BiosphereExchangeTable, DownstreamExchangeTable,
                      ProductExchangeTable, TechnosphereExchangeTable)
from ..widgets import ActivityDataGrid, DetailsGroupBox, SignalledPlainTextEdit
from ..panels import ABTab
from ..icons import qicons
from ...bwutils import commontasks as bc
from ...settings import project_settings
from ...signals import signals


class ActivitiesTab(ABTab):
    """Tab that contains sub-tabs describing activity information."""
    def __init__(self, parent=None):
        super(ActivitiesTab, self).__init__(parent)
        self.setTabsClosable(True)
        self.connect_signals()

    def connect_signals(self):
        signals.open_activity_tab.connect(self.open_activity_tab)
        signals.activity_modified.connect(self.update_activity_name)
        self.tabCloseRequested.connect(self.close_tab)
        signals.delete_activity.connect(self.close_tab_by_tab_name)
        signals.project_selected.connect(self.close_all)

    @Slot(tuple)
    def open_activity_tab(self, key: tuple) -> None:
        """Opens new tab or focuses on already open one."""
        if key not in self.tabs:
            act = bw.get_activity(key)
            if not bc.is_technosphere_activity(act):
                return
            new_tab = ActivityTab(key)
            self.tabs[key] = new_tab
            self.addTab(new_tab, bc.get_activity_name(act, str_length=30))

            # hovering on the tab shows the full name, in case it's truncated in the tabbar at the top
            # new_tab.setToolTip(bw.get_activity(key).as_dict()['name'])

        self.select_tab(self.tabs[key])
        signals.show_tab.emit("Activities")

    def update_activity_name(self, key, field, value):
        if key in self.tabs and field == 'name':
            try:
                index = self.indexOf(self.tabs[key])
                self.setTabText(index, value)
            except:
                pass


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

    def __init__(self, key, parent=None, read_only=True):
        super(ActivityTab, self).__init__(parent)
        self.read_only = read_only
        self.db_read_only = project_settings.db_is_readonly(db_name=key[0])
        self.key = key
        self.db_name = self.key[0]
        self.activity = bw.get_activity(key)

        # Edit Activity checkbox
        self.checkbox_edit_act = QtWidgets.QCheckBox('Edit Activity', parent=self)
        self.checkbox_edit_act.setChecked(not self.read_only)
        self.db_name = self.key[0]
        self.checkbox_edit_act.clicked.connect(self.act_read_only_changed)

        # Activity Description
        self.activity_description = SignalledPlainTextEdit(
            key=getattr(self.activity, "key", None),
            field="comment",
            parent=self,
        )

        # Activity Description checkbox
        self.checkbox_activity_description = QtWidgets.QCheckBox('Description', parent=self)
        self.checkbox_activity_description.clicked.connect(self.toggle_activity_description_visibility)
        # self.checkbox_description.setStyleSheet("QCheckBox::indicator { width: 20px; height: 20px;}")
        self.checkbox_activity_description.setChecked(not self.read_only)
        self.toggle_activity_description_visibility()

        self.db_read_only_changed(db_name=self.db_name, db_read_only=self.db_read_only)

        # Toolbar Layout
        toolbar = QtWidgets.QToolBar()
        toolbar.addWidget(self.checkbox_edit_act)
        toolbar.addWidget(self.checkbox_activity_description)
        self.graph_action = toolbar.addAction(
            qicons.graph_explorer, "Show graph", self.open_graph
        )

        # activity-specific data displayed and editable near the top of the tab
        self.activity_data_grid = ActivityDataGrid(read_only=self.read_only, parent=self)

        # 4 data tables displayed after the activity data
        self.production = ProductExchangeTable(self)
        self.technosphere = TechnosphereExchangeTable(self)
        self.biosphere = BiosphereExchangeTable(self)
        self.downstream = DownstreamExchangeTable(self)

        self.exchange_tables = [
            ("Products:", self.production),
            ("Technosphere Inputs:", self.technosphere),
            ("Biosphere Flows:", self.biosphere),
            ("Downstream Consumers:", self.downstream),
        ]
        self.grouped_tables = [DetailsGroupBox(l, t) for l, t in self.exchange_tables]
        # arrange activity data and exchange data into vertical layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.addWidget(toolbar)
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(self.activity_description)
        for group_box in self.grouped_tables:
            layout.addWidget(group_box)

        self.exchange_tables_read_only_changed()

        layout.addStretch()
        layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(layout)

        self.populate()
        # Hide the downstream table by default
        self.grouped_tables[-1].setChecked(False)
        self.update_tooltips()
        self.update_style()
        self.connect_signals()

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.db_read_only_changed)
        signals.database_changed.connect(self.populate)
        signals.parameters_changed.connect(self.populate)
        # signals.activity_modified.connect(self.update_activity_values)

    @Slot()
    def open_graph(self):
        signals.open_activity_graph_tab.emit(self.key)

    def populate(self):
        #  fill in the values of the ActivityTab widgets, excluding the ActivityDataGrid which is populated separately
        # todo: add count of results for each exchange table, to label above each table
        self.production.sync(self.activity.production())
        self.technosphere.sync(self.activity.technosphere())
        self.biosphere.sync(self.activity.biosphere())
        self.downstream.sync(self.activity.upstream())

        # Potentially update `DetailsGroupBox` now that tables are populated
        for _, table in self.exchange_tables:
            table.updated.emit()

        self.populate_description_box()

    def populate_description_box(self):
        # activity description
        self.activity_description.setPlainText(self.activity.get('comment', ''))
        self.activity_description.setReadOnly(self.read_only)
        self.activity_description._key = self.activity.key

        # the <font> html-tag has no effect besides making the tooltip rich text
        # this is required for line breaks of long comments
        self.checkbox_activity_description.setToolTip(
            '<font>{}</font>'.format(self.activity_description.toPlainText())
        )
        self.activity_description._before = self.activity.get('comment', '')
        # self.activity_description.adjust_size()

    def toggle_activity_description_visibility(self):
        """Show only if checkbox is checked."""
        self.activity_description.setVisible(self.checkbox_activity_description.isChecked())

    def act_read_only_changed(self, read_only):
        """ When read_only=False specific data fields in the tables below become user-editable
                When read_only=True these same fields become read-only"""
        self.read_only = not read_only
        self.activity_description.setReadOnly(self.read_only)

        if not self.read_only:  # update unique locations, units, etc. for editing (metadata)
            signals.edit_activity.emit(self.db_name)

        self.activity_data_grid.set_activity_fields_read_only(read_only=self.read_only)
        self.activity_data_grid.populate_database_combo()
        self.exchange_tables_read_only_changed()

        self.update_tooltips()
        self.update_style()

    def exchange_tables_read_only_changed(self):
        """the user should not be able to edit the exchange tables when read_only
                EditTriggers turned off to prevent DoubleClick-selection editing
                DragDropMode set to NoDragDrop prevents exchanges dropped on the table to add"""

        for label, table in self.exchange_tables:
            if self.read_only:
                table.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)
                table.setAcceptDrops(False)
                table.delete_exchange_action.setEnabled(False)
                table.remove_formula_action.setEnabled(False)
            else:
                table.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
                table.delete_exchange_action.setEnabled(True)
                table.remove_formula_action.setEnabled(True)
                if not table.downstream:  # downstream consumers table never accepts drops
                    table.setAcceptDrops(True)

    def db_read_only_changed(self, db_name, db_read_only):
        """ If database of open activity is set to read-only, the read-only checkbox cannot now be unchecked by user """
        if db_name == self.key[0]:
            self.db_read_only = db_read_only

            # if activity was editable, but now the database is read-only, read_only state must be changed to false.
            if not self.read_only and self.db_read_only:
                self.checkbox_edit_act.setChecked(False)
                self.act_read_only_changed(read_only=True)

            # update checkbox to greyed-out or not
            self.checkbox_edit_act.setEnabled(not self.db_read_only)
            self.update_tooltips()

        else:  # on read-only state change for a database different to the open activity...
            # update values in database list to ensure activity cannot be duplicated to read-only db
            self.activity_data_grid.populate_database_combo()

    def update_tooltips(self):
        if self.db_read_only:
            self.checkbox_edit_act.setToolTip("The database this activity belongs to is read-only."
                                         " Enable database editing with checkbox in databases list")
        else:
            if self.read_only:
                self.checkbox_edit_act.setToolTip("Click to enable editing. Edits are saved automatically")
            else:
                self.checkbox_edit_act.setToolTip("Click to prevent further edits. Edits are saved automatically")

    def update_style(self):
        if self.read_only:
            self.setStyleSheet(style_activity_tab.style_sheet_read_only)
        else:
            self.setStyleSheet(style_activity_tab.style_sheet_editable)

    # def update_activity_values(self, key, field, value):
    #     """Update activity values."""
    #     if key == self.key:
    #         self.activity[field] = value

