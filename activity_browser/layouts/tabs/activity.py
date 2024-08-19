# -*- coding: utf-8 -*-
from copy import copy
from dataclasses import dataclass
from math import nan
from typing import Any, Optional, Union
from peewee import DoesNotExist
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Slot

from activity_browser import ab_settings, project_settings, signals
from activity_browser.bwutils import commontasks as bc
from activity_browser.logger import log
from activity_browser.mod import bw2data as bd
from activity_browser.ui.style import style_item

from ...ui.icons import qicons
from ...ui.style import style_activity_tab
from ...ui.tables import (
    BiosphereExchangeTable,
    DownstreamExchangeTable,
    ProductExchangeTable,
    TechnosphereExchangeTable,
)
from ...ui.tables.delegates import StringDelegate, FloatDelegate
from ...ui.widgets import ActivityDataGrid, DetailsGroupBox, SignalledPlainTextEdit
from ..panels.panel import ABTab


class ActivitiesTab(ABTab):
    """Tab that contains sub-tabs describing activity information."""

    def __init__(self, parent=None):
        super(ActivitiesTab, self).__init__(parent)
        self.setTabsClosable(True)
        self.connect_signals()

    def connect_signals(self):
        signals.unsafe_open_activity_tab.connect(self.unsafe_open_activity_tab)
        signals.safe_open_activity_tab.connect(self.safe_open_activity_tab)
        self.tabCloseRequested.connect(self.close_tab)
        signals.close_activity_tab.connect(self.close_tab_by_tab_name)
        bd.projects.current_changed.connect(self.close_all)

    @Slot(tuple, name="openActivityTab")
    def open_activity_tab(self, key: tuple, read_only: bool = True) -> None:
        """Opens new tab or focuses on already open one."""
        if key not in self.tabs:
            act = bd.get_activity(key)
            if act.get("type") not in bd.labels.node_types:
                return
            new_tab = ActivityTab(key, read_only, self)

            # If this is a new or duplicated activity then we want to exit it
            # ditto check the Technosphere and Biosphere tables
            if not read_only:
                for table in new_tab.grouped_tables:
                    if table.title() in ("Technosphere Flows:", "Biosphere Flows:"):
                        table.setChecked(True)
            self.tabs[key] = new_tab
            tab_index = self.addTab(new_tab, bc.get_activity_name(act, str_length=30))

            new_tab.destroyed.connect(
                lambda: self.tabs.pop(key) if key in self.tabs else None
            )
            new_tab.destroyed.connect(signals.hide_when_empty.emit)
            new_tab.objectNameChanged.connect(
                lambda name: self.setTabText(tab_index, name)
            )

        self.select_tab(self.tabs[key])
        signals.show_tab.emit("Activity Details")

    @Slot(tuple, name="unsafeOpenActivityTab")
    def unsafe_open_activity_tab(self, key: tuple) -> None:
        self.open_activity_tab(key, False)

    @Slot(tuple, name="safeOpenActivityTab")
    def safe_open_activity_tab(self, key: tuple) -> None:
        self.open_activity_tab(key)


class ActivityTab(QtWidgets.QWidget):
    """The data relating to Brightway activities can be viewed and edited through this panel interface
    The interface is a GUI representation of the standard activity data format as determined by Brightway
    This is necessitated as AB does not save its own data structures to disk
    Data format documentation is under the heading "The schema for an LCI dataset in voluptuous is:" at this link:
    https://2.docs.brightway.dev/intro.html#database-is-a-subclass-of-datastore
    Note that all activity data are optional.
    When activities contain exchanges, some fields are required (input, type, amount)
    Each exchange has a type: production, substitution, technosphere, or biosphere
    AB does not yet support 'substitution'. Other exchange types are shown in separate columns on this interface
    Required and other common exchange data fields are hardcoded as column headers in these tables
    More detail available at: https://2.docs.brightway.dev/intro.html#exchange-data-format
    The technosphere products (first table) of the visible activity are consumed by other activities downstream
    The final table of this tab lists these 'Downstream Consumers'
    """

    def __init__(self, key: tuple, read_only=True, parent=None):
        super(ActivityTab, self).__init__(parent)
        self.read_only = read_only
        self.db_read_only = project_settings.db_is_readonly(db_name=key[0])
        self.key = key
        self.db_name = key[0]
        self.activity = bd.get_activity(key)
        self.database = bd.Database(self.db_name)

        # Edit Activity checkbox
        self.checkbox_edit_act = QtWidgets.QCheckBox("Edit Activity")
        self.checkbox_edit_act.setChecked(not self.read_only)
        self.checkbox_edit_act.toggled.connect(self.act_read_only_changed)

        # Activity Description
        self.activity_description = SignalledPlainTextEdit(
            key=key,
            field="comment",
            parent=self,
        )

        # Activity Description checkbox
        self.checkbox_activity_description = QtWidgets.QCheckBox(
            "Description", parent=self
        )
        self.checkbox_activity_description.clicked.connect(
            self.toggle_activity_description_visibility
        )
        self.checkbox_activity_description.setChecked(not self.read_only)
        self.checkbox_activity_description.setToolTip(
            "Show/hide the activity description"
        )
        self.toggle_activity_description_visibility()

        # Reveal/hide uncertainty columns
        self.checkbox_uncertainty = QtWidgets.QCheckBox("Uncertainty")
        self.checkbox_uncertainty.setToolTip("Show/hide the uncertainty columns")
        self.checkbox_uncertainty.setChecked(False)
        self.checkbox_uncertainty.toggled.connect(self.show_exchange_uncertainty)

        # Reveal/hide exchange comment columns
        self.checkbox_comment = QtWidgets.QCheckBox("Comments")
        self.checkbox_comment.setToolTip("Show/hide the comment column")
        self.checkbox_comment.setChecked(False)
        self.checkbox_comment.toggled.connect(self.show_comments)

        # Toolbar Layout
        toolbar = QtWidgets.QToolBar()
        self.graph_action = toolbar.addAction(
            qicons.graph_explorer, "Show in Graph Explorer", self.open_graph
        )
        toolbar.addWidget(self.checkbox_edit_act)
        toolbar.addWidget(self.checkbox_activity_description)
        toolbar.addWidget(self.checkbox_uncertainty)
        toolbar.addWidget(self.checkbox_comment)
        # Align the properties button to the right
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )
        toolbar.addWidget(spacer)
        toolbar.addAction("Properties", self.open_properties)

        # Activity information
        # this contains: activity name, location, database
        self.activity_data_grid = ActivityDataGrid(
            read_only=self.read_only, parent=self
        )
        self.db_read_only_changed(db_name=self.db_name, db_read_only=self.db_read_only)

        # Exchange tables
        self.production = ProductExchangeTable(self)
        self.technosphere = TechnosphereExchangeTable(self)
        self.biosphere = BiosphereExchangeTable(self)
        self.downstream = DownstreamExchangeTable(self)

        self.exchange_groups = [
            DetailsGroupBox("Products:", self.production),
            DetailsGroupBox("Technosphere Flows:", self.technosphere),
            DetailsGroupBox("Biosphere Flows:", self.biosphere),
            DetailsGroupBox("Downstream Consumers:", self.downstream),
        ]
        self.exchange_groups[-1].setChecked(False)  # hide Downstream table by default

        self.group_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        for group in self.exchange_groups:
            self.group_splitter.addWidget(group)
        if state := ab_settings.settings.get("activity_table_layout", None):
            self.group_splitter.restoreState(bytearray.fromhex(state))

        # Full layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 4, 1)
        layout.setAlignment(QtCore.Qt.AlignTop)

        layout.addWidget(toolbar)
        layout.addWidget(self.activity_data_grid)
        layout.addWidget(self.activity_description)
        layout.addWidget(self.group_splitter)

        self.setLayout(layout)

        self.exchange_tables_read_only_changed()
        self.populate()
        self.update_tooltips()
        self.update_style()
        self.connect_signals()

        # Make the activity tab editable in case it's new
        if not self.read_only:
            self.act_read_only_changed(True)

    def connect_signals(self):
        signals.database_read_only_changed.connect(self.db_read_only_changed)
        self.activity.changed.connect(self.populate)
        self.activity.deleted.connect(self.deleteLater)
        bd.parameters.parameters_changed.connect(self.populate)

        self.group_splitter.splitterMoved.connect(self.save_splitter_state)

    @Slot(name="openGraph")
    def open_graph(self) -> None:
        signals.open_activity_graph_tab.emit(self.key)

    @Slot(name="populatePage")
    def populate(self) -> None:
        """Populate the various tables and boxes within the Activity Detail tab"""
        if self.db_name in bd.databases:
            # Avoid a weird signal interaction in the tests
            try:
                self.activity = bd.get_activity(self.key)  # Refresh activity.
            except DoesNotExist:
                signals.close_activity_tab.emit(self.key)
                return
        self.populate_description_box()

        # update the object name to be the activity name
        self.setObjectName(self.activity["name"])

        # fill in the values of the ActivityTab widgets, excluding the ActivityDataGrid which is populated separately
        # todo: add count of results for each exchange table, to label above each table
        self.production.model.load(self.activity.production())
        self.technosphere.model.load(self.activity.technosphere())
        self.biosphere.model.load(self.activity.biosphere())
        self.downstream.model.load(self.activity.upstream())

        self.show_exchange_uncertainty(self.checkbox_uncertainty.isChecked())
        self.show_comments(self.checkbox_comment.isChecked())

    def populate_description_box(self):
        """Populate the activity description."""
        self.activity_description.refresh_text(self.activity.get("comment", ""))
        self.activity_description.setReadOnly(self.read_only)

    @Slot(name="toggleDescription")
    def toggle_activity_description_visibility(self) -> None:
        """Show only if checkbox is checked."""
        self.activity_description.setVisible(
            self.checkbox_activity_description.isChecked()
        )

    @Slot(bool, name="toggleUncertaintyColumns")
    def show_exchange_uncertainty(self, toggled: bool) -> None:
        self.technosphere.show_uncertainty(toggled)
        self.biosphere.show_uncertainty(toggled)

    @Slot(bool, name="toggleCommentColumn")
    def show_comments(self, toggled: bool) -> None:
        self.technosphere.show_comments(toggled)
        self.biosphere.show_comments(toggled)

    @Slot(bool, name="toggleReadOnly")
    def act_read_only_changed(self, read_only: bool) -> None:
        """When read_only=False specific data fields in the tables below become user-editable
        When read_only=True these same fields become read-only"""
        self.read_only = not read_only
        self.activity_description.setReadOnly(self.read_only)

        if (
            not self.read_only
        ):  # update unique locations, units, etc. for editing (metadata)
            signals.edit_activity.emit(self.db_name)

        self.activity_data_grid.set_activity_fields_read_only(read_only=self.read_only)
        self.activity_data_grid.populate_database_combo()
        self.exchange_tables_read_only_changed()

        self.update_tooltips()
        self.update_style()

    def exchange_tables_read_only_changed(self) -> None:
        """The user should not be able to edit the exchange tables when read_only

        EditTriggers turned off to prevent DoubleClick-selection editing.
        DragDropMode set to NoDragDrop prevents exchanges dropped on the table to add.
        """
        for table in [
            self.production,
            self.technosphere,
            self.biosphere,
            self.downstream,
        ]:
            if self.read_only:
                table.setEditTriggers(QtWidgets.QTableView.NoEditTriggers)
                table.setAcceptDrops(False)
                table.delete_exchange_action.setEnabled(False)
                table.remove_formula_action.setEnabled(False)
                table.modify_uncertainty_action.setEnabled(False)
                table.remove_uncertainty_action.setEnabled(False)
                table.setSelectionMode(table.NoSelection)
            else:
                table.setEditTriggers(QtWidgets.QTableView.DoubleClicked)
                table.delete_exchange_action.setEnabled(True)
                table.remove_formula_action.setEnabled(True)
                table.modify_uncertainty_action.setEnabled(True)
                table.remove_uncertainty_action.setEnabled(True)
                table.setSelectionMode(table.SingleSelection)
                if (
                    not table.downstream
                ):  # downstream consumers table never accepts drops
                    table.setAcceptDrops(True)

    @Slot(str, bool, name="dbReadOnlyToggle")
    def db_read_only_changed(self, db_name: str, db_read_only: bool) -> None:
        """If database of open activity is set to read-only, the read-only checkbox cannot now be unchecked by user"""
        if db_name == self.db_name:
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

    def update_tooltips(self) -> None:
        if self.db_read_only:
            self.checkbox_edit_act.setToolTip(
                "The database this activity belongs to is read-only."
                " Enable database editing with checkbox in databases list"
            )
        else:
            if self.read_only:
                self.checkbox_edit_act.setToolTip(
                    "Click to enable editing. Edits are saved automatically"
                )
            else:
                self.checkbox_edit_act.setToolTip(
                    "Click to prevent further edits. Edits are saved automatically"
                )

    def update_style(self) -> None:
        if self.read_only:
            self.setStyleSheet(style_activity_tab.style_sheet_read_only)
        else:
            self.setStyleSheet(style_activity_tab.style_sheet_editable)

    def save_splitter_state(self):
        ab_settings.settings["activity_table_layout"] = bytearray(
            self.group_splitter.saveState()
        ).hex()
        ab_settings.write_settings()

    def open_properties(self):
        """Opens the property editor for the current activity"""
        editor = PropertyEditor(self.activity.get("properties"), self.read_only, self)
        # Do not save the changes if the user pressed cancel
        if editor.exec_() == editor.Accepted:
            old_properties = self.activity.get("properties")
            # Get the values modified by the user
            updated_properties = editor.properties()
            # Nothing to do
            if not old_properties and not updated_properties:
                return
            # The user has deleted all properties
            elif old_properties and not updated_properties:
                del self.activity["properties"]
            # There were no properties and the user created some
            elif not old_properties and updated_properties:
                self.activity["properties"] = updated_properties
            else:
                # Properties changed, merge the values, to avoid reordering
                # the unmodified properties
                for property in list(old_properties.keys()):
                    if not property in updated_properties:
                        del old_properties[property]
                old_properties |= updated_properties
            self.activity.save()


class PropertyModel(QtCore.QAbstractTableModel):
    """
    Model for the property editor table
    The data is (str, float).
    """

    @dataclass
    class PropertyData:
        """Dataclass to represent one row with correct typehints"""
        key: str = ""
        value: float = 0

        def __getitem__(self, index: int) -> Union[str, float]:
            """x[k] operator for easier usage"""
            if index == 0:
                return self.key
            elif index == 1:
                return self.value
            raise IndexError

        def __setitem__(self, index: int, value: Union[str, float]):
            """x[k]=v operator for easier usage"""
            if index == 0:
                if not isinstance(value, str):
                    raise TypeError
                self.key = value
            elif index == 1:
                if not isinstance(value, float):
                    raise TypeError
                self.value = value
            else:
                raise IndexError


    def __init__(self, read_only: bool):
        super().__init__()
        self._data: list[PropertyModel.PropertyData] = []
        self._read_only = read_only

    def populate(self, data: Optional[dict[str, float]]) -> None:
        self._data.clear()
        log.info(f"Input data for property table: {data}")
        if data is not None:
            self._original_data = copy(data)
            for key in data:
                self._data.append(PropertyModel.PropertyData(key, data[key]))
        else:
            self._original_data = dict()
        self._data.append(PropertyModel.PropertyData())
        self.layoutChanged.emit()

    def data(self, index: QtCore.QModelIndex,
             role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
        if index.isValid():
            if role == QtCore.Qt.ItemDataRole.EditRole:
                return self._data[index.row()][index.column()]
            elif (role == QtCore.Qt.ItemDataRole.DisplayRole
                    or role == QtCore.Qt.ItemDataRole.ToolTipRole):
                # Do not show values for properties which have no name
                # to hint that these will not be saved
                if (index.column() == 1 and self._data[index.row()][0] == ""):
                    return nan

                return self._data[index.row()][index.column()]
            if role == QtCore.Qt.ItemDataRole.ForegroundRole:

                if self._original_data.get(self._data[index.row()].key) == self._data[index.row()].value:
                    return None
                return style_item.brushes.get("modified")
        return None

    def setData(self, index: QtCore.QModelIndex, value: Any,
             role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> bool:
        if index.isValid() and role == QtCore.Qt.ItemDataRole.EditRole:
            if self._data[index.row()][index.column()] != value:
                self._data[index.row()][index.column()] = value
                self.dataChanged.emit(index, index, [])
            # Make sure there is an empty row at the end
            if self._data[-1][0] != "":
                self._data.append(PropertyModel.PropertyData())
                self.layoutChanged.emit()

            return True
        return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        result = (QtCore.Qt.ItemFlag.ItemIsSelectable
                  | QtCore.Qt.ItemFlag.ItemIsEnabled) 
        if not self._read_only:
            result |= QtCore.Qt.ItemFlag.ItemIsEditable
        return result
    
    def rowCount(self, index: int) -> int:
        return len(self._data)

    def columnCount(self, index: int) -> int:
        return 2

    def headerData(self, section:int, orientation:QtCore.Qt.Orientation,
                   role: int=QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
        if (orientation == QtCore.Qt.Orientation.Horizontal
                and role == QtCore.Qt.ItemDataRole.DisplayRole):
            return ("Name", "Value")[section]
        return None

    def get_data_table(self) -> dict[str, float]:
        result = { item.key:item.value for item in self._data if item.key != ""}
        return result

    def has_duplicate_key(self) -> bool:
        key_set = {item.key for item in self._data}
        return len(key_set) < len(self._data)


class PropertyTable(QtWidgets.QTableView):
    """Table view for editing properties"""
    def __init__(self, model: PropertyModel, parent=None):
        super().__init__(parent)
        self.setVerticalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setHorizontalScrollMode(QtWidgets.QTableView.ScrollPerPixel)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        self.setWordWrap(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked |
            QtWidgets.QAbstractItemView.EditTrigger.SelectedClicked |
            QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed |
            QtWidgets.QAbstractItemView.EditTrigger.AnyKeyPressed
        )

        self.setItemDelegateForColumn(0, StringDelegate(self))
        # Use FloatDelegate, so that int values do not trigger an int validation
        self.setItemDelegateForColumn(1, FloatDelegate(self))

        self._model = model
        self.setModel(self._model)

    def populate(self, data: Optional[dict]) -> None:
        self._model.populate(data)


class PropertyEditor(QtWidgets.QDialog):
    """Property editor dialog"""

    def __init__(self, properties: Optional[dict[str, float]], read_only: bool, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Property Editor")
        self._data_model = PropertyModel(read_only)
        if not read_only:
            self._data_model.dataChanged.connect(self._handle_data_changed)
        self._editor_table = PropertyTable(self._data_model)
        self._editor_table.populate(properties)
        self._save_button = QtWidgets.QPushButton()
        if read_only:
            self._save_button.setText("Read only")
        else:
            self._save_button.setText("No changes yet")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self.accept)
        cancel_button = QtWidgets.QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        # Prevent hitting enter in the table from closing the dialog
        self._save_button.setAutoDefault(False)
        cancel_button.setAutoDefault(False)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._editor_table)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self._save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def properties(self) -> dict[str, float]:
        """Access method to get the result of the editing"""
        return self._data_model.get_data_table()

    def _handle_data_changed(self):
        if self._data_model.has_duplicate_key():
            self._save_button.setText("Duplicate keys")
            self._save_button.setEnabled(False)
        else:
            self._save_button.setText("Save changes")
            self._save_button.setEnabled(True)



