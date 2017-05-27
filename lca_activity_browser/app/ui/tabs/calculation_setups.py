# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from brightway2 import calculation_setups
from ..tables import (
    CSActivityTableWidget,
    CSList,
    CSMethodsTableWidget,
)
from .. import horizontal_line, header
from ...signals import signals
from ..network import SankeyWindow
from PyQt5 import QtCore, QtGui, QtWidgets

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

class CalculationSetupTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(CalculationSetupTab, self).__init__(parent)

        self.activities_table = CSActivityTableWidget()
        self.methods_table = CSMethodsTableWidget()
        self.list_widget = CSList()

        self.new_cs_button = QtWidgets.QPushButton('New')
        self.rename_cs_button = QtWidgets.QPushButton('Rename')
        self.delete_cs_button = QtWidgets.QPushButton('Delete')
        self.calculate_button = QtWidgets.QPushButton('Calculate')
        self.sankey_pb = QtWidgets.QPushButton('Sankey')

        name_row = QtWidgets.QHBoxLayout()
        name_row.addWidget(header('Calculation Setups:'))
        name_row.addWidget(self.list_widget)
        name_row.addWidget(self.new_cs_button)
        name_row.addWidget(self.rename_cs_button)
        name_row.addWidget(self.delete_cs_button)
        name_row.addStretch(1)
        
        calc_row = QtWidgets.QHBoxLayout()
        calc_row.addWidget(self.calculate_button)
        calc_row.addWidget(self.sankey_pb)
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

        signals.project_selected.connect(self.set_default_calculation_setup)
        signals.calculation_setup_selected.connect(self.show_details)
        self.calculate_button.clicked.connect(self.start_calculation)
        self.sankey_pb.clicked.connect(self.open_sankey)

    def start_calculation(self):
        signals.lca_calculation.emit(self.list_widget.name)

    def set_default_calculation_setup(self):
        if not len(calculation_setups):
            self.hide_details()
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

    def connect_signals(self, controller):
        """Signals that alter data and need access to Controller"""
        self.new_cs_button.clicked.connect(controller.new_calculation_setup)
        self.delete_cs_button.clicked.connect(controller.delete_calculation_setup)
        self.rename_cs_button.clicked.connect(controller.rename_calculation_setup)

    def open_sankey(self):
        self.sankey = SankeyWindow(self)
