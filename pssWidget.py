#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui, QtWebKit

from utils import *
from jinja2 import Template
import json
import pickle
import os
from pssCreator import ProcessSubsystemCreator
from processSubsystem import ProcessSubsystem

class pssWidget(QtGui.QWidget):
    signal_activity_key = QtCore.pyqtSignal(MyTableQWidgetItem)
    signal_status_bar_message = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super(PSSWidget, self).__init__(parent)
        self.PSC = ProcessSubsystemCreator()
        self.PSS_database = []
        self.helper = HelperMethods()
        self.setupUserInterface()

    def setupUserInterface(self):
        # PSS Data Widget
        self.PSSdataWidget = QtGui.QWidget()
        # Webview
        self.webview = QtWebKit.QWebView()
        # D3
        self.template = Template(open(os.path.join(os.getcwd(), "HTML", "tree_vertical.html")).read())
        self.current_d3_layout = "tree"
        # LABELS
        label_process_subsystem = QtGui.QLabel("Process Subsystem")
        label_PSS_database = QtGui.QLabel("PSS Database")
        # BUTTONS
        # Process Subsystems
        button_new_process_subsystem = QtGui.QPushButton("New")
        button_add_PSS_to_Database = QtGui.QPushButton("Add to DB")
        button_delete_PSS_from_Database = QtGui.QPushButton("Delete")
        button_toggle_layout = QtGui.QPushButton("Toggle Graph")
        # PSS Database
        button_load_PSS_database = QtGui.QPushButton("Load DB")
        button_saveAs_PSS_database = QtGui.QPushButton("Save DB")
        button_addDB = QtGui.QPushButton("Add DB")
        button_closeDB = QtGui.QPushButton("Close DB")
        # LAYOUTS for buttons
        # Process Subsystem
        self.HL_PSS_buttons = QtGui.QHBoxLayout()
        self.HL_PSS_buttons.addWidget(label_process_subsystem)
        self.HL_PSS_buttons.addWidget(button_new_process_subsystem)
        self.HL_PSS_buttons.addWidget(button_add_PSS_to_Database)
        self.HL_PSS_buttons.addWidget(button_delete_PSS_from_Database)
        self.HL_PSS_buttons.addWidget(button_toggle_layout)
        # PSS Database
        self.HL_PSS_Database_buttons = QtGui.QHBoxLayout()
        self.HL_PSS_Database_buttons.addWidget(label_PSS_database)
        self.HL_PSS_Database_buttons.addWidget(button_load_PSS_database)
        self.HL_PSS_Database_buttons.addWidget(button_saveAs_PSS_database)
        self.HL_PSS_Database_buttons.addWidget(button_addDB)
        self.HL_PSS_Database_buttons.addWidget(button_closeDB)
        # CONNECTIONS
        button_new_process_subsystem.clicked.connect(self.newProcessSubsystem)
        button_load_PSS_database.clicked.connect(self.loadPSSDatabase)
        button_saveAs_PSS_database.clicked.connect(self.saveAsPSSDatabase)
        button_add_PSS_to_Database.clicked.connect(self.addPSStoDatabase)
        button_toggle_layout.clicked.connect(self.toggleLayout)
        button_delete_PSS_from_Database.clicked.connect(self.deletePSSfromDatabase)
        button_addDB.clicked.connect(self.addPSSDatabase)
        button_closeDB.clicked.connect(self.closePSSDatabase)
        # TREEWIDGETS
        self.tree_view_cuts = QtGui.QTreeView()
        self.model_tree_view_cuts = QtGui.QStandardItemModel()
        self.tree_view_cuts.setModel(self.model_tree_view_cuts)
        # TABLES
        self.table_PSS_chain = QtGui.QTableWidget()
        self.table_PSS_outputs = QtGui.QTableWidget()
        self.table_PSS_database = QtGui.QTableWidget()
        # PSS data
        VL_PSS_data = QtGui.QVBoxLayout()
        self.PSSdataWidget.setLayout(VL_PSS_data)
        self.line_edit_PSS_name = QtGui.QLineEdit(self.PSC.pss.name)
        VL_PSS_data.addWidget(self.line_edit_PSS_name)
        VL_PSS_data.addWidget(self.table_PSS_outputs)
        VL_PSS_data.addWidget(QtGui.QLabel("Outputs"))
        VL_PSS_data.addWidget(self.table_PSS_outputs)
        VL_PSS_data.addWidget(QtGui.QLabel("Chain"))
        VL_PSS_data.addWidget(self.table_PSS_chain)
        VL_PSS_data.addWidget(QtGui.QLabel("Cuts"))
        VL_PSS_data.addWidget(self.tree_view_cuts)
        # CONNECTIONS
        self.line_edit_PSS_name.returnPressed.connect(self.set_pss_name)
        self.table_PSS_chain.itemDoubleClicked.connect(self.setNewCurrentActivity)
        self.model_tree_view_cuts.itemChanged.connect(self.set_cut_custom_data)
        self.table_PSS_outputs.itemChanged.connect(self.set_output_custom_data)
        self.table_PSS_database.itemDoubleClicked.connect(self.loadPSS)
        # CONTEXT MENUS
        # Chain
        self.table_PSS_chain.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_addCut = QtGui.QAction("Cut", None)
        self.action_addCut.triggered.connect(self.addCut)
        self.table_PSS_chain.addAction(self.action_addCut)
        self.action_remove_chain_item = QtGui.QAction("Remove from PSS", None)
        self.action_remove_chain_item.triggered.connect(self.removeChainItem)
        self.table_PSS_chain.addAction(self.action_remove_chain_item)
        # Cuts treeview
        self.tree_view_cuts.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_removeCut = QtGui.QAction("Remove cut", None)
        self.action_removeCut.triggered.connect(self.deleteCut)
        self.tree_view_cuts.addAction(self.action_removeCut)
        # PSS Database
        self.table_PSS_database.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_delete_selected = QtGui.QAction("Delete selected", None)
        self.action_delete_selected.triggered.connect(self.delete_selected_PSS)
        self.table_PSS_database.addAction(self.action_delete_selected)

    # PSS DATABASE

    def loadPSSDatabase(self, mode="load new"):
        file_types = "Pickle (*.pickle);;All (*.*)"
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Open File', '.\PSS Databases', file_types)
        if filename:
            with open(filename, 'r') as input:
                PSS_database = pickle.load(input)
            print "Load mode: " + str(mode)
            if mode == "load new" or not mode:  # if called via connect: mode = False
                self.PSS_database = PSS_database
            elif mode == "append":
                # Check if conflicting names. If so, rename new pss.
                existing_names = [pss['name'] for pss in self.PSS_database]
                for new_pss in PSS_database:
                    while True:
                        if new_pss['name'] in existing_names:
                            new_pss['name'] += "__ADDED"
                        else:
                            break
                self.PSS_database = self.PSS_database + PSS_database
            # TODO: update PSS data... ?
            self.signal_status_bar_message.emit("Loaded PSS Database successfully.")
            self.updateTablePSSDatabase()

    def addPSSDatabase(self):
        self.loadPSSDatabase(mode="append")

    def closePSSDatabase(self):
        msg = "If you reset your database, all unsaved Data will be lost. Continue?"
        reply = QtGui.QMessageBox.question(self, 'Message',
                    msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            self.PSS_database = []
            self.updateTablePSSDatabase()
            self.signal_status_bar_message.emit("Reset PSS Database.")

    def savePSSDatabase(self, filename=None):
        with open(filename, 'w') as output:
            pickle.dump(self.PSS_database, output)
        self.signal_status_bar_message.emit("PSS Database saved.")
        self.updateTablePSSDatabase()

    def saveAsPSSDatabase(self):
        if self.PSS_database:
            file_types = "Pickle (*.pickle);;All (*.*)"
            filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '.\PSS Databases', file_types)
            if filename:
                self.savePSSDatabase(filename)
                self.signal_status_bar_message.emit("PSS Database saved.")

    def export_as_JSON(self):
        outdata = []
        for pss in self.PSS_database:
            outdata.append(self.PSC.getHumanReadiblePSS(pss))
        file_types = "Python (*.py);;JSON (*.json);;All (*.*)"
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '.\PSS Databases', file_types)
        with open(filename, 'w') as outfile:
            json.dump(outdata, outfile, indent=4, sort_keys=True)

    def updateTablePSSDatabase(self):
        data = []
        for pss in self.PSS_database:
            numbers = [len(pss['outputs']), len(set(pss['chain'])), len(set(pss['cuts']))]
            data.append({
                'name': pss['name'],
                'out/chain/cuts': "/".join(map(str, numbers)),
                'outputs': ", ".join([o[1] for o in pss['outputs']]),
                'chain': "//".join([self.PSC.getActivityData(o)['name'] for o in pss['chain']]),
                'cuts': ", ".join([o[2] for o in pss['cuts']]),
            })
        keys = ['name', 'out/chain/cuts', 'outputs', 'cuts', 'chain']
        self.table_PSS_database = self.helper.update_normal_table(self.table_PSS_database, data, keys)

    # PSS <--> PSS DATABASE

    def loadPSS(self):
        item = self.table_PSS_database.currentItem()
        for pss in self.PSS_database:
            if pss['name'] == str(item.text()):
                self.PSC.load_pss(pss)
        self.signal_status_bar_message.emit("Loaded PSS: " + str(item.text()))
        self.showGraph()

    def addPSStoDatabase(self):
        if self.PSC.pss_data['chain']:
            add = False
            if self.PSC.pss_data['name'] not in [pss['name'] for pss in self.PSS_database]:
                add = True
            else:
                mgs = "Do you want to overwrite the existing PSS?"
                reply = QtGui.QMessageBox.question(self, 'Message',
                            mgs, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                    add = True
                    for pss in self.PSS_database:  # first remove pss that is to be replaced
                        if pss['name'] == self.PSC.pss_data['name']:
                            self.PSS_database.remove(pss)
            if add:
                self.PSS_database.append(self.PSC.pss_data)
                self.update_widget_PSS_data()
                self.signal_status_bar_message.emit("Added PSS to working database (not saved).")

    def deletePSSfromDatabase(self):
        if self.PSC.pss_data['chain']:
            to_be_deleted = self.PSC.pss_data['name']
            self.PSS_database = [pss for pss in self.PSS_database if pss['name'] != to_be_deleted]
            self.updateTablePSSDatabase()
            self.signal_status_bar_message.emit(str("Deleted (from working database): " + to_be_deleted))

    def delete_selected_PSS(self):
        for item in self.table_PSS_database.selectedItems():
            for pss in self.PSS_database:
                if pss['name'] == item.text():
                    self.PSS_database.remove(pss)
                    print "Deleted from working PSS database: " + item.text()
        self.updateTablePSSDatabase()
        self.signal_status_bar_message.emit("Deleted selected items.")

    # PSS

    def newProcessSubsystem(self):
        self.PSC.newProcessSubsystem()
        self.showGraph()

    def addToChain(self, item):
        self.PSC.add_to_chain(item.activity_or_database_key)
        self.showGraph()

    def removeChainItem(self):
        print "\nCONTEXT MENU: "+self.action_remove_chain_item.text()
        item = self.table_PSS_chain.currentItem()
        self.PSC.delete_from_chain(item.activity_or_database_key)
        self.showGraph()

    def addCut(self):
        print "\nCONTEXT MENU: "+self.action_addCut.text()
        item = self.table_PSS_chain.currentItem()
        self.PSC.add_cut(item.activity_or_database_key)
        self.showGraph()

    def deleteCut(self):
        print "\nCONTEXT MENU: "+self.action_removeCut.text()
        item = self.model_tree_view_cuts.itemFromIndex(self.tree_view_cuts.currentIndex())
        if item.activity_or_database_key:
            self.PSC.delete_cut(item.activity_or_database_key)
            self.showGraph()

    def set_pss_name(self):
        name = str(self.line_edit_PSS_name.text())  # otherwise QString
        self.PSC.set_pss_name(name)
        self.showGraph()
        
    def set_output_custom_data(self):
        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        item = self.table_PSS_outputs.currentItem()
        text = str(item.text())
        key = item.activity_or_database_key
        if item.column() == 0:  # name
            print "\nChanging output NAME to: " + text
            self.PSC.set_output_name(key, text)
        elif item.column() == 1 and is_number(text):  # quantity
            print "\nChanging output QUANTITY to: " + text
            self.PSC.set_output_quantity(key, text)
        else:  # ignore!
            print "\nYou don't want to do this, do you?"
            self.showGraph()

    def set_cut_custom_data(self):
        item = self.model_tree_view_cuts.itemFromIndex(self.tree_view_cuts.currentIndex())
        self.PSC.set_cut_name(item.activity_or_database_key, str(item.text()))

    # UPDATING TABLES AND TREEVIEW

    def update_widget_PSS_data(self):
        self.line_edit_PSS_name.setText(self.PSC.pss.name)
        self.updateTablePSSDatabase()
        self.update_PSS_table_widget_outputs()
        self.update_PSS_table_widget_chain()
        self.update_PSS_tree_view_cuts()

    def update_PSS_table_widget_outputs(self):
        keys = ['custom name', 'quantity', 'unit', 'product', 'name', 'location', 'database']
        data = []
        if self.PSC.pss.outputs:
            for i, output in enumerate(self.PSC.pss.outputs):
                output_data = self.PSC.getActivityData(output[0])
                try:
                    output_name = output[1]
                except IndexError:
                    output_name = "Output " + str(i)
                try:
                    output_quantity = output[2]
                except IndexError:
                    output_quantity = "1"
                output_data.update({'custom name': output_name, 'quantity': output_quantity})
                data.append(output_data)
        self.table_PSS_outputs = self.helper.update_table(self.table_PSS_outputs, data, keys)

    def update_PSS_table_widget_chain(self):
        keys = ['product', 'name', 'location', 'unit', 'database']
        data = [self.PSC.getActivityData(c) for c in self.PSC.pss.chain]
        self.table_PSS_chain = self.helper.update_table(self.table_PSS_chain, data, keys)

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
        for i, cut in enumerate(self.PSC.pss.cuts):
            try:
                cut_name = cut[2]
            except IndexError:
                cut_name = "Set input name"
            newNode = MyStandardItem(cut_name)
            newNode.activity_or_database_key = cut[0]
            newNode.setEditable(True)
            # make row with activity data
            ad = formatActivityData(self.PSC.getActivityData(cut[0]))
            cutFromNode = [MyStandardItem(str(item)) for item in ad]
            for msi in cutFromNode:
                msi.activity_or_database_key = cut[0]
            newNode.appendRow(cutFromNode)
            ad = formatActivityData(self.PSC.getActivityData(cut[1]))
            cutToNode = [MyStandardItem(str(item)) for item in ad]
            newNode.appendRow(cutToNode)
            root_node.appendRow(newNode)
        self.model_tree_view_cuts.appendRow(root_node)
        # display options
        self.tree_view_cuts.expandAll()
        for i in range(len(keys)):
            self.tree_view_cuts.resizeColumnToContents(i)
        self.model_tree_view_cuts.blockSignals(False)  # itemChanged signals again after updating

    # VISUALIZATION

    def showGraph(self):
        self.update_widget_PSS_data()
        # data needed depends on D3 layout
        geo = self.webview.geometry()
        if self.current_d3_layout == "tree":
            template_data = {
                'height': geo.height(),
                'width': geo.width(),
                'data': json.dumps(self.PSC.getTreeData(), indent=1)
            }
            # print json.dumps(self.PSC_Widget.PSC.getTreeData(), indent=1)
        elif self.current_d3_layout == "graph":
            template_data = {
                'height': geo.height(),
                'width': geo.width(),
                'data': json.dumps(self.PSC.getGraphData(), indent=1)
            }
        self.webview.setHtml(self.template.render(**template_data))

    def toggleLayout(self):
        if self.current_d3_layout == "tree":
            self.current_d3_layout = "graph"
            self.template = Template(open(os.path.join(os.getcwd(), "HTML", "force_directed_graph.html")).read())
        else:
            self.current_d3_layout = "tree"
            self.template = Template(open(os.path.join(os.getcwd(), "HTML", "tree_vertical.html")).read())
        print "New D3 layout: " + self.current_d3_layout
        self.showGraph()

    # OTHER METHODS

    def setNewCurrentActivity(self):
        self.signal_activity_key.emit(self.table_PSS_chain.currentItem())
