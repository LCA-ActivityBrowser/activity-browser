#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
reload(sys)
sys.setdefaultencoding("utf-8")
from PyQt4 import QtCore, QtGui, QtWebKit
# import brightway2 as bw2
from standardTasks import BrowserStandardTasks
from processSubsystem import ProcessSubsystem
import time
from jinja2 import Template
import json
# from process import SimplifiedProcess

class MyTableQWidgetItem(QtGui.QTableWidgetItem):
    def __init__(self, parent=None):
        super(MyTableQWidgetItem, self).__init__(parent)
        self.activity_or_database_key = None
        self.key_type = None
        # self.setFlags(QtCore.Qt.ItemIsEnabled)
        # self.setFlags(QtCore.Qt.ItemIsSelectable)
        # self.setFlags(QtCore.Qt.ItemIsEditable)

class MyStandardItem(QtGui.QStandardItem):
    def __init__(self, parent=None):
        super(MyStandardItem, self).__init__(parent)
        self.activity_or_database_key = None
        self.key_type = None
        self.setEditable(False)

class HelperMethods(object):
    def __init__(self):
        pass

    def update_table(self, table, data, keys):
        """
        A generic method to fill a QTableWidget
        :param table: QTableWidget object
        :param data: list of dictionaries
        :param keys: dictionary keys that are to be displayed
        :return: QTableWidget object
        """
        if not data:
            table.setRowCount(0)
            return table
        else:
            table.blockSignals(True)
            table.setRowCount(len(data))
            table.setColumnCount(len(keys))
            table.setHorizontalHeaderLabels(keys)
            for i, d in enumerate(data):
                for j in range(len(keys)):
                    mtqwi = MyTableQWidgetItem(str(d[keys[j]]))
                    mtqwi.activity_or_database_key = d["key"]
                    mtqwi.key_type = d["key_type"]
                    table.setItem(i, j, mtqwi)
            if 'quantity' in keys:
                table.setEditTriggers(QtGui.QTableWidget.DoubleClicked)
            else:
                table.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.resizeColumnsToContents()
            table.resizeRowsToContents()
            table.blockSignals(False)
        return table

class Styles(object):
    def __init__(self):
        # BIG FONT
        self.font_big = QtGui.QFont()
        self.font_big.setPointSize(12)
        self.font_big.setBold(True)

class PSSWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(PSSWidget, self).__init__(parent)
        self.PSS = ProcessSubsystem()
        self.helper = HelperMethods()
        # Webview
        self.webview = QtWebKit.QWebView()
        # D3
        self.template = Template(open(os.path.join(os.getcwd(), "HTML", "tree_vertical.html")).read())
        self.current_d3_layout = "tree"

        # TREEWIDGETS
        self.tree_view_cuts = QtGui.QTreeView()
        self.model_tree_view_cuts = QtGui.QStandardItemModel()
        self.tree_view_cuts.setModel(self.model_tree_view_cuts)
        # TABLES
        self.table_PSS_chain = QtGui.QTableWidget()
        self.table_PSS_chain.setSortingEnabled(True)
        self.table_PSS_outputs = QtGui.QTableWidget()
        # PSS data
        VL_PSS_data = QtGui.QVBoxLayout()
        self.setLayout(VL_PSS_data)
        self.line_edit_PSS_name = QtGui.QLineEdit(self.PSS.custom_data['name'])
        VL_PSS_data.addWidget(self.line_edit_PSS_name)
        VL_PSS_data.addWidget(self.table_PSS_outputs)
        VL_PSS_data.addWidget(QtGui.QLabel("Outputs"))
        VL_PSS_data.addWidget(self.table_PSS_outputs)
        VL_PSS_data.addWidget(QtGui.QLabel("Chain"))
        VL_PSS_data.addWidget(self.table_PSS_chain)
        VL_PSS_data.addWidget(QtGui.QLabel("Cuts"))
        VL_PSS_data.addWidget(self.tree_view_cuts)
        # CONNECTIONS
        self.line_edit_PSS_name.returnPressed.connect(self.new_PSS_name)
        # self.table_PSS_chain.itemDoubleClicked.connect(self.gotoDoubleClickActivity)  # TODO: this should reconnect to Main Window components...
        self.model_tree_view_cuts.itemChanged.connect(self.updateCutCustomData)
        self.table_PSS_outputs.itemChanged.connect(self.updateOutputCustomData)
        # CONTEXT MENUS
        # Outputs
        self.table_PSS_outputs.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_remove_output_item = QtGui.QAction("remove Output", None)
        self.action_remove_output_item.triggered.connect(self.removeOutput)
        self.table_PSS_outputs.addAction(self.action_remove_output_item)
        # Chain
        self.table_PSS_chain.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_addOutput = QtGui.QAction("define as Output", None)
        self.action_addOutput.triggered.connect(self.addOutput)
        self.table_PSS_chain.addAction(self.action_addOutput)
        self.action_remove_chain_item = QtGui.QAction("remove from Process Subsystem", None)
        self.action_remove_chain_item.triggered.connect(self.removeChainItem)
        self.table_PSS_chain.addAction(self.action_remove_chain_item)

    def newProcessSubsystem(self, key):
        if key:
        # if self.lcaData.currentActivity != None:
            self.newProcessSubsystem()
            self.showGraph()

    def addParentProcess(self, item, currentActivity):
        # print "\nCONTEXT MENU: "+self.action_addParentToPSS.text()
        # item = self.table_inputs_technosphere.currentItem()
        self.PSS.printEdgesToConsole([(item.activity_or_database_key, currentActivity)], "New Parent:")
        self.PSS.addProcess(item.activity_or_database_key, currentActivity)
        self.showGraph()

    def addChildProcess(self):
        # print "\nCONTEXT MENU: "+self.action_addChildToPSS.text()
        if self.lcaData.currentActivity:
            item = self.table_downstream_activities.currentItem()
            self.PSS_Widget.PSS.printEdgesToConsole([(self.lcaData.currentActivity, item.activity_or_database_key)], "New Child:")
            self.PSS_Widget.PSS.addProcess(self.lcaData.currentActivity, item.activity_or_database_key)
            self.showGraph()

    def addOutput(self):
        print "\nCONTEXT MENU: "+self.action_addOutput.text()
        item = self.table_PSS_chain.currentItem()
        self.PSS.linkToProcessSubsystemHead(item.activity_or_database_key)
        self.showGraph()

    def removeOutput(self):
        print "\nCONTEXT MENU: "+self.action_remove_output_item.text()
        item = self.table_PSS_outputs.currentItem()
        self.PSS.deleteProcessFromOutputs(item.activity_or_database_key)
        self.showGraph()

    def removeChainItem(self):
        print "\nCONTEXT MENU: "+self.action_remove_chain_item.text()
        item = self.table_PSS_chain.currentItem()
        self.PSS.deleteProcessFromChain(item.activity_or_database_key)
        self.showGraph()

    def new_PSS_name(self):
        name = str(self.line_edit_PSS_name.text())  # otherwise QString
        self.PSS.set_PSS_name(name)
        self.showGraph()

    def update_PSS_tree_view_cuts(self):
        def formatActivityData(ad):
            ad_list = []
            for key in keys:
                ad_list.append(ad.get(key, 'NA'))
            return ad_list
        self.model_tree_view_cuts.blockSignals(True)  # no itemChanged signals during updating
        self.model_tree_view_cuts.clear()
        keys = ['product', 'name', 'location', 'unit', 'database']
        self.model_tree_view_cuts.setHorizontalHeaderLabels(keys)
        root_node = MyStandardItem('Cuts')
        for i, cut in enumerate(self.PSS.process_subsystem['cuts']):
            if cut[0] in self.PSS.custom_data['cut names']:
                newNode = MyStandardItem(self.PSS.custom_data['cut names'][cut[0]])
            else:
                newNode = MyStandardItem("Set input name")
            newNode.activity_or_database_key = cut[0]
            newNode.setEditable(True)
            # make row with activity data
            ad = formatActivityData(self.PSS.getActivityData(cut[0]))
            cutFromNode = [MyStandardItem(str(item)) for item in ad]
            newNode.appendRow(cutFromNode)
            if cut[1] != self.PSS.custom_data['name']:  # PSS head
                ad = formatActivityData(self.PSS.getActivityData(cut[1]))
                cutToNode = [MyStandardItem(str(item)) for item in ad]
                newNode.appendRow(cutToNode)
            root_node.appendRow(newNode)
        self.model_tree_view_cuts.appendRow(root_node)
        # display options
        self.tree_view_cuts.expandAll()
        for i in range(len(keys)):
            self.tree_view_cuts.resizeColumnToContents(i)
        self.model_tree_view_cuts.blockSignals(False)  # itemChanged signals again after updating

    def updateCutCustomData(self):
        item = self.model_tree_view_cuts.itemFromIndex(self.tree_view_cuts.currentIndex())
        self.PSS.setCutName(item.activity_or_database_key, str(item.text()))

    def update_widget_PSS_data(self):
        self.update_PSS_table_widget_outputs()
        self.update_PSS_table_widget_chain()
        self.update_PSS_tree_view_cuts()

    def updateOutputCustomData(self):
        item = self.table_PSS_outputs.currentItem()
        text = str(item.text())
        key = item.activity_or_database_key
        if item.column() == 0:  # name
            print "\nChanging output NAME to: " + text
            self.PSS.setOutputName(key, text)
        elif item.column() == 1:  # quantity
            print "\nChanging output QUANTITY to: " + text
            self.PSS.setOutputQuantity(key, text)
        else:  # ignore!
            print "You don't want to change this, do you?"
            self.showGraph()

    def update_PSS_table_widget_outputs(self):
        keys = ['custom name', 'quantity', 'unit', 'product', 'name', 'location', 'database']
        data = self.getOutputsTableData()
        self.table_PSS_outputs = self.helper.update_table(self.table_PSS_outputs, data, keys)

    def update_PSS_table_widget_chain(self):
        keys = ['product', 'name', 'location', 'unit', 'database']
        data = self.getChainTableData()
        self.table_PSS_chain = self.helper.update_table(self.table_PSS_chain, data, keys)

    def getOutputsTableData(self):
        if not self.PSS.parents_children:
            return []
        else:
            outputs = self.PSS.process_subsystem['outputs']
            data = []
            for o in outputs:
                data.append(self.PSS.getActivityData(o))
            # add custom information
            for d in data:
                if d['key'] in self.PSS.custom_data['output names']:
                    # print "Custom data already available: " + d['name']
                    d.update({
                        'custom name': self.PSS.custom_data['output names'][d['key']],
                        'quantity': self.PSS.custom_data['output quantities'][d['key']],
                    })
                else:  # register default data
                    d.update({
                        'custom name': "default output",
                        'quantity': 1,
                    })
        return data

    def getChainTableData(self):
        # TODO: move to GUI / PSS widget
        if not self.PSS.parents_children:
            return []
        else:
            data = []
            parents, children = zip(*self.PSS.parents_children)
            uniqueKeys = set(parents+children)
            for key in uniqueKeys:
                if not self.PSS.custom_data['name'] in key:
                    data.append(self.PSS.getActivityData(key))
        return data

    def toggleLayout(self):
        if self.current_d3_layout == "tree":
            self.current_d3_layout = "graph"
            self.template = Template(open(os.path.join(os.getcwd(), "HTML", "force_directed_graph.html")).read())
        else:
            self.current_d3_layout = "tree"
            self.template = Template(open(os.path.join(os.getcwd(), "HTML", "tree_vertical.html")).read())
        print "New D3 layout: " + self.current_d3_layout
        self.showGraph()

    def showGraph(self):
        # print "\nCUSTOM DATA:"
        # print self.PSS_Widget.PSS.custom_data
        self.update_widget_PSS_data()
        # data needed depends on D3 layout
        # print "\nProcess Subsystem Data: "
        # print self.PSS.process_subsystem
        # print json.dumps(self.PSS.process_subsystem, indent=2)
        if self.current_d3_layout == "tree":
            template_data = {
                'data': json.dumps(self.PSS.tree_data, indent=1)
            }
            # print json.dumps(self.PSS_Widget.PSS.tree_data, indent=1)
        elif self.current_d3_layout == "graph":
            template_data = {
                'data': json.dumps(self.PSS.graph_data, indent=1)
            }
        self.webview.setHtml(self.template.render(**template_data))

class MainWindow(QtGui.QMainWindow):

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

        # set properties
        self.table_inputs_technosphere.setSortingEnabled(True)
        self.table_inputs_biosphere.setSortingEnabled(True)
        self.table_downstream_activities.setSortingEnabled(True)
        self.table_multipurpose.setSortingEnabled(True)

        # SPLITTERS
        self.splitter_right = QtGui.QSplitter(QtCore.Qt.Vertical)

        # LAYOUTS
        # V
        vlayout = QtGui.QVBoxLayout()
        self.VL_RIGHT = QtGui.QVBoxLayout()
        VL_LEFT = QtGui.QVBoxLayout()

        # H
        hlayout = QtGui.QHBoxLayout()
        HL_multi_purpose = QtGui.QHBoxLayout()

        # Search
        HL_multi_purpose.addWidget(self.line_edit_search)
        HL_multi_purpose.addWidget(button_search)
        HL_multi_purpose.addWidget(button_history)
        HL_multi_purpose.addWidget(button_databases)
        HL_multi_purpose.addWidget(button_random_activity)

        # HL Navigation
        # HL_navigation.addWidget(button_backward)
        # HL_navigation.addWidget(button_forward)

        # VL
        # LEFT
        VL_LEFT.addWidget(label_inputs)
        VL_LEFT.addWidget(self.table_inputs_technosphere)
        VL_LEFT.addWidget(self.label_current_activity_product)
        VL_LEFT.addWidget(self.label_current_activity)
        VL_LEFT.addWidget(self.label_current_database)
        VL_LEFT.addWidget(label_downstream_activities)
        VL_LEFT.addWidget(self.table_downstream_activities)

        # RIGHT
        # Tabs
        self.tab_widget = QtGui.QTabWidget()
        self.tab_widget.addTab(self.table_multipurpose, "SeHiDa")
        self.tab_widget.addTab(self.table_inputs_biosphere, "Biosphere")

        self.VL_RIGHT.addWidget(self.tab_widget)
        self.VL_RIGHT.addLayout(HL_multi_purpose)
        self.VL_RIGHT.addWidget(self.label_multi_purpose)
        widget_right_side = QtGui.QWidget()
        widget_right_side.setLayout(self.VL_RIGHT)
        self.splitter_right.addWidget(widget_right_side)
        # splitter_right.addWidget(self.PSS_Widget.webview)

        # OVERALL
        hlayout.addLayout(VL_LEFT)
        hlayout.addWidget(self.splitter_right)

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
        file = menubar.addMenu('&Tools')
        file.addAction(addPSS)

    def setUpPSSEditor(self):
        self.PSS_Widget = PSSWidget()
        self.tab_widget.addTab(self.PSS_Widget, "PSS Widget")
        self.splitter_right.addWidget(self.PSS_Widget.webview)
        # ADDING...
        # LABELS
        label_process_subsystem = QtGui.QLabel("Process Subsystem")
        # CONTEXT MENUS
        # Technosphere Inputs
        self.table_inputs_technosphere.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_addParentToPSS = QtGui.QAction("link to Process Subsystem", None)
        self.action_addParentToPSS.triggered.connect(lambda: self.PSS_Widget.addParentProcess(self.table_inputs_technosphere.currentItem(), self.lcaData.currentActivity))
        self.table_inputs_technosphere.addAction(self.action_addParentToPSS)
        # Downstream Activities
        self.table_downstream_activities.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_addChildToPSS = QtGui.QAction("link to Process Subsystem", None)
        self.action_addChildToPSS.triggered.connect(self.PSS_Widget.addChildProcess)
        self.table_downstream_activities.addAction(self.action_addChildToPSS)
        # BUTTONS
        # Process Subsystems
        button_show_process_subsystem = QtGui.QPushButton("Show")
        button_new_process_subsystem = QtGui.QPushButton("New")
        button_toggle_layout = QtGui.QPushButton("Toggle Layout")
        button_submit_PSS = QtGui.QPushButton("Submit")
        # Process Subsystem
        HL_PS_manipulation = QtGui.QHBoxLayout()
        self.VL_RIGHT.addLayout(HL_PS_manipulation)
        HL_PS_manipulation.addWidget(label_process_subsystem)
        HL_PS_manipulation.addWidget(button_show_process_subsystem)
        HL_PS_manipulation.addWidget(button_new_process_subsystem)
        HL_PS_manipulation.addWidget(button_toggle_layout)
        HL_PS_manipulation.addWidget(button_submit_PSS)
        # CONNECTIONS
        button_show_process_subsystem.clicked.connect(self.PSS_Widget.showGraph)
        button_new_process_subsystem.clicked.connect(self.PSS_Widget.newProcessSubsystem)
        button_toggle_layout.clicked.connect(self.PSS_Widget.toggleLayout)
        # self.PSS_Widget.show_graph.connect(self.PSS_Widget.webview.showGraph)


    def listDatabases(self):
        data = self.lcaData.getDatabases()
        keys = ["name", "activities", "dependencies"]
        self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
        label_text = str(len(data)) + " databases found."
        self.label_multi_purpose.setText(QtCore.QString(label_text))
        self.tab_widget.setCurrentIndex(0)

    def table_headers(self, type="technosphere"):
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
        print "Searched for:", searchString
        if searchString != "":
            try:
                keys = self.table_headers(type="search")
                data = self.lcaData.get_search_results(searchString)
                self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
                label_text = str(len(data)) + " activities found."
                self.label_multi_purpose.setText(QtCore.QString(label_text))
                self.tab_widget.setCurrentIndex(0)
            except AttributeError:
                self.statusBar().showMessage("Need to load a database first")

    def newActivity(self, key=None):
        try:
            self.lcaData.setNewCurrentActivity(key)
            keys = self.table_headers()
            self.table_inputs_technosphere = self.helper.update_table(self.table_inputs_technosphere, self.lcaData.get_exchanges(type="technosphere"), keys)
            self.table_inputs_biosphere = self.helper.update_table(self.table_inputs_biosphere, self.lcaData.get_exchanges(type="biosphere"), self.table_headers(type="biosphere"))
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
        keys = self.table_headers(type="history")
        data = self.lcaData.getHistory()
        self.table_multipurpose = self.helper.update_table(self.table_multipurpose, data, keys)
        label_text = "History"
        self.label_multi_purpose.setText(QtCore.QString(label_text))
        self.tab_widget.setCurrentIndex(0)

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
