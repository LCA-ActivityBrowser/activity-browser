# -*- coding: utf-8 -*-
from qtpy import QtCore, QtWidgets
from bw_functional import allocation_strategies, list_available_properties
from logging import getLogger

from activity_browser import actions, project_settings, signals
from activity_browser.actions.activity.activity_redo_allocation import MultifunctionalProcessRedoAllocation
from activity_browser.ui.style import style_item
from activity_browser.ui.widgets.custom_allocation_editor import CustomAllocationEditor

from ...bwutils import AB_metadata
from ..icons import qicons
from .line_edit import SignalledComboEdit, SignalledLineEdit

log = getLogger(__name__)


class DetailsGroupBox(QtWidgets.QGroupBox):
    def __init__(self, label, widget):
        super().__init__(label)
        self.widget = widget
        self.setCheckable(True)
        self.toggled.connect(self.showhide)
        self.setChecked(True)
        self.setStyleSheet("QGroupBox { border: none; }")
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(widget)
        layout.setContentsMargins(0, 22, 0, 5)
        self.setLayout(layout)
        if isinstance(self.widget, QtWidgets.QTableWidget):
            self.widget.itemChanged.connect(self.toggle_empty_table)
        # The model will have an 'updated' signal that is emitted whenever
        # a change is made to the underlying data.
        if hasattr(self.widget, "model"):
            self.widget.model.updated.connect(self.toggle_empty_table)

    @QtCore.Slot(name="showHideTable")
    def showhide(self):
        return
        self.widget.setVisible(self.isChecked())
        if not self.isChecked():
            minimum_height = self.minimumSizeHint().height()
            self.setMaximumHeight(minimum_height)
        else:
            self.setMaximumHeight(16777215)  # apparently this is the Qt default

    @QtCore.Slot(name="toggleEmptyTable")
    def toggle_empty_table(self) -> None:
        self.setChecked(True) # Disable hidden tables for now


class ActivityDataGrid(QtWidgets.QWidget):
    """Displayed at the top of each activity panel to show the user basic data related to the activity
    Expects to find the following data for each activity displayed: name, location, database
    Includes the read-only checkbox which enables or disables user-editing of some activity and exchange data
    Exchange data is displayed separately, below this grid, in tables.
    """
    DATABASE_DEFINED_ALLOCATION = "(database default)"
    CUSTOM_ALLOCATION = "Custom..."


    def __init__(self, parent, read_only=True):
        super(ActivityDataGrid, self).__init__(parent)

        self.read_only = read_only
        self.parent = parent

        self.name_box = SignalledLineEdit(
            key=parent.key,
            field="name",
            parent=self,
        )
        # self.name_box.setPlaceholderText("Activity name")

        # location combobox
        self.location_combo = SignalledComboEdit(
            key=parent.key,
            field="location",
            parent=self,
            contents=self._get_location(),
        )
        self.location_combo.setToolTip(
            "Select an existing location from the current activity database."
            " Or add new location"
        )
        self.location_combo.setEditable(
            True
        )  # always 'editable', but not always 'enabled'

        # database label
        self.database_label = QtWidgets.QLabel("Database")
        self.database_label.setToolTip(
            "Select a different database to duplicate activity to it"
        )

        # database combobox
        # the database of the activity is shown as a dropdown (ComboBox), which enables user to change it
        self.database_combo = QtWidgets.QComboBox()
        self.database_combo.currentTextChanged.connect(
            lambda target_db: self.duplicate_confirm_dialog(target_db)
        )
        self.database_combo.setToolTip(
            "Use dropdown menu to duplicate activity to another database"
        )

        # Default allocation combobox
        self._def_alloc_label = QtWidgets.QLabel("Default Allocation")
        self._def_alloc_combo = QtWidgets.QComboBox()
        self._def_alloc_combo.currentTextChanged.connect(self._handle_def_alloc_changed)
        self._def_alloc_combo.setToolTip(
            "Use dropdown menu to change the default allocation"
        )

        # arrange widgets for display as a grid
        self.grid = QtWidgets.QGridLayout()

        self.setContentsMargins(0, 0, 0, 0)
        self.grid.setContentsMargins(5, 5, 0, 5)
        self.grid.setSpacing(6)
        self.grid.setAlignment(QtCore.Qt.AlignTop)

        self.grid.addWidget(QtWidgets.QLabel("Name"), 1, 1)
        self.grid.addWidget(self.name_box, 1, 2, 1, 3)
        self.grid.addWidget(QtWidgets.QLabel("Location"), 2, 1)
        self.grid.addWidget(self.location_combo, 2, 2, 1, -1)
        self.grid.addWidget(self.database_combo, 3, 2, 1, -1)
        self.grid.addWidget(self.database_label, 3, 1)

        self.grid.addWidget(self._def_alloc_label, 4, 1)
        self.grid.addWidget(self._def_alloc_combo, 4, 2, 1, -1)

        self.setLayout(self.grid)

        self.populate()

        # do not allow user to edit fields if the ActivityDataGrid is read-only
        self.set_activity_fields_read_only()
        self.connect_signals()

    def connect_signals(self):
        signals.edit_activity.connect(self.update_location_combo)

    def populate(self):
        # fill in the values of the ActivityDataGrid widgets
        self.name_box.setText(self.parent.activity.get("name", ""))
        self.name_box._key = self.parent.activity.key

        self.populate_location_combo()
        self.populate_database_combo()
        self.populate_def_alloc_combo()


    def _get_location(self) -> str:
        location = str(self.parent.activity.get("location", "unknown"))
        if location == "":
            location = "unknown"
        return location

    def populate_location_combo(self):
        """acts as both of: a label to show current location of act, and
        auto-completes with all other locations in the database, to enable selection"""
        self.location_combo.blockSignals(True)
        location = self._get_location()
        # If the entry is not yet added
        if self.location_combo.findText(location) < 0:
            self.location_combo.addItem(location)
        self.location_combo.setCurrentText(location)
        self.location_combo.blockSignals(False)

    def update_location_combo(self):
        """Update when in edit mode"""
        self.location_combo.blockSignals(True)
        location = self._get_location()
        self.location_combo._before = location

        # get all locations in db
        self.location_combo.clear()
        db = self.parent.activity.get("database", "")
        locations = sorted(AB_metadata.get_locations(db))
        if "unknown" not in locations:
            locations.append("unknown")
        self.location_combo.clear()
        self.location_combo.insertItems(0, locations)
        self.location_combo.setCurrentIndex(locations.index(location))
        self.location_combo.blockSignals(False)

    def populate_database_combo(self):
        """acts as both: a label to show current db of act, and
        allows copying to others editable dbs via populated drop-down list"""
        # clear any existing items first
        self.database_combo.blockSignals(True)
        self.database_combo.clear()

        # first item in db combo, shown by default, is the current database
        current_db = self.parent.activity.get("database", "Error: db of Act not found")
        self.database_combo.addItem(current_db)

        # other items are the dbs that the activity can be duplicated to: find them and add
        available_target_dbs = list(project_settings.get_editable_databases())
        if current_db in available_target_dbs:
            available_target_dbs.remove(current_db)

        for db_name in available_target_dbs:
            self.database_combo.addItem(qicons.duplicate_activity, db_name)
        self.database_combo.blockSignals(False)

    def is_multifunctional(self) -> bool:
        return self.parent.activity.get("type") == "multifunctional"

    def populate_def_alloc_combo(self):
        self._def_alloc_label.setVisible(self.is_multifunctional())
        self._def_alloc_combo.setVisible(self.is_multifunctional())
        self._refresh_def_alloc_combo_values()

    def duplicate_confirm_dialog(self, target_db):
        actions.ActivityDuplicateToDB.run([self.parent.activity], target_db)
        # change selected database item back to original (index=0), to avoid confusing user
        # block and unblock signals to prevent unwanted extra emits from the automated change
        self.database_combo.blockSignals(True)
        self.database_combo.setCurrentIndex(0)
        self.database_combo.blockSignals(False)

    def set_activity_fields_read_only(self, read_only=True):
        """called on init after widgets instantiated
        also whenever a user clicks the read-only checkbox"""
        # user cannot edit these fields if they are read-only
        self.read_only = read_only
        self.name_box.setReadOnly(self.read_only)
        self.location_combo.setEnabled(not self.read_only)
        self._def_alloc_combo.setEnabled(not self.read_only)

    def _refresh_def_alloc_combo_values(self):
        if self.is_multifunctional():
            allocation_options = sorted(list(allocation_strategies.keys()))
            # Make the unspecified value the first in the list of options
            allocation_options.insert(0, self.DATABASE_DEFINED_ALLOCATION)
            index = 0
            if (process_alloc := self.parent.activity.get("default_allocation")) is not None:
                try:
                    index = allocation_options.index(process_alloc)
                except ValueError:
                    log.error(f"Invalid Default allocation value '{process_alloc}'"
                              f" for process {self.parent.key}")
            # Append custom option after the index has been calculated
            allocation_options.append(self.CUSTOM_ALLOCATION)
            self._def_alloc_combo.currentTextChanged.disconnect()
            self._def_alloc_combo.clear()
            self._def_alloc_combo.insertItems(0, allocation_options)
            self._def_alloc_combo.setCurrentIndex(index)
            try:
                current_db = self.parent.activity.get("database", "")
                evaluated_properties = list_available_properties(current_db, self.parent.activity)
                properties_dict = {item[0]:item[1] for item in evaluated_properties}
                # Color the combo entries according to their status
                for i in range(len(allocation_options)):
                    brush = None
                    if allocation_options[i] == "equal":
                        brush = style_item.brushes["good"]
                    elif allocation_options[i] in properties_dict:
                        brush = CustomAllocationEditor.brush_for_message_type(
                            properties_dict[allocation_options[i]]
                        )
                    elif 0 < i < len(allocation_options) - 1:
                        brush = style_item.brushes["missing"]
                    if brush is not None:
                        self._def_alloc_combo.setItemData(i, brush, QtCore.Qt.ForegroundRole)
            except ValueError as e:
                log.error(f"Error calculating the colors for the combobox. exception: {e}")

            self._def_alloc_combo.currentTextChanged.connect(self._handle_def_alloc_changed)

    def _handle_def_alloc_changed(self, selection: str):
        changed = False
        current_def_alloc = self.parent.activity.get("default_allocation", "")
        if selection == self.DATABASE_DEFINED_ALLOCATION:
            if current_def_alloc != "":
                del self.parent.activity["default_allocation"]
                changed = True
        elif selection == self.CUSTOM_ALLOCATION:
            custom_value = CustomAllocationEditor.define_custom_allocation(
                                current_def_alloc, self.parent.activity,
                                first_open=False, parent=self
                            )
            if custom_value and custom_value != current_def_alloc:
                self.parent.activity["default_allocation"] = custom_value
                self._refresh_def_alloc_combo_values()
                changed = True
            # Update the selected text of the combo in both cases, so it is not
            # stuck on "Custom..."
            if custom_value:
                self._def_alloc_combo.setCurrentText(custom_value)
            else:
                self._def_alloc_combo.setCurrentIndex(0)
        elif current_def_alloc != selection:
            self.parent.activity["default_allocation"] = selection
            changed = True
        if changed:
            self.parent.activity.save()
            MultifunctionalProcessRedoAllocation.run(self.parent.activity)

