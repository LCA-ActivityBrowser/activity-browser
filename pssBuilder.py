#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui, QtWebKit

from utils import *
from jinja2 import Template
import json
import pickle
import os
from processSubsystem import ProcessSubsystem

class PSSWidget(QtGui.QWidget):
    signal_activity_key = QtCore.pyqtSignal(MyTableQWidgetItem)
    signal_status_bar_message = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super(PSSWidget, self).__init__(parent)
        self.PSS = ProcessSubsystemManager()
        self.PSS_database = []
        self.helper = HelperMethods()
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
        self.action_deleteCut = QtGui.QAction("Remove cut", None)
        self.action_deleteCut.triggered.connect(self.deleteCut)
        self.table_PSS_chain.addAction(self.action_deleteCut)
        self.action_remove_chain_item = QtGui.QAction("Remove from chain", None)
        self.action_remove_chain_item.triggered.connect(self.removeChainItem)
        self.table_PSS_chain.addAction(self.action_remove_chain_item)
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
            outdata.append(self.PSS.getHumanReadiblePSS(pss))
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
                'chain': "//".join([self.PSS.getActivityData(o)['name'] for o in pss['chain']]),
                'cuts': ", ".join([o[2] for o in pss['cuts']]),
            })
        keys = ['name', 'out/chain/cuts', 'outputs', 'cuts', 'chain']
        self.table_PSS_database = self.helper.update_normal_table(self.table_PSS_database, data, keys)

    # PSS <--> PSS DATABASE

    def loadPSS(self):
        item = self.table_PSS_database.currentItem()
        for pss in self.PSS_database:
            if pss['name'] == str(item.text()):
                self.PSS.loadPSS(pss)
        self.signal_status_bar_message.emit("Loaded PSS: " + str(item.text()))
        self.showGraph()

    def addPSStoDatabase(self):
        if self.PSS.parents_children:
            self.validatePSS()
            add = False
            if self.PSS.pss['name'] not in [pss['name'] for pss in self.PSS_database]:
                add = True
            else:
                mgs = "Do you want to overwrite the existing PSS?"
                reply = QtGui.QMessageBox.question(self, 'Message',
                            mgs, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                    add = True
                    for pss in self.PSS_database:  # first remove pss that is to be replaced
                        if pss['name'] == self.PSS.pss['name']:
                            self.PSS_database.remove(pss)
            if add:
                self.PSS_database.append(self.PSS.pss)
                self.update_widget_PSS_data()
                self.signal_status_bar_message.emit("Validation successful. Added PSS to working database (not saved).")

    def deletePSSfromDatabase(self):
        if self.PSS.parents_children:
            to_be_deleted = self.PSS.custom_data['name']
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
        self.PSS.newProcessSubsystem()
        self.showGraph()

    def addToChain(self, item, currentActivity, type):
        if type == "as child":
            self.PSS.printEdgesToConsole([(currentActivity, item.activity_or_database_key)], "\nNew Child:")
            self.PSS.addProcess(currentActivity, item.activity_or_database_key)
        elif type == "as parent":
            self.PSS.printEdgesToConsole([(item.activity_or_database_key, currentActivity)], "\nNew Parent:")
            self.PSS.addProcess(item.activity_or_database_key, currentActivity)
        self.showGraph()

    def removeChainItem(self):
        print "\nCONTEXT MENU: "+self.action_remove_chain_item.text()
        item = self.table_PSS_chain.currentItem()
        self.PSS.deleteProcessFromChain(item.activity_or_database_key)
        self.showGraph()

    def addCut(self):
        print "\nCONTEXT MENU: "+self.action_addCut.text()
        item = self.table_PSS_chain.currentItem()
        self.PSS.addCut(item.activity_or_database_key)
        self.showGraph()

    def deleteCut(self):
        print "\nCONTEXT MENU: "+self.action_deleteCut.text()
        item = self.table_PSS_chain.currentItem()
        self.PSS.deleteCut(item.activity_or_database_key)
        self.showGraph()

    def set_pss_name(self):
        name = str(self.line_edit_PSS_name.text())  # otherwise QString
        self.PSS.set_PSS_name(name)
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
            self.PSS.setOutputName(key, text)
        elif item.column() == 1 and is_number(text):  # quantity
            print "\nChanging output QUANTITY to: " + text
            self.PSS.setOutputQuantity(key, text)
        else:  # ignore!
            print "\nYou don't want to do this, do you?"
            self.showGraph()

    def set_cut_custom_data(self):
        item = self.model_tree_view_cuts.itemFromIndex(self.tree_view_cuts.currentIndex())
        self.PSS.setCutName(item.activity_or_database_key, str(item.text()))

    def validatePSS(self):
        pss = self.PSS.format_data_as_pss()
        try:
            ProcessSubsystem(**pss)
            self.signal_status_bar_message.emit("Validation successful.")
        except:
            self.signal_status_bar_message.emit("Validation NOT successful.")
            print "PSS for validation:"
            ProcessSubsystem(**pss)  # to see what was the problem

    # UPDATING TABLES AND TREEVIEW

    def update_widget_PSS_data(self):
        self.line_edit_PSS_name.setText(self.PSS.custom_data['name'])
        self.updateTablePSSDatabase()
        self.update_PSS_table_widget_outputs()
        self.update_PSS_table_widget_chain()
        self.update_PSS_tree_view_cuts()

    def update_PSS_table_widget_outputs(self):
        keys = ['custom name', 'quantity', 'unit', 'product', 'name', 'location', 'database']
        data = self.getOutputsTableData()
        self.table_PSS_outputs = self.helper.update_table(self.table_PSS_outputs, data, keys)

    def getOutputsTableData(self):
        if not self.PSS.outputs:
            return []
        else:
            outputs = self.PSS.outputs
            data = []
            for o in outputs:
                data.append(self.PSS.getActivityData(o))
            # add custom information (if already available)
            CD = self.PSS.custom_data
            for d in data:
                d.update({'custom name': CD['output names'][d['key']]}) \
                    if d['key'] in CD['output names'] else d.update({'custom name': "default output"})
                d.update({'quantity': CD['output quantities'][d['key']]}) \
                    if d['key'] in CD['output quantities'] else d.update({'quantity': 1})
        return data

    def update_PSS_table_widget_chain(self):
        keys = ['product', 'name', 'location', 'unit', 'database']
        data = self.getChainTableData()
        self.table_PSS_chain = self.helper.update_table(self.table_PSS_chain, data, keys)

    def getChainTableData(self):
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
        for i, cut in enumerate(self.PSS.cuts):
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

    # VISUALIZATION

    def showGraph(self):
        print "\nPSS:"
        # print self.PSS.custom_data
        print self.PSS.pss
        self.update_widget_PSS_data()
        # data needed depends on D3 layout
        # print "\nProcess Subsystem Data: "
        # print self.PSS.process_subsystem
        # print json.dumps(self.PSS.process_subsystem, indent=2)
        geo = self.webview.geometry()
        if self.current_d3_layout == "tree":
            template_data = {
                'height': geo.height(),
                'width': geo.width(),
                'data': json.dumps(self.PSS.tree_data, indent=1)
            }
            # print json.dumps(self.PSS_Widget.PSS.tree_data, indent=1)
        elif self.current_d3_layout == "graph":
            template_data = {
                'height': geo.height(),
                'width': geo.width(),
                'data': json.dumps(self.PSS.graph_data, indent=1)
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


class ProcessSubsystemManager(BrowserStandardTasks):
    def __init__(self):
        self.parents_children = []  # flat: [(parent, child),...]
        self.outputs = []  # child keys
        self.chain = []  # unique chain item keys
        self.cuts = []  # key tuples (parent, child)
        self.custom_data = {
            'name': 'Default Process Subsystem',
            'output names': {},  # map activity key to *name*
            'output quantities': {},  # map activity key to *amount*
            'cut names': {},  # map activity key to *name*
        }
        self.pss = {}
        self.tree_data = []  # hierarchical
        self.graph_data = []  # source --> target

    def update(self):
        if not self.parents_children:
            self.outputs, self.chain, self.cuts = [], [], []
        else:
            # outputs
            self.outputs = self.getHeads()
            # chain
            parents, children = zip(*self.parents_children)
            self.chain = list(set(parents+children))
            # cuts
            if self.cuts:
                # remove false cuts (e.g. previously a cut, but now another parent node was added)
                for false_cut in [c for c in self.cuts if c[0] in children]:
                    self.cuts.remove(false_cut)
                    print "Removed cut (new parent node was added that links to this cut): "+str(false_cut)
        # pss
        self.pss = self.format_data_as_pss()
        # D3
        self.graph_data = self.getGraphData()
        self.tree_data = self.getTreeData()

    def getHeads(self):
        if self.parents_children:
            parents, children = zip(*self.parents_children)
            return list(set([c for c in children if c not in parents]))
        else:
            return []

    def newProcessSubsystem(self):
        self.parents_children, self.tree_data, self.graph_data = [], [], []
        self.update()

    def loadPSS(self, pss):
        print "Loading PSS:" + pss['name']
        # clear existing data
        self.newProcessSubsystem()
        # load and update new data (outputs, chain, cuts are determined from the edges)
        self.parents_children = pss['edges'][:]  # TODO? get edges from ProcessSubsystem self.internal_edges_with_cuts
        # load custom data
        self.custom_data['name'] = pss['name']
        for o in pss['outputs']:
            self.custom_data['output names'].update({o[0]: o[1]})
            self.custom_data['output quantities'].update({o[0]: o[2]})
        for c in pss['cuts']:
            self.cuts.append((c[0], c[1]))
            self.custom_data['cut names'].update({c[0]: c[2]})
        self.update()

    def addProcess(self, parent_key, child_key):
        if (parent_key, child_key) not in self.parents_children:
            self.parents_children.append((parent_key, child_key))
        self.update()

    def deleteProcessFromChain(self, key):
        self.printEdgesToConsole(self.parents_children, "Chain before delete:")
        parents, children = zip(*self.parents_children)
        if key in children:
            print "\nCannot remove activity as as other activities still link to it."
        elif key in parents:  # delete from chain
            for pc in self.parents_children:
                if key in pc:
                    self.parents_children.remove(pc)
            self.update()
            self.printEdgesToConsole(self.parents_children, "Chain after removal:")
        else:
            print "WARNING: Key not in chain. Key: " + self.getActivityData(key)['name']

    def addCut(self, from_key):
        parents, children = zip(*self.parents_children)
        if from_key in children:
            print "Cannot add cut. Activity is linked to by another activity."
        else:
            self.cuts = list(set(self.cuts + [pc for pc in self.parents_children if from_key == pc[0]]))
            self.update()

    def deleteCut(self, from_key):
        for cut in self.cuts:
            if from_key == cut[0]:
                self.cuts.remove(cut)
                self.update()

    def set_PSS_name(self, name):
        self.custom_data['name'] = name
        self.update()

    def setOutputName(self, key, name):
        self.custom_data['output names'].update({key: name})
        self.update()

    def setOutputQuantity(self, key, text):
        self.custom_data['output quantities'].update({key: text})
        self.update()

    def setCutName(self, key, name):
        self.custom_data['cut names'].update({key: name})
        self.update()
        
    def format_data_as_pss(self):
        outputs = []
        for i, key in enumerate(self.outputs):
            name = self.custom_data['output names'][key] if key in self.custom_data['output names'] else 'Output '+str(i)
            quantity = float(self.custom_data['output quantities'][key]) if key in self.custom_data['output quantities'] else 1.0
            outputs.append((key, name, quantity))
        # self.chain elements contain also cut parents. 
        # They need to be removed for the ProcessSubsystem as this leads to wrong LCA results.
        chain_without_cuts = [key for key in self.chain if not key in [cut[0] for cut in self.cuts]]
        cuts = []
        for i, cut in enumerate(self.cuts):
            parent, child = cut[0], cut[1]
            name = self.custom_data['cut names'][parent] if parent in self.custom_data['cut names'] else 'Cut '+str(i)
            cuts.append((parent, child, name))
        pss = {
            'name': self.custom_data['name'],
            'outputs': outputs,
            'chain': chain_without_cuts,
            'cuts': cuts,
            'edges': self.parents_children,
        }
        return pss

    # VISUALIZATION

    def getGraphData(self):
        graph_data = []
        for pc in self.parents_children:
            graph_data.append({
                'source': self.getActivityData(pc[0])['name'],
                'target': self.getActivityData(pc[1])['name'],
                'type': "suit"
            })
        # append connection to Process Subsystem
        for head in self.getHeads():
            graph_data.append({
                'source': self.getActivityData(head)['name'],
                'target': self.custom_data['name'],
                'type': "suit"
            })
        return graph_data

    def getTreeData(self):
        # TODO: rewrite using ProcessSubsystem? To apply: self.internal_scaled_edges_with_cuts
        if not self.parents_children:
            return []
        def get_nodes(node):
            d = {}
            if node == self.custom_data['name']:
                d['name'] = node
            else:
                d['name'] = self.getActivityData(node)['name']
            parents = get_parents(node)
            if parents:
                d['children'] = [get_nodes(parent) for parent in parents]
            return d
        def get_parents(node):
            return [x[0] for x in parents_children if x[1] == node]

        parents_children = self.parents_children[:]  # mutable type, therefore needs slicing
        head_nodes = self.getHeads()
        for head in head_nodes:
            parents_children.append((head, self.custom_data['name']))
        tree_data = []
        tree_data.append(get_nodes(self.custom_data['name']))
        return tree_data

    def printEdgesToConsole(self, edges_data, message=None):
        if message:
            print message
        for i, pc in enumerate(edges_data):
            if self.custom_data['name'] in pc:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+pc[1]
            else:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+self.getActivityData(pc[1])['name']

    def getHumanReadiblePSS(self, pss):
        print pss

        def getData(key):
            try:
                ad = self.getActivityData(key)
                return (ad['database'], ad['product'], ad['name'], ad['location'])
            except:
                return key

        outputs = [(getData(o[0]), o[1]) for o in pss['outputs']]
        chain = [getData(o) for o in pss['chain']]
        cuts = [(getData(o[0]), getData(o[1]), o[2]) for o in pss['cuts']]
        edges = [(getData(o[0]), getData(o[1])) for o in pss['edges']]
        pss_HR = {
            'name': pss['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
            'edges': edges,
        }
        print "\nPSS (HUMAN READIBLE):"
        print pss_HR
        return pss_HR

# TODO: remove?
    def format_data_as_pss_dagre(self):
        SP = {}
        outputs = []
        for i, key in enumerate(self.process_subsystem['outputs']):
            name = self.custom_data['output names'][key] if key in self.custom_data['output names'] else 'Output'+str(i)
            quantity = float(self.custom_data['output quantities'][key]) if key in self.custom_data['output quantities'] else 1.0
            outputs.append((self.getActivityData(key)['name'], name, quantity))
        chain = []
        for key in self.process_subsystem['chain']:
            if key != self.custom_data['name']:  # only real keys, not the head
                chain.append(self.getActivityData(key)['name'])
        cuts = []
        for i, cut in enumerate(self.process_subsystem['cuts']):
            parent, child = cut[0], cut[1]
            name = self.custom_data['cut names'][parent] if parent in self.custom_data['cut names'] else 'Cut'+str(i)
            cuts.append((self.getActivityData(parent)['name'], self.getActivityData(child)['name'], name))

        SP.update({
            'name': self.custom_data['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
        })
        print "\nPSS as SP (HUMAN READIBLE):"
        print SP
        print json.dumps(SP, indent=2)
        self.SP_dagre = SP
