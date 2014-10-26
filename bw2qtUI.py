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
import uuid
import pprint

class MainWindow(QtGui.QMainWindow):
    signal_add_to_chain = QtCore.pyqtSignal(MyQTableWidgetItem)

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.styles = Styles()
        self.helper = HelperMethods()

        # LCA Data
        self.lcaData = BrowserStandardTasks()
        self.history = []

        # Activity Editor settings
        self.read_only_databases = ["ecoinvent 2.2", "ecoinvent 2.2 multioutput", "ecoinvent 3.01 default",
                                    "ecoinvent 3.01 cutoff", "ecoinvent 3.01 consequential", "ecoinvent 3.1 default",
                                    "ecoinvent 3.1 cutoff", "ecoinvent 3.1 consequential", "biosphere", "biosphere3"]

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
        button_edit = QtGui.QPushButton("Edit")
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
        HL_multi_purpose.addWidget(button_edit)
        # TAB WIDGETS
        self.tab_widget_RIGHT = QtGui.QTabWidget()
        self.tab_widget_RIGHT.setMovable(True)
        self.tab_widget_LEFT = QtGui.QTabWidget()
        self.tab_widget_LEFT.setMovable(True)
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
        button_random_activity.clicked.connect(lambda: self.load_new_current_activity())
        # button_backward.clicked.connect(self.goBackward)
        # button_forward.clicked.connect(self.goForward)
        self.line_edit_search.returnPressed.connect(self.search_results)
        button_search.clicked.connect(self.search_results)
        button_history.clicked.connect(self.showHistory)
        button_databases.clicked.connect(self.listDatabases)
        button_key.clicked.connect(self.search_by_key)
        button_edit.clicked.connect(self.edit_activity)

        self.table_inputs_technosphere.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_downstream_activities.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
        self.table_multipurpose.itemDoubleClicked.connect(self.gotoDoubleClickActivity)

        # CONTEXT MENUS
        self.table_inputs_technosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.table_downstream_activities.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.table_multipurpose.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_delete_activity = QtGui.QAction("delete activity", None)
        self.action_delete_activity.triggered.connect(self.delete_activity)
        self.table_multipurpose.addAction(self.action_delete_activity)

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

    def setUpActivityEditor(self):
        if not hasattr(self, 'VL_AE'):
            # Labels
            self.label_ae_activity = QtGui.QLabel("Activity")
            self.label_ae_database = QtGui.QLabel("Select database")
            self.label_ae_tech_in = QtGui.QLabel("Technosphere Inputs")
            self.label_ae_bio_in = QtGui.QLabel("Biosphere Inputs")
            # Buttons
            self.button_save = QtGui.QPushButton("Save Activity")
            # TABLES
            self.table_AE_activity = QtGui.QTableWidget()
            self.table_AE_technosphere = QtGui.QTableWidget()
            self.table_AE_biosphere = QtGui.QTableWidget()
            # Dropdown
            self.combo_databases = QtGui.QComboBox(self)
            for name in [db['name'] for db in self.lcaData.getDatabases() if db['name'] not in self.read_only_databases]:
                self.combo_databases.addItem(name)
            # HL
            self.HL_AE_actions = QtGui.QHBoxLayout()
            self.HL_AE_actions.addWidget(self.label_ae_database)
            self.HL_AE_actions.addWidget(self.combo_databases)
            self.HL_AE_actions.addWidget(self.button_save)
            self.HL_AE_actions.setAlignment(QtCore.Qt.AlignLeft)
            # VL
            self.VL_AE = QtGui.QVBoxLayout()
            self.VL_AE.addWidget(self.label_ae_activity)
            self.VL_AE.addWidget(self.table_AE_activity)
            self.VL_AE.addWidget(self.label_ae_tech_in)
            self.VL_AE.addWidget(self.table_AE_technosphere)
            self.VL_AE.addWidget(self.label_ae_bio_in)
            self.VL_AE.addWidget(self.table_AE_biosphere)
            self.VL_AE.addLayout(self.HL_AE_actions)
            # AE widget
            self.widget_AE = QtGui.QWidget()
            self.widget_AE.setLayout(self.VL_AE)
            self.tab_widget_RIGHT.addTab(self.widget_AE, "Activity Editor")
            # Connections
            self.table_AE_technosphere.itemDoubleClicked.connect(self.gotoDoubleClickActivity)
            self.table_AE_activity.itemChanged.connect(self.change_values_activity)
            self.table_AE_technosphere.itemChanged.connect(self.change_values_technosphere)
            self.table_AE_biosphere.itemChanged.connect(self.change_values_biosphere)
            self.button_save.clicked.connect(self.save_edited_activity)
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

    def setUpPSSEditor(self):
        if hasattr(self, 'PSS_Widget'):
            print "PSS WIDGET ALREADY LOADED"
        else:
            self.PSS_Widget = pssWidget()
            self.tab_widget_LEFT.addTab(self.PSS_Widget.PSSdataWidget, "PSS")
            self.tab_widget_LEFT.addTab(self.PSS_Widget.table_PSS_database, "PSS database")
            self.tab_widget_LEFT.addTab(self.PSS_Widget.PP_analyzer, "PP Analyzer")
            self.VL_LEFT.addLayout(self.PSS_Widget.HL_PSS_buttons)
            self.VL_LEFT.addLayout(self.PSS_Widget.HL_PSS_Database_buttons)
            self.tab_widget_RIGHT.addTab(self.PSS_Widget.webview, "Graph")
            # CONTEXT MENUS
            # Technosphere Inputs
            self.action_addParentToPSS = QtGui.QAction("--> Process Subsystem", None)
            self.action_addParentToPSS.triggered.connect(self.add_Parent_to_chain)
            self.table_inputs_technosphere.addAction(self.action_addParentToPSS)
            # Downstream Activities
            self.action_addChildToPSS = QtGui.QAction("--> Process Subsystem", None)
            self.action_addChildToPSS.triggered.connect(self.add_Child_to_chain)
            self.table_downstream_activities.addAction(self.action_addChildToPSS)
            # Multi-Purpose Table
            self.action_addToPSS = QtGui.QAction("--> Process Subsystem", None)
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
        self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_multipurpose))

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
            self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_multipurpose))
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
                self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_multipurpose))
        except AttributeError:
            self.statusBar().showMessage("Need to load a database first")
        except:
            self.statusBar().showMessage("This did not work.")

    def load_new_current_activity(self, key=None):
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
            self.load_new_current_activity(item.activity_or_database_key)
            self.label_current_database.setText(QtCore.QString(item.activity_or_database_key[0]))
        else:  # database
            tic = time.clock()
            self.statusBar().showMessage("Loading... "+item.activity_or_database_key)
            print "Loading Database:", item.activity_or_database_key
            self.lcaData.loadDatabase(item.activity_or_database_key)
            self.statusBar().showMessage(str("Database loaded: {0} in {1:.2f} seconds.").format(item.activity_or_database_key, (time.clock()-tic)))
            self.label_current_database.setText(QtCore.QString(item.activity_or_database_key))

    def edit_activity(self):
        if self.lcaData.currentActivity:
            self.setUpActivityEditor()
            self.lcaData.set_edit_activity(self.lcaData.currentActivity)
            self.update_AE_tables()
            self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.widget_AE))

    def add_technosphere_exchange(self):
        self.lcaData.add_exchange(self.table_inputs_technosphere.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def add_downstream_exchange(self):
        self.lcaData.add_exchange(self.table_downstream_activities.currentItem().activity_or_database_key)
        self.update_AE_tables()

    def add_multipurpose_exchange(self):
        self.lcaData.add_exchange(self.table_multipurpose.currentItem().activity_or_database_key)
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

    def save_edited_activity(self):
        values = self.lcaData.editActivity_values
        db_name = str(self.combo_databases.currentText())
        key = (unicode(db_name), unicode(uuid.uuid4().urn[9:]))
        if str(self.table_AE_activity.item(0, 0).text()):
            name = str(self.table_AE_activity.item(0, 0).text())  # ref product
        else:
            name = str(self.table_AE_activity.item(0, 1).text())  # activity name
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
        self.statusBar().showMessage("Saved activity. Key: " + str(key))

    def delete_activity(self):
        key = self.table_multipurpose.currentItem().activity_or_database_key
        if key[0] not in self.read_only_databases:
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

    def showHistory(self):
        keys = self.get_table_headers(type="history")
        data = self.lcaData.getHistory()
        self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
        label_text = "History"
        self.label_multi_purpose.setText(QtCore.QString(label_text))
        self.tab_widget_RIGHT.setCurrentIndex(self.tab_widget_RIGHT.indexOf(self.table_multipurpose))

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
    mw.load_new_current_activity()

    # wnd.resize(800, 600)
    mw.showMaximized()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


