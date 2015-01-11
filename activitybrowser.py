#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import os
from PyQt4 import QtCore, QtGui, QtWebKit
# from PySide import QtCore, QtGui, QtWebKit
from browser_utils import *
import browser_settings
from mpwidget import MPWidget
import time
from ast import literal_eval
import uuid
import pprint
import multiprocessing
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt


# class TestMyIdea(QtGui.QWidget):
#
#     def __init__(self, parent=None):
#         super(TestMyIdea, self).__init__(parent)
#         print "was in TestMyIdea"
#
#     def load_Idea(self):
#         table_databases = QtGui.QTableWidget()
#         self.add_dock(table_databases, 'MyIdea',  QtCore.Qt.LeftDockWidgetArea)

# class MySoftware():
#
#     def __init__(self, parent=None):
#         mw = MainWindow()
#
#     def set_up_MP(self):
#         print "was in TestMyIdea"

class MainWindow(QtGui.QMainWindow):
    signal_add_to_chain = QtCore.pyqtSignal(MyQTableWidgetItem)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        # tools from utils
        self.styles = Styles()
        self.helper = HelperMethods()
        self.lcaData = BrowserStandardTasks()

        # Main Window
        self.setWindowTitle("Activity Browser")
        self.statusBar().showMessage("Welcome")

        # dock info
        self.map_dock_name = {}
        self.map_name_dock = {}
        self.dock_info = {}
        self.areas = {}

        # set up standard widgets in docks
        self.set_up_standard_widgets()
        self.set_up_menu_bar()
        self.set_up_context_menus()

        # layout docks
        self.setDockOptions(QtGui.QMainWindow.AllowNestedDocks
                            | QtGui.QMainWindow.AllowTabbedDocks
                            | QtGui.QMainWindow.AnimatedDocks)
        self.position_docks_at_start()
        self.update_dock_positions()
        # raise first tab
        self.map_name_dock['Technosphere'].raise_()
        self.map_name_dock['Databases'].raise_()
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtGui.QTabWidget.North)
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtGui.QTabWidget.North)



        # at program start
        self.listDatabases()

    # Setup of UIs, connections...

    def add_dock(self, widget, dockName, area, tab_pos=None):
        dock = QtGui.QDockWidget(dockName)
        dock.setWidget(widget)
        dock.setFeatures(QtGui.QDockWidget.DockWidgetClosable |
                         QtGui.QDockWidget.DockWidgetMovable |
                         QtGui.QDockWidget.DockWidgetFloatable)
        self.addDockWidget(area, dock)
        self.map_dock_name.update({dock: dockName})
        self.map_name_dock.update({dockName: dock})
        self.dock_info.update()
        self.dock_info.update({
            dockName: {
                'area': area,
                'tab position': tab_pos,
            }
        })

    def position_docks_at_start(self):
        """
        Set areas and tab positions. Override with information from settings file.
        """
        # Update self.dock_info based on settings file
        for area, dock_names in browser_settings.dock_positions_at_start.items():
            for index, dock_name in enumerate(dock_names):
                self.dock_info[dock_name].update({
                    'area': area,
                    'tab position': index,
                })

        # assign all docks to areas
        for name, info in self.dock_info.items():
            self.areas.setdefault(info['area'], []).append(name)
        # print areas

        # order dock names in areas
        for area, dock_names in self.areas.items():
            # remove names from settings file from dock_names
            preset_names = browser_settings.dock_positions_at_start[area]
            for name in preset_names:
                dock_names.remove(name)
            self.areas[area] = preset_names + dock_names

    def update_dock_positions(self):
        # place docks in areas
        for name, dock in self.map_name_dock.items():
            area = self.dock_info[name]['area']
            self.addDockWidget(area, dock)
        # tabify docks
        for area, dock_names in self.areas.items():
            if len(dock_names) > 1:
                for index in range(0, len(dock_names) - 1):
                    self.tabifyDockWidget(self.map_name_dock[dock_names[index]],
                                          self.map_name_dock[dock_names[index + 1]])

    def set_up_standard_widgets(self):
        self.set_up_widget_technosphere()
        self.set_up_widget_LCIA()
        self.set_up_widget_LCA_results()
        self.set_up_widget_databases()
        self.set_up_widget_search()
        self.set_up_widget_biosphere()
        self.set_up_widget_toolbar()
        self.setup_widget_activity_editor()

    def set_up_widget_technosphere(self):
        button_edit = QtGui.QPushButton("Edit")
        button_calc_lca = QtGui.QPushButton("Calculate LCA")
        # LABELS
        # dynamic
        self.label_current_activity_product = QtGui.QLabel("Product")
        self.label_current_activity_product.setFont(self.styles.font_big)
        self.label_current_activity_product.setStyleSheet("QLabel { color : blue; }")
        self.label_current_activity = QtGui.QLabel("Activity Name")
        self.label_current_activity.setFont(self.styles.font_big)
        self.label_current_database = QtGui.QLabel("Database")
        # static
        label_inputs = QtGui.QLabel("Technosphere Inputs")
        label_downstream_activities = QtGui.QLabel("Downstream Activities")
        self.table_inputs_technosphere = QtGui.QTableWidget()
        self.table_downstream_activities = QtGui.QTableWidget()
        # Activity Buttons
        HL_activity_buttons = QtGui.QHBoxLayout()
        HL_activity_buttons.setAlignment(QtCore.Qt.AlignLeft)
        HL_activity_buttons.addWidget(button_edit)
        HL_activity_buttons.addWidget(button_calc_lca)
        # Layout
        VL_technosphere = QtGui.QVBoxLayout()
        VL_technosphere.addWidget(label_inputs)
        VL_technosphere.addWidget(self.table_inputs_technosphere)
        VL_technosphere.addWidget(self.label_current_activity_product)
        VL_technosphere.addWidget(self.label_current_activity)
        VL_technosphere.addWidget(self.label_current_database)
        VL_technosphere.addLayout(HL_activity_buttons)
        VL_technosphere.addWidget(label_downstream_activities)
        VL_technosphere.addWidget(self.table_downstream_activities)
        widget_technosphere = QtGui.QWidget()
        widget_technosphere.setLayout(VL_technosphere)
        # dock
        self.add_dock(widget_technosphere, 'Technosphere', QtCore.Qt.RightDockWidgetArea)
        # Connections
        button_edit.clicked.connect(self.edit_activity)
        button_calc_lca.clicked.connect(self.calculate_lcia)
        self.table_inputs_technosphere.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_downstream_activities.itemDoubleClicked.connect(self.gotoDoubleClickActivity)

    def set_up_widget_databases(self):
        self.table_databases = QtGui.QTableWidget()
        self.add_dock(self.table_databases, 'Databases', QtCore.Qt.LeftDockWidgetArea)
        # Connections
        self.table_databases.itemDoubleClicked.connect(self.gotoDoubleClickDatabase)

    def set_up_widget_search(self):
        self.label_multi_purpose = QtGui.QLabel()
        self.table_multipurpose = QtGui.QTableWidget()
        # Layout
        vl = QtGui.QVBoxLayout()
        vl.addWidget(self.label_multi_purpose)
        vl.addWidget(self.table_multipurpose)
        # dock
        widget = QtGui.QWidget()
        widget.setLayout(vl)
        self.add_dock(widget, 'Search', QtCore.Qt.RightDockWidgetArea)
        # Connections
        self.table_multipurpose.itemDoubleClicked.connect(self.gotoDoubleClickActivity)

    def set_up_widget_biosphere(self):
        self.table_inputs_biosphere = QtGui.QTableWidget()
        self.add_dock(self.table_inputs_biosphere, 'Biosphere', QtCore.Qt.RightDockWidgetArea)

    def set_up_widget_toolbar(self):
        self.line_edit_search = QtGui.QLineEdit()
        self.line_edit_search.setMaximumSize(QtCore.QSize(200, 30))
        # buttons
        button_random_activity = QtGui.QPushButton("Random Activity")
        button_key = QtGui.QPushButton("Key")
        # button_backward = QtGui.QPushButton("<<")
        # button_forward = QtGui.QPushButton(">>")
        button_search = QtGui.QPushButton("Search")
        button_history = QtGui.QPushButton("History")
        button_test = QtGui.QPushButton("Test")

        # toolbar
        self.toolbar = QtGui.QToolBar()
        self.addToolBar(self.toolbar)

        self.toolbar.addWidget(self.line_edit_search)
        self.toolbar.addWidget(button_search)
        self.toolbar.addWidget(button_history)
        self.toolbar.addWidget(button_random_activity)
        self.toolbar.addWidget(button_key)
        self.toolbar.addWidget(button_test)

        # Connections
        button_random_activity.clicked.connect(lambda: self.load_new_current_activity())
        self.line_edit_search.returnPressed.connect(self.search_results)
        button_search.clicked.connect(self.search_results)
        button_history.clicked.connect(self.showHistory)
        button_key.clicked.connect(self.search_by_key)
        button_test.clicked.connect(self.setupMP)

    def setupMP(self):
        # from mpwidget import MPWidget, TestMyIdea
        print "was in setupMP"
        myIdea = TestMyIdea()
        # myIdea.load_Idea()

    def set_up_widget_LCIA(self):
        # TODO this should be split into user interface and update method
        # TODO: create a table that can be filled with methods
        # - one should be able to select e.g. ReCiPe and then get all of its submethods.
        # - the LCA results widget should then also contain a table with Results for all methods
        # - this should be exportable (copy whole table)

        # CPU count
        self.cpu_count = multiprocessing.cpu_count()

        # Labels
        self.label_LCIAW_product = QtGui.QLabel("Product")
        self.label_LCIAW_product.setFont(self.styles.font_bold)
        self.label_LCIAW_product.setStyleSheet("QLabel { color : blue; }")
        self.label_LCIAW_activity = QtGui.QLabel("Activity")
        self.label_LCIAW_activity.setFont(self.styles.font_bold)
        self.label_LCIAW_database = QtGui.QLabel("Database")
        self.label_LCIAW_functional_unit = QtGui.QLabel("Functional Unit:")
        self.label_LCIAW_unit = QtGui.QLabel("unit")
        label_lcia_method = QtGui.QLabel("LCIA method:")
        label_previous_calcs = QtGui.QLabel("Previous calculations")
        # Line edits
        self.line_edit_FU = QtGui.QLineEdit("1.0")
        # Buttons
        self.button_clear_lcia_methods = QtGui.QPushButton("Clear")
        self.button_calc_lcia = QtGui.QPushButton("Calculate")
        self.button_calc_monte_carlo = QtGui.QPushButton("Monte Carlo")
        # Dropdown
        self.combo_lcia_method_part0 = QtGui.QComboBox(self)
        self.combo_lcia_method_part1 = QtGui.QComboBox(self)
        self.combo_lcia_method_part2 = QtGui.QComboBox(self)
        # Tables
        self.table_previous_calcs = QtGui.QTableWidget()

        # set default LCIA method
        self.update_lcia_method(selection=(u'IPCC 2007', u'climate change', u'GWP 100a'))

        # MATPLOTLIB FIGURE Monte Carlo
        self.matplotlib_figure_mc = QtGui.QWidget()
        self.figure_mc = plt.figure()
        self.canvas_mc = FigureCanvas(self.figure_mc)
        self.toolbar_mc = NavigationToolbar(self.canvas_mc, self.matplotlib_figure_mc)
        # set the layout
        plt_layout = QtGui.QVBoxLayout()
        plt_layout.addWidget(self.toolbar_mc)
        plt_layout.addWidget(self.canvas_mc)
        self.matplotlib_figure_mc.setLayout(plt_layout)

        # HL
        self.HL_functional_unit = QtGui.QHBoxLayout()
        self.HL_functional_unit.setAlignment(QtCore.Qt.AlignLeft)
        self.HL_functional_unit.addWidget(self.label_LCIAW_functional_unit)
        self.HL_functional_unit.addWidget(self.line_edit_FU)
        self.HL_functional_unit.addWidget(self.label_LCIAW_unit)

        self.HL_LCIA = QtGui.QHBoxLayout()
        self.HL_LCIA.setAlignment(QtCore.Qt.AlignLeft)
        self.HL_LCIA.addWidget(label_lcia_method)
        self.HL_LCIA.addWidget(self.button_clear_lcia_methods)

        self.HL_calculation = QtGui.QHBoxLayout()
        self.HL_calculation.setAlignment(QtCore.Qt.AlignLeft)
        self.HL_calculation.addWidget(self.button_calc_lcia)
        self.HL_calculation.addWidget(self.button_calc_monte_carlo)

        # VL
        self.VL_LCIA_widget = QtGui.QVBoxLayout()
        self.VL_LCIA_widget.addWidget(self.label_LCIAW_product)
        self.VL_LCIA_widget.addWidget(self.label_LCIAW_activity)
        self.VL_LCIA_widget.addWidget(self.label_LCIAW_database)
        self.VL_LCIA_widget.addLayout(self.HL_functional_unit)
        self.VL_LCIA_widget.addLayout(self.HL_LCIA)
        self.VL_LCIA_widget.addWidget(self.combo_lcia_method_part0)
        self.VL_LCIA_widget.addWidget(self.combo_lcia_method_part1)
        self.VL_LCIA_widget.addWidget(self.combo_lcia_method_part2)
        self.VL_LCIA_widget.addLayout(self.HL_calculation)
        self.VL_LCIA_widget.addWidget(label_previous_calcs)
        self.VL_LCIA_widget.addWidget(self.table_previous_calcs)
        self.VL_LCIA_widget.addWidget(self.matplotlib_figure_mc)
        # dock
        self.widget_LCIA = QtGui.QWidget()
        self.widget_LCIA.setLayout(self.VL_LCIA_widget)
        self.add_dock(self.widget_LCIA, 'LCIA', QtCore.Qt.LeftDockWidgetArea)
        # Connections
        self.button_calc_lcia.clicked.connect(self.calculate_lcia)
        self.button_calc_monte_carlo.clicked.connect(self.calculate_monte_carlo)
        self.table_previous_calcs.itemDoubleClicked.connect(self.goto_LCA_results)
        self.combo_lcia_method_part0.currentIndexChanged.connect(self.update_lcia_method)
        self.combo_lcia_method_part1.currentIndexChanged.connect(self.update_lcia_method)
        self.combo_lcia_method_part2.currentIndexChanged.connect(self.update_lcia_method)
        self.button_clear_lcia_methods.clicked.connect(lambda: self.update_lcia_method(selection=('','','')))

    def set_up_widget_LCA_results(self):
        # Labels
        self.label_LCAR_product = QtGui.QLabel("Product")
        self.label_LCAR_product.setFont(self.styles.font_bold)
        self.label_LCAR_product.setStyleSheet("QLabel { color : blue; }")
        self.label_LCAR_activity = QtGui.QLabel("Activity")
        self.label_LCAR_activity.setFont(self.styles.font_bold)
        self.label_LCAR_database = QtGui.QLabel("Database")
        self.label_LCAR_fu = QtGui.QLabel("Functional Unit")
        self.label_LCAR_method = QtGui.QLabel("Method")
        self.label_LCAR_score = QtGui.QLabel("LCA score")
        self.label_LCAR_score.setFont(self.styles.font_bold)
        self.label_LCAR_score.setStyleSheet("QLabel { color : red; }")
        label_top_processes = QtGui.QLabel("Top Processes")
        label_top_emissions = QtGui.QLabel("Top Emissions")
        # Tables
        self.table_lcia_results = QtGui.QTableWidget()
        self.table_top_processes = QtGui.QTableWidget()
        self.table_top_emissions = QtGui.QTableWidget()
        # VL
        VL_widget_LCIA_Results = QtGui.QVBoxLayout()
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_product)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_activity)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_database)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_fu)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_method)
        VL_widget_LCIA_Results.addWidget(self.label_LCAR_score)
        VL_widget_LCIA_Results.addWidget(label_top_processes)
        VL_widget_LCIA_Results.addWidget(self.table_top_processes)
        VL_widget_LCIA_Results.addWidget(label_top_emissions)
        VL_widget_LCIA_Results.addWidget(self.table_top_emissions)
        # dock
        widget_LCIA_Results = QtGui.QWidget()
        widget_LCIA_Results.setLayout(VL_widget_LCIA_Results)
        self.add_dock(widget_LCIA_Results, 'LCA Results', QtCore.Qt.RightDockWidgetArea)
        # Connections

    def setup_widget_activity_editor(self):
        # Labels
        self.label_ae_activity = QtGui.QLabel("Activity")
        self.label_ae_database = QtGui.QLabel("Select database")
        self.label_ae_tech_in = QtGui.QLabel("Technosphere Inputs")
        self.label_ae_bio_in = QtGui.QLabel("Biosphere Inputs")
        # Buttons
        self.button_save = QtGui.QPushButton("Save New Activity")
        self.button_replace = QtGui.QPushButton("Replace Existing")
        # TABLES
        self.table_AE_activity = QtGui.QTableWidget()
        self.table_AE_technosphere = QtGui.QTableWidget()
        self.table_AE_biosphere = QtGui.QTableWidget()
        # Dropdown
        self.combo_databases = QtGui.QComboBox(self)
        for name in [db['name'] for db in self.lcaData.getDatabases() if db['name'] not in browser_settings.read_only_databases]:
            self.combo_databases.addItem(name)
        # HL
        HL_AE_actions = QtGui.QHBoxLayout()
        HL_AE_actions.addWidget(self.label_ae_database)
        HL_AE_actions.addWidget(self.combo_databases)
        HL_AE_actions.addWidget(self.button_save)
        HL_AE_actions.addWidget(self.button_replace)
        HL_AE_actions.setAlignment(QtCore.Qt.AlignLeft)
        # VL
        VL_AE = QtGui.QVBoxLayout()
        VL_AE.addWidget(self.label_ae_activity)
        VL_AE.addWidget(self.table_AE_activity)
        VL_AE.addWidget(self.label_ae_tech_in)
        VL_AE.addWidget(self.table_AE_technosphere)
        VL_AE.addWidget(self.label_ae_bio_in)
        VL_AE.addWidget(self.table_AE_biosphere)
        VL_AE.addLayout(HL_AE_actions)
        # AE widget
        widget_AE = QtGui.QWidget()
        widget_AE.setLayout(VL_AE)
        self.add_dock(widget_AE, 'Activity Editor', QtCore.Qt.RightDockWidgetArea)
        # Connections
        self.table_AE_technosphere.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_AE_activity.itemChanged.connect(self.change_values_activity)
        self.table_AE_technosphere.itemChanged.connect(self.change_values_technosphere)
        self.table_AE_biosphere.itemChanged.connect(self.change_values_biosphere)
        self.button_save.clicked.connect(self.save_edited_activity)
        self.button_replace.clicked.connect(self.replace_edited_activity)

        # CONTEXT MENUS
        # Technosphere Inputs
        self.action_add_technosphere_exchange = QtGui.QAction("--> edited activity", None)
        self.action_add_technosphere_exchange.triggered.connect(self.add_technosphere_exchange)
        self.table_inputs_technosphere.addAction(self.action_add_technosphere_exchange)
        # Downstream Activities
        self.action_add_downstream_exchange = QtGui.QAction("--> edited activity", None)
        self.action_add_downstream_exchange.triggered.connect(self.add_downstream_exchange)
        self.table_downstream_activities.addAction(self.action_add_downstream_exchange)
        # Multi-Purpose Table
        self.action_add_multipurpose_exchange = QtGui.QAction("--> edited activity", None)
        self.action_add_multipurpose_exchange.triggered.connect(self.add_multipurpose_exchange)
        self.table_multipurpose.addAction(self.action_add_multipurpose_exchange)
        # Biosphere Table
        self.table_inputs_biosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_add_biosphere_exchange = QtGui.QAction("--> edited activity", None)
        self.action_add_biosphere_exchange.triggered.connect(self.add_biosphere_exchange)
        self.table_inputs_biosphere.addAction(self.action_add_biosphere_exchange)
        # AE Technosphere Table
        self.table_AE_technosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_remove_exchange_tech = QtGui.QAction("delete", None)
        self.action_remove_exchange_tech.triggered.connect(self.remove_exchange_from_technosphere)
        self.table_AE_technosphere.addAction(self.action_remove_exchange_tech)
        # AE Biosphere Table
        self.table_AE_biosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_remove_exchange_bio = QtGui.QAction("delete", None)
        self.action_remove_exchange_bio.triggered.connect(self.remove_exchange_from_biosphere)
        self.table_AE_biosphere.addAction(self.action_remove_exchange_bio)

# TODO
    def to_be_deleted_(self):
        # TABLES

        # SPLITTERS
        # self.splitter_right = QtGui.QSplitter(QtCore.Qt.Vertical)
        # self.splitter_horizontal = QtGui.QSplitter(QtCore.Qt.Horizontal)
        # LAYOUTS
        # V
        # vlayout = QtGui.QVBoxLayout()
        # self.VL_RIGHT = QtGui.QVBoxLayout()
        # self.VL_LEFT = QtGui.QVBoxLayout()
        # H


        # TAB WIDGETS
        # self.tab_widget_RIGHT = QtGui.QTabWidget()
        # self.tab_widget_RIGHT.setMovable(True)
        # self.tab_widget_LEFT = QtGui.QTabWidget()
        # self.tab_widget_LEFT.setMovable(True)
        # VL
        # LEFT


        # WIDGETS
        # self.widget_LEFT = QtGui.QWidget()
        # self.widget_RIGHT = QtGui.QWidget()
        # RIGHT SIDE
        # self.widget_RIGHT.setLayout(self.VL_RIGHT)
        # self.VL_RIGHT.addLayout(HL_multi_purpose)
        self.VL_RIGHT.addWidget(self.label_multi_purpose)
        self.VL_RIGHT.addWidget(self.tab_widget_RIGHT)
        # self.tab_widget_RIGHT.addTab(self.table_databases, "Databases")

        # self.tab_widget_RIGHT.addTab(self.table_multipurpose, "Search")

        # self.tab_widget_RIGHT.addTab(self.table_inputs_biosphere, "Biosphere")

        # LEFT SIDE
        self.widget_LEFT.setLayout(self.VL_LEFT)
        self.VL_LEFT.addWidget(self.tab_widget_LEFT)
        # self.tab_widget_LEFT.addTab(self.widget_technosphere, "Technosphere")

        # OVERALL
        self.splitter_horizontal.addWidget(self.widget_LEFT)
        self.splitter_horizontal.addWidget(self.widget_RIGHT)
        hlayout.addWidget(self.splitter_horizontal)
        vlayout.addLayout(hlayout)
        self.central_widget.setLayout(vlayout)
        # self.setCentralWidget(self.central_widget)

        # CONNECTIONS

        # button_backward.clicked.connect(self.goBackward)
        # button_forward.clicked.connect(self.goForward)

    def set_up_context_menus(self):
        # CONTEXT MENUS
        self.table_inputs_technosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.table_downstream_activities.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.table_multipurpose.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_delete_activity = QtGui.QAction("delete activity", None)
        self.action_delete_activity.triggered.connect(self.delete_activity)
        self.table_multipurpose.addAction(self.action_delete_activity)

    def set_up_menu_bar(self):
        # MENU BAR
        # Actions
        addMP = QtGui.QAction('&Meta-Process Editor', self)
        addMP.setShortcut('Ctrl+E')
        addMP.setStatusTip('Start Meta-Process Editor')
        self.connect(addMP, QtCore.SIGNAL('triggered()'), self.set_up_widgets_meta_process)
        # Add actions
        menubar = self.menuBar()
        extensions_menu = menubar.addMenu('&Extensions')
        extensions_menu.addAction(addMP)

        help_menu = QtGui.QMenu('&Help', self)
        menubar.addMenu(help_menu)
        help_menu.addAction('&About', self.about)


    def about(self):
        QtGui.QMessageBox.about(self, "About",
"""Activity Browser

Copyright 2015 Bernhard Steubing, ETH Zurich
email: steubing@ifu.baug.ethz.ch

This software servers as a graphical user interface to do LCA
and is based on the brightway2 LCA software (http://brightwaylca.org/)
as well as own extensions.

Feel free to contact me regarding additional extensions as well
as its use for private and commercial applications.

As licensing questions are not yet determined, the software
shall *not* be used and modified without prior consent of the author;
copies as well as modified versions of the software shall *not*
be distributed to others without the consent of the author."""
)

    def statusBarMessage(self, message):
        """
        Can be used to display status bar messages from other widgets via signal-connect.
        :param message:
        :return:
        """
        self.statusBar().showMessage(message)

    # META-PROCESS STUFF

    def set_up_widgets_meta_process(self):
        if hasattr(self, 'MP_Widget'):
            print "MP WIDGET ALREADY LOADED"
        else:
            self.MP_Widget = MPWidget()
            # self.tab_widget_LEFT.addTab(self.MP_Widget.MPdataWidget, "MP")
            self.add_dock(self.MP_Widget.MPdataWidget, 'MP', QtCore.Qt.LeftDockWidgetArea)
            # self.tab_widget_LEFT.addTab(self.MP_Widget.table_MP_database, "MP database")
            self.add_dock(self.MP_Widget.table_MP_database, 'MP database', QtCore.Qt.LeftDockWidgetArea)
            # self.tab_widget_LEFT.addTab(self.MP_Widget.PP_analyzer, "MP LCA")
            self.add_dock(self.MP_Widget.PP_analyzer, 'MP LCA', QtCore.Qt.LeftDockWidgetArea)
            # self.VL_LEFT.addLayout(self.MP_Widget.HL_MP_buttons)
            # self.VL_LEFT.addLayout(self.MP_Widget.HL_MP_Database_buttons)
            # add buttons as new toolbar
            # toolbar
            self.toolbar_MP = QtGui.QToolBar()
            self.addToolBar(self.MP_Widget.toolbar_MP)

            # vl = QtGui.QVBoxLayout()
            # vl.addLayout(self.MP_Widget.HL_MP_buttons)
            # vl.addLayout(self.MP_Widget.HL_MP_Database_buttons)
            # widget = QtGui.QWidget()
            # widget.setLayout(vl)
            # self.add_dock(widget, 'buttons', QtCore.Qt.LeftDockWidgetArea)

            # self.tab_widget_RIGHT.addTab(self.MP_Widget.webview, "Graph")
            self.add_dock(self.MP_Widget.webview, 'Graph', QtCore.Qt.RightDockWidgetArea)
            # self.webview = QtWebKit.QWebView()
            # self.setCentralWidget(self.webview)
            # self.tab_widget_RIGHT.addTab(self.webview, "Graph")
            # self.tab_widget_RIGHT.addTab(QtGui.QWidget(), "Graph")
            # self.position_docks_at_start()
            # self.update_dock_positions()
            print self.map_name_dock.keys()
            print self.areas
            print self.dock_info

            # CONTEXT MENUS
            # Technosphere Inputs
            self.action_addParentToMP = QtGui.QAction("--> Meta-Process", None)
            self.action_addParentToMP.triggered.connect(self.add_Parent_to_chain)
            self.table_inputs_technosphere.addAction(self.action_addParentToMP)
            # Downstream Activities
            self.action_addChildToMP = QtGui.QAction("--> Meta-Process", None)
            self.action_addChildToMP.triggered.connect(self.add_Child_to_chain)
            self.table_downstream_activities.addAction(self.action_addChildToMP)
            # Multi-Purpose Table
            self.action_addToMP = QtGui.QAction("--> Meta-Process", None)
            self.action_addToMP.triggered.connect(self.add_to_chain)
            self.table_multipurpose.addAction(self.action_addToMP)
            # CONNECTIONS BETWEEN WIDGETS
            self.signal_add_to_chain.connect(self.MP_Widget.addToChain)
            self.MP_Widget.signal_activity_key.connect(self.gotoDoubleClickActivity)
            self.MP_Widget.signal_status_bar_message.connect(self.statusBarMessage)
            # MENU BAR
            # Actions
            exportMPDatabaseAsJSONFile = QtGui.QAction('Export DB to file', self)
            exportMPDatabaseAsJSONFile.setStatusTip('Export the working MP database as JSON to a .py file')
            self.connect(exportMPDatabaseAsJSONFile, QtCore.SIGNAL('triggered()'), self.MP_Widget.export_as_JSON)
            # Add actions
            menubar = self.menuBar()
            mp_menu = menubar.addMenu('MP')
            mp_menu.addAction(exportMPDatabaseAsJSONFile)

    def add_Child_to_chain(self):
        self.signal_add_to_chain.emit(self.table_downstream_activities.currentItem())

    def add_Parent_to_chain(self):
        self.signal_add_to_chain.emit(self.table_inputs_technosphere.currentItem())

    def add_to_chain(self):
        self.signal_add_to_chain.emit(self.table_multipurpose.currentItem())

    # NAVIGATION

    def gotoDoubleClickActivity(self, item):
        print "DOUBLECLICK on: ", item.text()
        if item.key_type == "activity":
            print "Loading Activity:", item.activity_or_database_key
            self.load_new_current_activity(item.activity_or_database_key)

    def load_new_current_activity(self, key=None):
        try:
            self.lcaData.setNewCurrentActivity(key)
            keys = self.get_table_headers()
            self.table_inputs_technosphere = self.helper.update_table(self.table_inputs_technosphere, self.lcaData.get_exchanges(type="technosphere"), keys)
            self.table_inputs_biosphere = self.helper.update_table(self.table_inputs_biosphere, self.lcaData.get_exchanges(type="biosphere"), self.get_table_headers(type="biosphere"))
            self.table_downstream_activities = self.helper.update_table(self.table_downstream_activities, self.lcaData.get_downstream_exchanges(), keys)
            ad = self.lcaData.getActivityData()
            label_text = ad["name"]+" {"+ad["location"]+"}"
            self.label_current_activity.setText(QtCore.QString(label_text))
            label_text = ad["product"]+" ["+str(ad["amount"])+" "+ad["unit"]+"]"
            self.label_current_activity_product.setText(QtCore.QString(label_text))
            self.label_current_database.setText(QtCore.QString(ad['database']))
            # update LCIA widget
            self.label_LCIAW_product.setText(ad['product'])
            self.label_LCIAW_activity.setText("".join([ad['name'], " {", ad['location'], "}"]))
            self.label_LCIAW_database.setText(ad['database'])
            self.label_LCIAW_unit.setText(ad['unit'])
        except AttributeError:
            self.statusBar().showMessage("Need to load a database first")

    def showHistory(self):
        keys = self.get_table_headers(type="history")
        data = self.lcaData.getHistory()
        self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
        label_text = "History"
        self.label_multi_purpose.setText(QtCore.QString(label_text))
        # TODO: self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_multipurpose))

    def goBackward(self):
        # self.lcaData.goBack()
        print "HISTORY:"
        for key in self.lcaData.history:
            print key, self.lcaData.database[key]["name"]

        if self.lcaData.history:
            self.lcaData.currentActivity = self.lcaData.history.pop()
            self.load_new_current_activity(self.lcaData.currentActivity)
            # self.load_new_current_activity(self.lcaData.history.pop())
        else:
            print "Cannot go further back."

    def goForward(self):
        pass

    def get_table_headers(self, type="technosphere"):
        if self.lcaData.database_version == 2:
            if type == "technosphere":
                keys = ["name", "location", "amount", "unit", "database"]
            elif type == "biosphere":
                keys = ["name", "amount", "unit"]
            elif type == "history" or type == "search":
                keys = ["name", "location", "unit", "database", "key"]
        else:
            if type == "technosphere":
                keys = ["product", "name", "location", "amount", "unit", "database"]
            elif type == "biosphere":
                keys = ["name", "amount", "unit"]
            elif type == "history" or type == "search":
                keys = ["product", "name", "location", "unit", "database", "key"]
        return keys

    # DATABASES

    def listDatabases(self):
        data = self.lcaData.getDatabases()
        keys = ["name", "activities", "dependencies"]
        self.table_databases = self.helper.update_table(self.table_databases, data, keys)

    def gotoDoubleClickDatabase(self, item):
        print "DOUBLECLICK on: ", item.text()
        if item.key_type != "activity":
            tic = time.clock()
            self.statusBar().showMessage("Loading... "+item.activity_or_database_key)
            print "Loading Database:", item.activity_or_database_key
            self.lcaData.loadDatabase(item.activity_or_database_key)
            self.statusBar().showMessage(str("Database loaded: {0} in {1:.2f} seconds.").format(item.activity_or_database_key, (time.clock()-tic)))

    # SEARCH

    def search_results(self):
        searchString = self.line_edit_search.text()
        try:
            if searchString == '':
                print "Listing all activities in database"
                data = [self.lcaData.getActivityData(key) for key in self.lcaData.database.keys()]
                data.sort(key=lambda x: x['name'])
            else:
                print "\nSearched for:", searchString
                data = self.lcaData.get_search_results(searchString)
            keys = self.get_table_headers(type="search")
            self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
            label_text = str(len(data)) + " activities found."
            self.label_multi_purpose.setText(QtCore.QString(label_text))
            # TODO self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_multipurpose))
        except AttributeError:
            self.statusBar().showMessage("Need to load a database first")

    def search_by_key(self):
        searchString = str(self.line_edit_search.text())
        try:
            if searchString != '':
                print "\nSearched for:", searchString
                data = [self.lcaData.getActivityData(literal_eval(searchString))]
                print "Data: "
                print data
                keys = self.get_table_headers(type="search")
                self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
                label_text = str(len(data)) + " activities found."
                self.label_multi_purpose.setText(QtCore.QString(label_text))
                # TODO self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_multipurpose))
        except AttributeError:
            self.statusBar().showMessage("Need to load a database first")
        except:
            self.statusBar().showMessage("Could not find activity key for searchstring.")

    # LCIA and LCA Results

    def update_lcia_method(self, current_index=0, selection=None):
        if not selection:
            selection = (str(self.combo_lcia_method_part0.currentText()), str(self.combo_lcia_method_part1.currentText()), str(self.combo_lcia_method_part2.currentText()))
            print "LCIA method combobox selection: "+str(selection)
        methods, parts = self.lcaData.get_selectable_LCIA_methods(selection)
        # set new available choices
        comboboxes = [self.combo_lcia_method_part0, self.combo_lcia_method_part1, self.combo_lcia_method_part2]
        for i, combo in enumerate(comboboxes):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(['']+parts[i])
            if len(parts[i]) == 1:  # choice made for this combobox (and then only 2 left: 0='', 1='choice'
                combo.setCurrentIndex(1)
            combo.blockSignals(False)

    def calculate_lcia(self, monte_carlo=False):
        method = self.lcaData.LCIA_method
        if not self.lcaData.currentActivity:
            self.statusBar().showMessage("Need to load an activity first.")
        elif not method:
            self.statusBar().showMessage("Need to select an LCIA method first.")
        else:
            if self.line_edit_FU and self.helper.is_number(self.line_edit_FU.text()):
                amount = float(self.line_edit_FU.text())
            else:
                amount = 1.0

            tic = time.clock()
            uuid_ = self.lcaData.lcia(amount=amount, method=method)
            # Update Table Previous LCA calculations
            keys = ['product', 'name', 'location', 'database', 'functional unit', 'unit', 'method']
            data = []
            for lcia_data in self.lcaData.LCIA_calculations.values():
                data.append(dict(lcia_data.items() + self.lcaData.getActivityData(lcia_data['key']).items()))
            self.table_previous_calcs = self.helper.update_table(
                self.table_previous_calcs, data, keys)
            # Monte Carlo LCA
            if monte_carlo:
                self.lcaData.monte_carlo_lcia(key=None, amount=amount, method=method,
                                              iterations=500, cpu_count=self.cpu_count, uuid_=uuid_)
            # Update LCA results
            self.update_LCA_results(uuid_)
            # TODO self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_LCIA_Results))
            self.statusBar().showMessage("Calculated LCIA score in {:.2f} seconds.".format(time.clock()-tic))

    def calculate_monte_carlo(self):
        self.calculate_lcia(monte_carlo=True)

    def goto_LCA_results(self, item):
        print "DOUBLECLICK on: ", item.text()
        if item.uuid_:
            print "Loading LCA Results for:", str(item.text())
            self.update_LCA_results(item.uuid_)
        else:
            print "Error: Item does not have a UUID"

    def update_LCA_results(self, uuid_):
        lcia_data = self.lcaData.LCIA_calculations[uuid_]
        ad = self.lcaData.getActivityData(lcia_data['key'])
        # Update Labels
        self.label_LCAR_product.setText(ad['product'])
        self.label_LCAR_activity.setText("".join([ad['name'], " {", ad['location'], "}"]))
        self.label_LCAR_database.setText(ad['database'])
        self.label_LCAR_fu.setText(" ".join(["{:.3g}".format(lcia_data['functional unit']), ad['unit']]))
        self.label_LCAR_method.setText(", ".join([m for m in lcia_data['method']]))
        self.label_LCAR_score.setText("{:.3g} {:}".format(lcia_data['score'], bw2.methods[lcia_data['method']]['unit']))
        # Tables
        # Top Processes
        keys = ['inventory', 'unit', 'name', 'impact score', '%']
        data = []
        for row in lcia_data['top processes']:
            acd = self.lcaData.getActivityData(row[-1])
            data.append({
                'inventory': "{:.3g}".format(row[1]),
                'unit': acd['unit'],
                'impact score': "{:.3g}".format(row[0]),
                '%': "{:.2f}".format(100*row[0]/lcia_data['score']),
                'name': acd['name'],
            })
        self.table_top_processes = self.helper.update_table(
            self.table_top_processes, data, keys)
        # Top Emissions
        data = []
        for row in lcia_data['top emissions']:
            acd = self.lcaData.getActivityData(row[-1])
            data.append({
                'inventory': "{:.3g}".format(row[1]),
                'unit': acd['unit'],
                'impact score': "{:.3g}".format(row[0]),
                '%': "{:.2f}".format(100*row[0]/lcia_data['score']),
                'name': acd['name'],
            })
        self.table_top_emissions = self.helper.update_table(
            self.table_top_emissions, data, keys)
        # Monte Carlo
        if uuid_ in self.lcaData.LCIA_calculations_mc.keys():
            self.plot_figure_mc(self.lcaData.LCIA_calculations_mc[uuid_])
        else:
            self.figure_mc.clf()
            self.canvas_mc.draw()

    def plot_figure_mc(self, mc):
        ''' plot matplotlib Monte Carlo figure '''
        # get matplotlib figure data
        hist = np.array(mc['histogram'])
        smoothed = np.array(mc['smoothed'])
        values = hist[:, 0]
        bins = hist[:, 1]
        sm_x = smoothed[:, 0]
        sm_y = smoothed[:, 1]
        median = mc['statistics']['median']
        mean = mc['statistics']['mean']
        lconfi, upconfi =mc['statistics']['interval'][0], mc['statistics']['interval'][1]

        # plot
        self.figure_mc.clf()
        ax = self.figure_mc.add_subplot(111)
        plt.rcParams.update({'font.size': 10})
        ax.plot(values, bins)
        ax.plot(sm_x, sm_y)
        ax.vlines(lconfi, 0 , sm_y[0],
                  label='lower 95%: {:.3g}'.format(lconfi), color='red', linewidth=2.0)
        ax.vlines(upconfi, 0 , sm_y[-1],
                  label='upper 95%: {:.3g}'.format(upconfi), color='red', linewidth=2.0)
        ax.vlines(median, 0 , sm_y[self.helper.find_nearest(sm_x, median)],
                  label='median: {:.3g}'.format(median), color='magenta', linewidth=2.0)
        ax.vlines(mean, 0 , sm_y[self.helper.find_nearest(sm_x, mean)],
                  label='mean: {:.3g}'.format(mean), color='blue', linewidth=2.0)
        plt.xlabel('LCA scores'), plt.ylabel('count')
        plt.legend(loc='upper right', prop={'size':10})
        self.canvas_mc.draw()

    # ACTIVITY EDITOR (AE)

    def edit_activity(self):
        if self.lcaData.currentActivity:
            self.lcaData.set_edit_activity(self.lcaData.currentActivity)
            self.update_AE_tables()
            # TODO: self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_AE))

    def add_technosphere_exchange(self):
        self.lcaData.add_exchange(self.table_inputs_technosphere.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def add_downstream_exchange(self):
        self.lcaData.add_exchange(self.table_downstream_activities.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def add_multipurpose_exchange(self):
        self.lcaData.add_exchange(self.table_multipurpose.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def add_biosphere_exchange(self):
        self.lcaData.add_exchange(self.table_inputs_biosphere.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def remove_exchange_from_technosphere(self):
        self.lcaData.remove_exchange(self.table_AE_technosphere.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def remove_exchange_from_biosphere(self):
        self.lcaData.remove_exchange(self.table_AE_biosphere.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def change_values_activity(self):
        item = self.table_AE_activity.currentItem()
        print "Changed value: " + str(item.text())
        header = str(self.table_AE_activity.horizontalHeaderItem(self.table_AE_activity.currentColumn()).text())
        self.lcaData.change_activity_value(str(item.text()), type=header)
        self.update_AE_tables()

    def change_values_technosphere(self):
        item = self.table_AE_technosphere.currentItem()
        print "Changed value: " + str(item.text())
        self.lcaData.change_exchange_value(item.activity_or_database_key, str(item.text()), "amount")
        self.update_AE_tables()

    def change_values_biosphere(self):
        item = self.table_AE_biosphere.currentItem()
        print "Changed value: " + str(item.text())
        self.lcaData.change_exchange_value(item.activity_or_database_key, str(item.text()), "amount")
        self.update_AE_tables()

    def save_edited_activity(self, overwrite=False):
        if overwrite:
            key = self.lcaData.editActivity_key
        else:
            key = (unicode(str(self.combo_databases.currentText())), unicode(uuid.uuid4().urn[9:]))
        if str(self.table_AE_activity.item(0, 0).text()):
            name = str(self.table_AE_activity.item(0, 0).text())  # ref product
        else:
            name = str(self.table_AE_activity.item(0, 1).text())  # activity name
        values = self.lcaData.editActivity_values
        prod_exc_data = {
            "name": name,
            "amount": float(self.table_AE_activity.item(0, 2).text()),
            "input": key,
            "type": "production",
            "unit": str(self.table_AE_activity.item(0, 3).text()),
        }
        print "\nSaving\nKey: " + str(key)
        print "Values:"
        pprint.pprint(values)
        print "Production exchange: " + str(prod_exc_data)
        self.lcaData.save_activity_to_database(key, values, prod_exc_data)
        if overwrite:
            self.statusBar().showMessage("Replaced existing activity.")
        else:
            self.statusBar().showMessage("Saved as new activity.")

    def replace_edited_activity(self):
        key = self.lcaData.editActivity_key
        if key[0] in browser_settings.read_only_databases:
            self.statusBar().showMessage('Cannot save to protected database "'+str(key[0])+'". See settings file.')
        else:
            self.save_edited_activity(overwrite=True)

    def delete_activity(self):
        key = self.table_multipurpose.currentItem().activity_or_database_key
        if key[0] not in browser_settings.read_only_databases:
            mgs = "Delete this activity?"
            reply = QtGui.QMessageBox.question(self, 'Message',
                        mgs, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.lcaData.delete_activity(key)
                self.statusBar().showMessage("Deleted activity: "+str(key))
            else:
                self.statusBar().showMessage("Yeah... better safe than sorry.")
        else:
            self.statusBar().showMessage("Not allowed to delete from: "+str(key[0]))

    def update_AE_tables(self):
        keys = ['product', 'name', 'amount', 'unit', 'location']
        ad = self.lcaData.getActivityData(values=self.lcaData.editActivity_values)
        # ad['database'] = "please choose"  # for safety reasons. You do not want to modify ecoinvent data.
        self.table_AE_activity = self.helper.update_table(
            self.table_AE_activity, [ad], keys, edit_keys=keys)
        exchanges = self.lcaData.editActivity_values['exchanges']
        self.table_AE_technosphere = self.helper.update_table(
            self.table_AE_technosphere,
            self.lcaData.get_exchanges(exchanges=exchanges, type="technosphere"),
            self.get_table_headers(type="technosphere"),
            edit_keys=['amount'])
        self.table_AE_biosphere = self.helper.update_table(
            self.table_AE_biosphere,
            self.lcaData.get_exchanges(exchanges=exchanges, type="biosphere"),
            self.get_table_headers(type="biosphere"),
            edit_keys=['amount'])
        self.table_AE_activity.setMaximumHeight(self.table_AE_activity.horizontalHeader().height()+self.table_AE_activity.rowHeight(0))


# class TestMyIdea(MainWindow):
#
#     def __init__(self):
#         # super(TestMyIdea, self).__init__(parent)
#         print "was in TestMyIdea"
#         table_databases = QtGui.QTableWidget()
#         super(TestMyIdea, self).add_dock(table_databases, 'MyIdea',  QtCore.Qt.LeftDockWidgetArea)

def main():
    app = QtGui.QApplication(sys.argv)
    mw = MainWindow()

    # AUTO-START CUSTOMIZATION
    # mw.setUpMPEditor()
    # mw.lcaData.loadDatabase('ecoinvent 2.2')
    # mw.load_new_current_activity()

    # wnd.resize(800, 600)
    mw.showMaximized()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
