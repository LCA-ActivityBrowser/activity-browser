# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QIcon

from activity_browser.app.bwutils import commontasks as bc
from .line_edit import SignalledLineEdit, SignalledPlainTextEdit, SignalledComboEdit
from ..icons import icons
from ...signals import signals


class DetailsGroupBox(QtWidgets.QGroupBox):
    def __init__(self, label, widget):
        super().__init__(label)
        self.widget = widget
        self.setCheckable(True)
        self.toggled.connect(self.showhide)
        self.setChecked(False)
        self.setStyleSheet("QGroupBox { border: none; }")
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(widget)
        layout.setContentsMargins(0, 22, 0, 5)
        self.setLayout(layout)
        if isinstance(self.widget, QtWidgets.QTableWidget):
            self.widget.itemChanged.connect(self.toggle_empty_table)

    def showhide(self):
        self.widget.setVisible(self.isChecked())

    def toggle_empty_table(self):
        self.setChecked(bool(self.widget.rowCount()))


class ActivityDataGrid(QtWidgets.QWidget):
    """ Displayed at the top of each activity panel to show the user basic data related to the activity
    Expects to find the following data for each activity displayed: name, location, database, comment
    Exchange data is displayed separately, below this grid, in tables.
    Includes the read-only checkbox which enables or disables user-editing of some activity and exchange data
    """
    def __init__(self, parent, read_only=True):
        super(ActivityDataGrid, self).__init__(parent)

        self.read_only = read_only

        self.name_box = SignalledLineEdit(
            key=getattr(parent.activity, "key", None),
            field="name",
            parent=self,
        )
        # self.name_box.setPlaceholderText("Activity name")

        self.location_combo = SignalledComboEdit(
            key=getattr(parent.activity, "key", None),
            field="location",
            parent=self,
            contents=parent.activity.get('location', '')
        )
        self.location_combo.setToolTip("Select an existing location from the current activity database."
                                          " Or add new location")
        self.location_combo.setEditable(True)  # always 'editable', but not always 'enabled'

        self.database_label = QtWidgets.QLabel('Database')
        self.database_label.setToolTip("Select a different database to duplicate activity to it")

        # the database of the activity is shown as a dropdown (ComboBox), which enables user to change it
        self.database_combo = QtWidgets.QComboBox()
        self.database_combo.currentTextChanged.connect(
            lambda target_db: self.duplicate_confirm_dialog(target_db, parent=parent))
        self.database_combo.setToolTip("Use dropdown menu to duplicate activity to another database")

        self.comment_box = SignalledPlainTextEdit(
            key=getattr(parent.activity, "key", None),
            field="comment",
            parent=self,
        )
        self.comment_groupbox = DetailsGroupBox(
            'Description', self.comment_box)
        self.comment_groupbox.setChecked(False)

        # arrange widgets for display as a grid
        self.grid = QtWidgets.QGridLayout()

        self.setContentsMargins(0, 0, 0, 0)
        self.grid.setContentsMargins(5, 5, 0, 5)
        self.grid.setSpacing(6)
        self.grid.setAlignment(QtCore.Qt.AlignTop)

        self.grid.addWidget(QtWidgets.QLabel('Name'), 1, 1)
        self.grid.addWidget(self.name_box, 1, 2, 1, 3)
        self.grid.addWidget(QtWidgets.QLabel('Location'), 2, 1)
        self.grid.addWidget(self.location_combo, 2, 2, 1, -1)
        self.grid.addWidget(self.database_combo, 3, 2, 1, -1)
        self.grid.addWidget(self.database_label, 3, 1)
        self.grid.addWidget(self.comment_groupbox, 4, 1, 2, -1)

        self.setLayout(self.grid)

        self.populate(parent)

        # do not allow user to edit fields if the ActivityDataGrid is read-only
        self.set_activity_fields_read_only()

    def populate(self, parent):
        # fill in the values of the ActivityDataGrid widgets
        self.name_box.setText(parent.activity.get('name', ''))
        self.name_box._key = parent.activity.key

        self.populate_location_combo(parent)
        self.populate_database_combo(parent)

        self.comment_box.setPlainText(parent.activity.get('comment', ''))
        self.comment_box._key = parent.activity.key
        # the <font> html-tag has no effect besides making the tooltip rich text
        # this is required for line breaks of long comments
        self.comment_groupbox.setToolTip(
            '<font>{}</font>'.format(self.comment_box.toPlainText())
        )
        self.comment_box._before = parent.activity.get('comment', '')
        self.comment_box.adjust_size()

    def populate_location_combo(self, parent):
        """ acts as both: a label to show current location of act, and
                auto-completes with all other locations in the database, to enable selection """
        self.location_combo.blockSignals(True)
        self.location_combo.clear()
        location = parent.activity.get('location', '')
        self.location_combo._before = location

        # get unique set of locations in db
        loc_set = bc.get_locations_in_db(parent.activity.get('database', ''))
        for loc in loc_set:
            self.location_combo.addItem(loc) # perhaps add an icon? QIcon(icons.switch)

        self.location_combo.model().sort(0)
        self.location_combo.setCurrentText(location)
        self.location_combo.blockSignals(False)

    def populate_database_combo(self, parent):
        """ acts as both: a label to show current db of act, and
                allows copying to others editable dbs via populated drop-down list """
        # clear any existing items first
        self.database_combo.blockSignals(True)
        self.database_combo.clear()

        # first item in db combo, shown by default, is the current database
        current_db = parent.activity.get('database', 'Error: db of Act not found')
        self.database_combo.addItem(current_db)

        # other items are the dbs that the activity can be duplicated to: find them and add
        available_target_dbs = bc.get_editable_databases()
        if current_db in available_target_dbs:
            available_target_dbs.remove(current_db)

        for db_name in available_target_dbs:
            self.database_combo.addItem(QIcon(icons.duplicate), db_name)
        self.database_combo.blockSignals(False)

    def duplicate_confirm_dialog(self, target_db, parent):
        """ Get user confirmation for duplication action """
        title = "Duplicate activity to new database"
        text = "Copy {} to {} and open as new tab?".format(
            parent.activity.get('name', 'Error: Name of Act not found'), target_db)

        user_choice = QMessageBox.question(self, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if user_choice == QMessageBox.Yes:
            signals.duplicate_activity_to_db.emit(target_db, parent.activity)
        # todo: give user more options in the dialog:
        #   * retain / delete version in current db
        #   * open / don't open new tab

        # change selected database item back to original (index=0), to avoid confusing user
        # block and unblock signals to prevent unwanted extra emits from the automated change
        self.database_combo.blockSignals(True)
        self.database_combo.setCurrentIndex(0)
        self.database_combo.blockSignals(False)

    def set_activity_fields_read_only(self):
        """ called on init after widgets instantiated
            also whenever a user clicks the read-only checkbox """
        # user cannot edit these fields if they are read-only
        self.name_box.setReadOnly(self.read_only)
        self.location_combo.setEnabled(not self.read_only)
        self.comment_box.setReadOnly(self.read_only)
