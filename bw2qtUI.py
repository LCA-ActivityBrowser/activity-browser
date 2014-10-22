#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
reload(sys)
sys.setdefaultencoding("utf-8")
from PyQt4 import QtCore, QtGui, QtWebKit
from utils import *
from pssWidget import pssWidget
import time
from ast import literal_eval

class MainWindow(QtGui.QMainWindow):
    signal_add_to_chain = QtCore.pyqtSignal(MyTableQWidgetItem)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.styles = Styles()
        self.helper = HelperMethods()

        # LCA Data
        self.lcaData = BrowserStandardTasks()
        self.history = []

        # create the central container widget
        self.widget = QtGui.QWidget(self)
        self.setStandardWidgets()
        self.setWindowTitle("Activity Browser")
        self.statusBar().showMessage("Welcome")

    def setStandardWidgets(self):
        # BUTTONS
        # random activity
        button_random_activity = QtGui.QPushButton("Random Activity")
        button_key = QtGui.QPushButton("Key")
        # button_backward = QtGui.QPushButton("<<")
        # button_forward = QtGui.QPushButton(">>")
        # search
        button_search = QtGui.QPushButton("Search")
        button_history = QtGui.QPushButton("History")
        button_databases = QtGui.QPushButton("Databases")
        # LINE EDITS
        self.line_edit_search = QtGui.QLineEdit()
        # LABELS
        # dynamic
        self.label_current_activity_product = QtGui.QLabel("Product")
        self.label_current_activity_product.setFont(self.styles.font_big)
        self.label_current_activity_product.setStyleSheet("QLabel { color : blue; }")
        self.label_current_activity = QtGui.QLabel("Activity Name")
        self.label_current_activity.setFont(self.styles.font_big)
        self.label_current_database = QtGui.QLabel("Database")
        self.label_multi_purpose = QtGui.QLabel()
        # static
        label_inputs = QtGui.QLabel("Technosphere Inputs")
        label_downstream_activities = QtGui.QLabel("Downstream Activities")
        # TABLES
        self.table_inputs_technosphere = QtGui.QTableWidget()
        self.table_inputs_biosphere = QtGui.QTableWidget()
        self.table_downstream_activities = QtGui.QTableWidget()
        self.table_multipurpose = QtGui.QTableWidget()

        # SPLITTERS
        self.splitter_right = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter_horizontal = QtGui.QSplitter(QtCore.Qt.Horizontal)
        # LAYOUTS
        # V
        vlayout = QtGui.QVBoxLayout()
        self.VL_RIGHT = QtGui.QVBoxLayout()
        self.VL_LEFT = QtGui.QVBoxLayout()
        # H
        hlayout = QtGui.QHBoxLayout()
        HL_multi_purpose = QtGui.QHBoxLayout()
        # Search
        HL_multi_purpose.addWidget(self.line_edit_search)
        HL_multi_purpose.addWidget(button_search)
        HL_multi_purpose.addWidget(button_history)
        HL_multi_purpose.addWidget(button_databases)
        HL_multi_purpose.addWidget(button_random_activity)
        HL_multi_purpose.addWidget(button_key)
        # TAB WIDGETS
        self.tab_widget_RIGHT = QtGui.QTabWidget()
        self.tab_widget_LEFT = QtGui.QTabWidget()
        # VL
        # LEFT
        self.VL_technosphere = QtGui.QVBoxLayout()
        self.widget_technosphere = QtGui.QWidget()
        self.widget_technosphere.setLayout(self.VL_technosphere)
        self.VL_technosphere.addWidget(label_inputs)
        self.VL_technosphere.addWidget(self.table_inputs_technosphere)
        self.VL_technosphere.addWidget(self.label_current_activity_product)
        self.VL_technosphere.addWidget(self.label_current_activity)
        self.VL_technosphere.addWidget(self.label_current_database)
        self.VL_technosphere.addWidget(label_downstream_activities)
        self.VL_technosphere.addWidget(self.table_downstream_activities)

        # WIDGETS
        self.widget_LEFT = QtGui.QWidget()
        self.widget_RIGHT = QtGui.QWidget()
        # RIGHT SIDE
        self.widget_RIGHT.setLayout(self.VL_RIGHT)
        self.VL_RIGHT.addLayout(HL_multi_purpose)
        self.VL_RIGHT.addWidget(self.label_multi_purpose)
        self.VL_RIGHT.addWidget(self.tab_widget_RIGHT)
        self.tab_widget_RIGHT.addTab(self.table_multipurpose, "SeHiDa")
        self.tab_widget_RIGHT.addTab(self.table_inputs_biosphere, "Biosphere")
        # LEFT SIDE
        self.widget_LEFT.setLayout(self.VL_LEFT)
        self.VL_LEFT.addWidget(self.tab_widget_LEFT)
        self.tab_widget_LEFT.addTab(self.widget_technosphere, "Technosphere")
        # OVERALL
        self.splitter_horizontal.addWidget(self.widget_LEFT)
        self.splitter_horizontal.addWidget(self.widget_RIGHT)
        hlayout.addWidget(self.splitter_horizontal)
        vlayout.addLayout(hlayout)
        self.widget.setLayout(vlayout)
        self.setCentralWidget(self.widget)

        # CONNECTIONS
        button_random_activity.clicked.connect(lambda: self.newActivity())
        # button_backward.clicked.connect(self.goBackward)
        # button_forward.clicked.connect(self.goForward)
        self.line_edit_search.returnPressed.connect(self.search_results)
        button_search.clicked.connect(self.search_results)
        button_history.clicked.connect(self.showHistory)
        button_databases.clicked.connect(self.listDatabases)
        button_key.clicked.connect(self.search_by_key)

        self.table_inputs_technosphere.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_downstream_activities.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_multipurpose.itemDoubleClicked.connect(self.gotoDoubleClickActivity)

        # CONTEXT MENUS
        # MENU BAR
        # Actions
        addPSS = QtGui.QAction('Process Subsystem Editor', self)
        addPSS.setShortcut('Ctrl+E')
        addPSS.setStatusTip('Start Process Subsystem Editor')
        self.connect(addPSS, QtCore.SIGNAL('triggered()'), self.setUpPSSEditor)
        # Add actions
        menubar = self.menuBar()
        file = menubar.addMenu('Extensions')
        file.addAction(addPSS)

    def setUpPSSEditor(self):
        if hasattr(self, 'PSS_Widget'):
            print "PSS WIDGET ALREADY LOADED"
        else:
            self.PSS_Widget = pssWidget()
            self.tab_widget_LEFT.addTab(self.PSS_Widget.PSSdataWidget, "PSS")
            self.tab_widget_LEFT.addTab(self.PSS_Widget.table_PSS_database, "PSS database")
            self.VL_LEFT.addLayout(self.PSS_Widget.HL_PSS_buttons)
            self.VL_LEFT.addLayout(self.PSS_Widget.HL_PSS_Database_buttons)
            self.tab_widget_RIGHT.addTab(self.PSS_Widget.webview, "Graph")
            # CONTEXT MENUS
            # Technosphere Inputs
            self.table_inputs_technosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            self.action_addParentToPSS = QtGui.QAction("add to Process Subsystem", None)
            self.action_addParentToPSS.triggered.connect(self.add_Parent_to_chain)
            self.table_inputs_technosphere.addAction(self.action_addParentToPSS)
            # Downstream Activities
            self.table_downstream_activities.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            self.action_addChildToPSS = QtGui.QAction("add to Process Subsystem", None)
            self.action_addChildToPSS.triggered.connect(self.add_Child_to_chain)
            self.table_downstream_activities.addAction(self.action_addChildToPSS)
            # Search Table
            self.table_multipurpose.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
            self.action_addToPSS = QtGui.QAction("add to Process Subsystem", None)
            self.action_addToPSS.triggered.connect(self.add_to_chain)
            self.table_multipurpose.addAction(self.action_addToPSS)
            # CONNECTIONS BETWEEN WIDGETS
            self.signal_add_to_chain.connect(self.PSS_Widget.addToChain)
            self.PSS_Widget.signal_activity_key.connect(self.gotoDoubleClickActivity)
            self.PSS_Widget.signal_status_bar_message.connect(self.statusBarMessage)
            # MENU BAR
            # Actions
            exportPSSDatabaseAsJSONFile = QtGui.QAction('Export DB to file', self)
            exportPSSDatabaseAsJSONFile.setStatusTip('Export the working PSS database as JSON to a .py file')
            self.connect(exportPSSDatabaseAsJSONFile, QtCore.SIGNAL('triggered()'), self.PSS_Widget.export_as_JSON)
            # Add actions
            menubar = self.menuBar()
            pss_menu = menubar.addMenu('PSS')
            pss_menu.addAction(exportPSSDatabaseAsJSONFile)

    def statusBarMessage(self, message):
        self.statusBar().showMessage(message)

    def listDatabases(self):
        data = self.lcaData.getDatabases()
        keys = ["name", "activities", "dependencies"]
        self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
        label_text = str(len(data)) + " databases found."
        self.label_multi_purpose.setText(QtCore.QString(label_text))
        self.tab_widget_RIGHT.setCurrentIndex(0)

    def get_table_headers(self, type="technosphere"):
        if self.lcaData.database_version == 2:
            if type == "technosphere":
                keys = ["name", "location", "amount", "unit", "database"]
            elif type == "biosphere":
                keys = ["name", "amount", "unit"]
            elif type == "history" or type == "search":
                keys = ["name", "location", "unit", "database"]
        else:
            if type == "technosphere":
                keys = ["product", "name", "location", "amount", "unit", "database"]
            elif type == "biosphere":
                keys = ["name", "amount", "unit"]
            elif type == "history" or type == "search":
                keys = ["product", "name", "location", "unit", "database"]
        return keys

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
            self.tab_widget_RIGHT.setCurrentIndex(0)
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
                self.tab_widget_RIGHT.setCurrentIndex(0)
        except AttributeError:
            self.statusBar().showMessage("Need to load a database first")
        except:
            self.statusBar().showMessage("This did not work.")

    def newActivity(self, key=None):
        try:
            self.lcaData.setNewCurrentActivity(key)
            keys = self.get_table_headers()
            self.table_inputs_technosphere = self.helper.update_table(self.table_inputs_technosphere, self.lcaData.get_exchanges(type="technosphere"), keys)
            self.table_inputs_biosphere = self.helper.update_table(self.table_inputs_biosphere, self.lcaData.get_exchanges(type="biosphere"), self.get_table_headers(type="biosphere"))
            self.table_downstream_activities = self.helper.update_table(self.table_downstream_activities, self.lcaData.get_downstream_exchanges(), keys)
            actdata = self.lcaData.getActivityData()
            label_text = actdata["name"]+" {"+actdata["location"]+"}"
            self.label_current_activity.setText(QtCore.QString(label_text))
            label_text = actdata["product"]+" ["+str(actdata["amount"])+" "+actdata["unit"]+"]"
            self.label_current_activity_product.setText(QtCore.QString(label_text))
        except AttributeError:
            self.statusBar().showMessage("Need to load a database first")

    def gotoDoubleClickActivity(self, item):
        print "DOUBLECLICK on: ", item.text()
        if item.key_type == "activity":
            print "Loading Activity:", item.activity_or_database_key
            self.newActivity(item.activity_or_database_key)
            self.label_current_database.setText(QtCore.QString(item.activity_or_database_key[0]))
        else:  # database
            tic = time.clock()
            self.statusBar().showMessage("Loading... "+item.activity_or_database_key)
            print "Loading Database:", item.activity_or_database_key
            self.lcaData.loadDatabase(item.activity_or_database_key)
            self.statusBar().showMessage(str("Database loaded: {0} in {1:.2f} seconds.").format(item.activity_or_database_key, (time.clock()-tic)))
            self.label_current_database.setText(QtCore.QString(item.activity_or_database_key))

    def showHistory(self):
        keys = self.get_table_headers(type="history")
        data = self.lcaData.getHistory()
        self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
        label_text = "History"
        self.label_multi_purpose.setText(QtCore.QString(label_text))
        self.tab_widget_RIGHT.setCurrentIndex(0)

    def goBackward(self):
        # self.lcaData.goBack()
        print "HISTORY:"
        for key in self.lcaData.history:
            print key, self.lcaData.database[key]["name"]

        if self.lcaData.history:
            self.lcaData.currentActivity = self.lcaData.history.pop()
            self.newActivity(self.lcaData.currentActivity)
            # self.newActivity(self.lcaData.history.pop())
        else:
            print "Cannot go further back."

    def goForward(self):
        pass

    def add_Child_to_chain(self):
        self.signal_add_to_chain.emit(self.table_downstream_activities.currentItem())

    def add_Parent_to_chain(self):
        self.signal_add_to_chain.emit(self.table_inputs_technosphere.currentItem())

    def add_to_chain(self):
        self.signal_add_to_chain.emit(self.table_multipurpose.currentItem())

def main():
    app = QtGui.QApplication(sys.argv)
    mw = MainWindow()
    mw.setUpPSSEditor()
    mw.lcaData.loadDatabase('ecoinvent 2.2')
    mw.newActivity()

    # wnd.resize(800, 600)
    mw.showMaximized()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


