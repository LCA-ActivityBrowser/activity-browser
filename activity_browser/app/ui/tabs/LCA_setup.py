# -*- coding: utf-8 -*-
from PySide2 import QtWidgets
from brightway2 import calculation_setups

# from activity_browser.app.ui.web.sankey import SankeyWidget
from ..icons import qicons
from ..style import horizontal_line, header
from ..tables import (
    CSActivityTable,
    CSList,
    CSMethodsTable,
)
from ...signals import signals

"""
Lifecycle of a calculation setup
================================

Data format
-----------

{name: {'inv': [{key: amount}], 'ia': [method]}}

Responsibilities
----------------

``CalculationSetupTab`` manages whether the activities and methods tables are shown, and which buttons are shown.

``CSActivityTableWidget`` and ``CSMethodsTableWidget`` mangage drag and drop events, and use signals to communicate data changes with the controller.

Initiation
----------

The app is started, a default project is loaded. ``CalculationSetupTab`` is initiated. If a calculation setup is present, the first one in a sorted list is selected. The signal ``calculation_setup_selected`` is emitted. Activity and methods tables are shown, as well as the full button row. If no calculation setup is available, all tables and most buttons are hidden, only the ``new_cs_button`` is shown.

``calculation_setup_selected`` is received by ``CSList``, which sets the list index correctly.

``calculation_setup_selected`` is received by ``CSActivityTableWidget`` and ``CSMethodsTableWidget``, and data is displayed.

Selecting a new project
-----------------------

When a new project is selected, the signal ``project_selected`` is received by ``CalculationSetupTab``, which follows the same procedure: emit ``calculation_setup_selected`` is possible, otherwise hide tables and buttons.

Selecting a different calculation setup
---------------------------------------

When a new calculation setup is selected in ``CSList``, the event ``itemSelectionChanged`` calls a function that emits ``calculation_setup_selected``.

Altering the current calculation setup
--------------------------------------

When new activities or methods are dragged into the activity or methods tables, the signal ``calculation_setup_changed`` is emitted. ``calculation_setup_changed`` is received by a controller method ``write_current_calculation_setup`` which saves the current data.

When the amount of an activity is changed, the event ``cellChanged`` is caught by ``CSActivityTableWidget``, which emits ``calculation_setup_changed``.

Creating a new calculation setup
--------------------------------

The button ``new_cs_button`` is connected to the controller method ``new_calculation_setup``, which creates the new controller setup and in turn emits ``calculation_setup_selected``. Note that ``CSList`` rebuilds the list of all calculation setups when receiving ``calculation_setup_selected``, so the new setup is listed.

Renaming a calculation setup
----------------------------

The button ``rename_cs_button`` is connected to the controller method ``rename_calculation_setup``, which changes the calculation setup name and in turn emits ``calculation_setup_selected``.

Deleting a calculation setup
----------------------------

The button ``delete_cs_button`` is connected to the controller method ``delete_calculation_setup``, which deletes the calculation setup name and in turn emits ``calculation_setups_changed``.

State data
----------

The currently selected calculation setup is retrieved by getting the currently selected value in ``CSList``.

"""


class LCASetupTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(LCASetupTab, self).__init__(parent)
        self.window = self.window()

        self.activities_table = CSActivityTable(self)
        self.methods_table = CSMethodsTable(self)
        self.list_widget = CSList()

        self.new_cs_button = QtWidgets.QPushButton(qicons.add, "New")
        self.rename_cs_button = QtWidgets.QPushButton(qicons.edit, "Rename")
        self.delete_cs_button = QtWidgets.QPushButton(qicons.delete, "Delete")
        self.calculate_button = QtWidgets.QPushButton(qicons.calculate, "Calculate")
        # self.sankey_button = QtWidgets.QPushButton('Sankey')

        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(header('Calculation Setups:'))
        name_row.addWidget(self.list_widget)
        name_row.addWidget(self.new_cs_button)
        name_row.addWidget(self.rename_cs_button)
        name_row.addWidget(self.delete_cs_button)
        name_row.addStretch(1)

        calc_row = QtWidgets.QHBoxLayout()
        calc_row.addWidget(self.calculate_button)
        # calc_row.addWidget(self.sankey_button)
        calc_row.addStretch(1)

        container = QtWidgets.QVBoxLayout()
        container.addLayout(name_row)
        container.addLayout(calc_row)
        container.addWidget(horizontal_line())
        container.addWidget(header('Products and amounts:'))
        container.addWidget(self.activities_table)
        container.addWidget(horizontal_line())
        container.addWidget(header('LCIA Methods:'))
        container.addWidget(self.methods_table)

        self.setLayout(container)

        self.connect_signals()

    def connect_signals(self):
        # Signals
        self.calculate_button.clicked.connect(self.start_calculation)
        # self.sankey_button.clicked.connect(self.open_sankey)

        self.new_cs_button.clicked.connect(signals.new_calculation_setup.emit)
        self.delete_cs_button.clicked.connect(
            lambda x: signals.delete_calculation_setup.emit(
                self.list_widget.name
        ))
        self.rename_cs_button.clicked.connect(
            lambda x: signals.rename_calculation_setup.emit(
                self.list_widget.name
        ))
        signals.calculation_setup_changed.connect(self.save_cs_changes)

        # Slots
        signals.set_default_calculation_setup.connect(self.set_default_calculation_setup)
        signals.project_selected.connect(self.set_default_calculation_setup)
        signals.calculation_setup_selected.connect(self.show_details)
        signals.calculation_setup_selected.connect(self.enable_calculations)
        signals.calculation_setup_changed.connect(self.enable_calculations)

    def save_cs_changes(self):
        name = self.list_widget.name
        if name:
            calculation_setups[name] = {
                'inv': self.activities_table.to_python(),
                'ia': self.methods_table.to_python()
            }

    def start_calculation(self):
        signals.lca_calculation.emit(self.list_widget.name)

    def set_default_calculation_setup(self):
        if not len(calculation_setups):
            self.hide_details()
            self.calculate_button.setEnabled(False)
            # self.sankey_button.setEnabled(False)
        else:
            signals.calculation_setup_selected.emit(
                sorted(calculation_setups)[0]
            )

    def hide_details(self):
        self.rename_cs_button.hide()
        self.delete_cs_button.hide()
        self.list_widget.hide()
        self.activities_table.hide()
        self.methods_table.hide()

    def show_details(self):
        self.rename_cs_button.show()
        self.delete_cs_button.show()
        self.list_widget.show()
        self.activities_table.show()
        self.methods_table.show()

    def enable_calculations(self):
        valid_cs = all([self.activities_table.rowCount(), self.methods_table.rowCount()])
        self.calculate_button.setEnabled(valid_cs)
        # self.sankey_button.setEnabled(valid_cs)

    # def open_sankey(self):
    #     if self.list_widget.currentText():
    #         cs = self.list_widget.currentText()
    #         if hasattr(self, 'sankey'):
    #             self.window.stacked.removeWidget(self.sankey)
    #             self.sankey.deleteLater()
    #         self.sankey = SankeyWidget(self, cs=cs)
    #         self.window.stacked.addWidget(self.sankey)
    #         self.window.stacked.setCurrentWidget(self.sankey)
    #         signals.update_windows.emit()
