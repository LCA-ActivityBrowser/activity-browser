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
import numpy as np
import itertools
import networkx as nx  # TODO get rid of this dependency?

class pssWidget(QtGui.QWidget):
    signal_activity_key = QtCore.pyqtSignal(MyQTableWidgetItem)
    signal_status_bar_message = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super(pssWidget, self).__init__(parent)
        self.PSC = ProcessSubsystemCreator()
        self.PSS_database = []
        self.helper = HelperMethods()
        self.setupUserInterface()
        self.set_up_PP_analyzer()

    def setupUserInterface(self):
        # PSS Widgets
        self.PSSdataWidget = QtGui.QWidget()
        # Webview
        self.webview = QtWebKit.QWebView()
        # D3
        self.template = Template(open(os.path.join(os.getcwd(), "HTML", "tree_vertical.html")).read())
        self.current_d3_layout = "dagre"
        # LABELS
        label_process_subsystem = QtGui.QLabel("Process Subsystem")
        label_PSS_database = QtGui.QLabel("PSS Database")
        # BUTTONS
        # Process Subsystems
        button_new_process_subsystem = QtGui.QPushButton("New")
        button_add_PSS_to_Database = QtGui.QPushButton("Add to DB")
        button_delete_PSS_from_Database = QtGui.QPushButton("Delete")
        button_graph = QtGui.QPushButton("Graph")
        button_toggle_layout = QtGui.QPushButton("Toggle")
        # PSS Database
        button_load_PSS_database = QtGui.QPushButton("Load DB")
        button_saveAs_PSS_database = QtGui.QPushButton("Save DB")
        button_addDB = QtGui.QPushButton("Add DB")
        button_closeDB = QtGui.QPushButton("Close DB")
        button_pp_graph = QtGui.QPushButton("PP-Graph")
        # LAYOUTS for buttons
        # Process Subsystem
        self.HL_PSS_buttons = QtGui.QHBoxLayout()
        self.HL_PSS_buttons.addWidget(label_process_subsystem)
        self.HL_PSS_buttons.addWidget(button_new_process_subsystem)
        self.HL_PSS_buttons.addWidget(button_add_PSS_to_Database)
        self.HL_PSS_buttons.addWidget(button_delete_PSS_from_Database)
        self.HL_PSS_buttons.addWidget(button_toggle_layout)
        self.HL_PSS_buttons.addWidget(button_graph)
        # PSS Database
        self.HL_PSS_Database_buttons = QtGui.QHBoxLayout()
        self.HL_PSS_Database_buttons.addWidget(label_PSS_database)
        self.HL_PSS_Database_buttons.addWidget(button_load_PSS_database)
        self.HL_PSS_Database_buttons.addWidget(button_saveAs_PSS_database)
        self.HL_PSS_Database_buttons.addWidget(button_addDB)
        self.HL_PSS_Database_buttons.addWidget(button_closeDB)
        self.HL_PSS_Database_buttons.addWidget(button_pp_graph)
        # CONNECTIONS
        button_new_process_subsystem.clicked.connect(self.newProcessSubsystem)
        button_load_PSS_database.clicked.connect(self.loadPSSDatabase)
        button_saveAs_PSS_database.clicked.connect(self.saveAsPSSDatabase)
        button_add_PSS_to_Database.clicked.connect(self.addPSStoDatabase)
        button_toggle_layout.clicked.connect(self.toggleLayout)
        button_graph.clicked.connect(self.showGraph)
        button_delete_PSS_from_Database.clicked.connect(self.deletePSSfromDatabase)
        button_addDB.clicked.connect(self.addPSSDatabase)
        button_closeDB.clicked.connect(self.closePSSDatabase)
        button_pp_graph.clicked.connect(self.pp_graph)
        # TREEWIDGETS
        self.tree_widget_cuts = QtGui.QTreeWidget()
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
        VL_PSS_data.addWidget(self.tree_widget_cuts)
        # CONNECTIONS
        self.line_edit_PSS_name.returnPressed.connect(self.set_pss_name)
        self.table_PSS_chain.itemDoubleClicked.connect(self.setNewCurrentActivity)
        self.tree_widget_cuts.itemChanged.connect(self.set_cut_custom_data)
        self.table_PSS_outputs.itemChanged.connect(self.set_output_custom_data)
        self.table_PSS_outputs.currentItemChanged.connect(self.save_text_before_edit)
        self.table_PSS_database.itemDoubleClicked.connect(self.loadPSS)
        # CONTEXT MENUS
        # Outputs
        self.table_PSS_outputs.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_addOutput = QtGui.QAction("Duplicate", None)
        self.action_addOutput.triggered.connect(self.addOutput)
        self.table_PSS_outputs.addAction(self.action_addOutput)
        self.action_removeOutput = QtGui.QAction("Remove", None)
        self.action_removeOutput.triggered.connect(self.removeOutput)
        self.table_PSS_outputs.addAction(self.action_removeOutput)
        # Chain
        self.table_PSS_chain.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_addCut = QtGui.QAction("Cut", None)
        self.action_addCut.triggered.connect(self.addCut)
        self.table_PSS_chain.addAction(self.action_addCut)
        self.action_remove_chain_item = QtGui.QAction("Remove from PSS", None)
        self.action_remove_chain_item.triggered.connect(self.removeChainItem)
        self.table_PSS_chain.addAction(self.action_remove_chain_item)
        # Cuts treeview
        self.tree_widget_cuts.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_removeCut = QtGui.QAction("Remove cut", None)
        self.action_removeCut.triggered.connect(self.deleteCut)
        self.tree_widget_cuts.addAction(self.action_removeCut)
        # PSS Database
        self.table_PSS_database.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.action_delete_selected = QtGui.QAction("Delete selected", None)
        self.action_delete_selected.triggered.connect(self.delete_selected_PSS)
        self.table_PSS_database.addAction(self.action_delete_selected)

    def set_up_PP_analyzer(self):
        self.PP_analyzer = QtGui.QWidget()
        # PP Analyzer
        self.button_PP_pathways = QtGui.QPushButton("Pathways")
        self.button_PP_lca = QtGui.QPushButton("LCA")
        self.button_PP_lca_pathways = QtGui.QPushButton("LCA-Pathways")
        # Dropdown
        self.combo_functional_unit = QtGui.QComboBox(self)
        # HL
        self.HL_functional_unit = QtGui.QHBoxLayout()
        self.HL_functional_unit.addWidget(self.combo_functional_unit)
        self.HL_functional_unit.addWidget(self.button_PP_pathways)
        self.HL_functional_unit.addWidget(self.button_PP_lca)
        self.HL_functional_unit.addWidget(self.button_PP_lca_pathways)
        # VL
        self.VL_PP_analyzer = QtGui.QVBoxLayout()
        self.VL_PP_analyzer.addLayout(self.HL_functional_unit)
        self.PP_analyzer.setLayout(self.VL_PP_analyzer)
        # Connections
        self.button_PP_pathways.clicked.connect(self.get_all_pathways_in_pp_graph)
        self.button_PP_lca.clicked.connect(self.get_all_lca_scores_in_pp_graph)
        self.button_PP_lca_pathways.clicked.connect(self.compare_pathway_lcas)

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
        self.table_PSS_database = self.helper.update_table(self.table_PSS_database, data, keys)

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

    def addOutput(self):
        item = self.table_PSS_outputs.currentItem()
        print "\nDuplicating output: " + str(item.activity_or_database_key) + " " + item.text()
        self.PSC.add_output(item.activity_or_database_key)
        self.showGraph()

    def removeOutput(self):
        item = self.table_PSS_outputs.currentItem()
        print "\nRemoving output: " + str(item.activity_or_database_key) + " " + item.text()
        key = item.activity_or_database_key
        row = self.table_PSS_outputs.currentRow()
        name = str(self.table_PSS_outputs.item(row, 0).text())
        amount = str(self.table_PSS_outputs.item(row, 1).text())
        self.PSC.remove_output(key, name, float(amount))
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
        item = self.tree_widget_cuts.itemFromIndex(self.tree_widget_cuts.currentIndex())
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
        # need this information to distinguish between outputs that have the same key
        # (makes the code a bit ugly, but outputs have no unique id)
        row = self.table_PSS_outputs.currentRow()
        name = str(self.table_PSS_outputs.item(row, 0).text())
        amount = str(self.table_PSS_outputs.item(row, 1).text())
        if item.column() == 0:  # name
            print "\nChanging output NAME to: " + text
            self.PSC.set_output_name(key, text, self.text_before_edit, float(amount))
        elif item.column() == 1 and is_number(text):  # quantity
            print "\nChanging output QUANTITY to: " + text
            self.PSC.set_output_quantity(key, float(text), name, float(self.text_before_edit))
        else:  # ignore!
            print "\nYou don't want to do this, do you?"
        self.showGraph()

    def save_text_before_edit(self):
        self.text_before_edit = str(self.table_PSS_outputs.currentItem().text())

    def set_cut_custom_data(self):
        item = self.tree_widget_cuts.itemFromIndex(self.tree_widget_cuts.currentIndex())
        self.PSC.set_cut_name(item.activity_or_database_key, str(item.text(0)))
        self.showGraph()

    # UPDATING TABLES AND TREEVIEW

    def update_widget_PSS_data(self):
        self.line_edit_PSS_name.setText(self.PSC.pss.name)
        self.updateTablePSSDatabase()
        self.update_PSS_table_widget_outputs()
        self.update_PSS_table_widget_chain()
        self.update_PSS_tree_widget_cuts()

    def update_PSS_table_widget_outputs(self):
        keys = ['custom name', 'quantity', 'unit', 'product', 'name', 'location', 'database']
        edit_keys = ['custom name', 'quantity']
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
        self.table_PSS_outputs = self.helper.update_table(self.table_PSS_outputs, data, keys, edit_keys)

    def update_PSS_table_widget_chain(self):
        keys = ['product', 'name', 'location', 'unit', 'database']
        data = [self.PSC.getActivityData(c) for c in self.PSC.pss.chain]
        self.table_PSS_chain = self.helper.update_table(self.table_PSS_chain, data, keys)

    def update_PSS_tree_widget_cuts(self):
        def formatActivityData(ad):
            ad_list = []
            for key in keys:
                ad_list.append(ad.get(key, 'NA'))
            return ad_list
        self.tree_widget_cuts.blockSignals(True)  # no itemChanged signals during updating
        self.tree_widget_cuts.clear()
        keys = ['product', 'name', 'location', 'amount', 'unit', 'database']
        self.tree_widget_cuts.setHeaderLabels(keys)
        root = MyTreeWidgetItem(self.tree_widget_cuts, ['Cuts'])

        for i, cut in enumerate(self.PSC.pss.cuts):
            try:
                cut_name = cut[2]
            except IndexError:
                cut_name = "Set input name"
            newNode = MyTreeWidgetItem(root, [cut_name])
            newNode.activity_or_database_key = cut[0]
            newNode.setFlags(newNode.flags() | QtCore.Qt.ItemIsEditable)
            # make row with activity data
            ad = formatActivityData(self.PSC.getActivityData(cut[0]))
            ad[3] = cut[3]  # set amount to that of internal_scaled_edge_with_cuts
            cutFromNode = MyTreeWidgetItem(newNode, [str(item) for item in ad])
            cutFromNode.activity_or_database_key = cut[0]
            ad = formatActivityData(self.PSC.getActivityData(cut[1]))
            ad[3] = ''  # we are only interested in the cutFromNode amount
            cutToNode = MyTreeWidgetItem(newNode, [str(item) for item in ad])

        # display and signals
        self.tree_widget_cuts.expandAll()
        for i in range(len(keys)):
            self.tree_widget_cuts.resizeColumnToContents(i)
        self.tree_widget_cuts.blockSignals(False)  # itemChanged signals again after updating
        self.tree_widget_cuts.setEditTriggers(QtGui.QTableWidget.AllEditTriggers)

    # VISUALIZATION

    def showGraph(self):
        self.update_widget_PSS_data()
        geo = self.webview.geometry()
        # data needed depends on D3 layout
        if self.current_d3_layout == "tree":
            template_data = {
                'height': geo.height(),
                'width': geo.width(),
                'data': json.dumps(self.PSC.getTreeData(), indent=1)
            }
            self.set_webview(template_data, self.current_d3_layout)
        elif self.current_d3_layout == "graph":
            template_data = {
                'height': geo.height(),
                'width': geo.width(),
                'data': json.dumps(self.PSC.getGraphData(), indent=1)
            }
            self.set_webview(template_data, self.current_d3_layout)
            print json.dumps(self.PSC.getGraphData(), indent=1)
        elif self.current_d3_layout == "dagre":
            template_data = self.PSC.get_dagre_data()
            self.set_webview(template_data, self.current_d3_layout)

    def set_webview(self, template_data, template_name):
        templates = {
            "tree": os.path.join(os.getcwd(), "HTML", "tree_vertical.html"),
            "graph": os.path.join(os.getcwd(), "HTML", "force_directed_graph.html"),
            "dagre": os.path.join(os.getcwd(), "HTML", "dagre_graph.html"),
            "pp_graph": os.path.join(os.getcwd(), "HTML", "force_directed_graph.html"),
        }
        filename = os.path.join(os.getcwd(), "HTML", "temp.html")
        url = QtCore.QUrl("file:///"+"/".join(filename.split("\\")))
        self.template = Template(open(templates[template_name]).read())
        with open(filename, "w") as f:
            f.write(self.template.render(**template_data))
        self.webview.load(url)

    def toggleLayout(self):
        if self.current_d3_layout == "tree":
            self.current_d3_layout = "graph"
        elif self.current_d3_layout == "graph":
            self.current_d3_layout = "dagre"
        else:
            self.current_d3_layout = "tree"
        print "Visualization as: " + self.current_d3_layout
        self.showGraph()

    def get_all_pathways_in_pp_graph(self, functional_unit=None):
        functional_unit = str(self.combo_functional_unit.currentText())
        print "\nAnalyzing all possibilities to produce: " + functional_unit
        # get subgraphs (i.e. with a square matrix)
        edge_list = []
        for d in self.get_pp_graph():
            edge_list.append((d['source'], d['target']))
        G = nx.DiGraph()
        G.add_edges_from(edge_list)
        Gr = G.reverse(copy=True)
        upstream_heads = [n for n, d in Gr.out_degree().items() if d == 0]  # all possible starting points
        print "Starting points: " + str(upstream_heads)
        unique_pathways = []
        for start in upstream_heads:
            for p in nx.all_simple_paths(G, start, functional_unit):
                unique_pathways.append(p)

        print "Unique pathways:"
        for i, p in enumerate(unique_pathways):
            print i, p

        return unique_pathways

    def get_all_lca_scores_in_pp_graph(self, method=None):
        if not method:
            method = (u'IPCC 2007', u'climate change', u'GWP 100a')
        mapping_lca = {}
        for pss_data in self.PSS_database:
            pss = ProcessSubsystem(**pss_data)
            score = pss.lca(method, factorize=False)
            mapping_lca.update({
                pss_data['name']: score,
            })
        print "\nLCA results:"
        # print mapping_lca
        for k, v in mapping_lca.items():
            print "{0}: {1:.2g}".format(k, v)

    def compare_pathway_lcas(self):

        # solve matrix (i.e. get scaling vector
        # multiply scaling vector with LCA results for each PSS
        unique_paths = self.get_all_pathways_in_pp_graph()
        # build matrix
        path_data = []  # will contain dictionaries with all path results
        pss_names = [pss_data['name'] for pss_data in self.PSS_database]
        for path in unique_paths:
            # TODO: this works only if pss names and products are different!
            processes = [node for node in path if node in pss_names]
            products = [node for node in path if node not in pss_names]
            mapping_processes = dict(*[zip(sorted(processes), itertools.count())])
            mapping_products = dict(*[zip(sorted(products), itertools.count())])

            print "processes and products (in path):"
            print processes
            print products

            M = len(mapping_processes)
            matrix = np.zeros((M, M))
            # Set ones on diagonal; standard LCA stuff
            # matrix[range(M), range(M)] = 1

            # Only add edges that are within our system
            # But, allow multiple links to same product (simply add them)
            # for in_, out_, a in [x for x in edges if x[0] in chain and x[1] in chain]:
            # for product_, process_, a in [x for x in edges if x[0] in chain and x[1] in chain]:
            for process in processes:
                pss_data = [pss for pss in self.PSS_database if pss['name'] == process][0]  # there should only be unique names
                inputs = [c for c in pss_data['cuts'] if c[2] in products]
                outputs = [o for o in pss_data['outputs'] if o[1] in products]
                for i in inputs:
                    matrix[
                        mapping_products[i[2]],
                        mapping_processes[process]
                    ] -= i[3]
                for o in outputs:
                    matrix[
                        mapping_products[o[1]],
                        mapping_processes[process]
                    ] += o[2]

            path_data.append({
                'path': path,
                'matrix': matrix,
            })

        print "\nUnique pathways and matrices:"
        for p in path_data:
            for k, v in p.items():
                print k
                print v

            # demand = np.zeros((M,))

        # for a in scaling_activities:
        #     for o in [output for output in outputs if output[0] == a]:
        #         demand[mapping[a]] += o[2]
        # return mapping, matrix, np.linalg.solve(matrix, demand).tolist()

        # path_lca_scores = self.get_all_lca_scores_in_pp_graph()


    def get_pp_graph(self):
        graph_data = []
        for pss_data in self.PSS_database:
            for input in pss_data['cuts']:
                graph_data.append({
                    'source': input[2],
                    'target': pss_data['name'],
                    'type': 'suit',
                    'class': 'chain',  # this gets overwritten with "activity" in dagre_graph.html
                    'product_in': input[3],
                })
            for output in pss_data['outputs']:
                graph_data.append({
                    'source': pss_data['name'],
                    'target': output[1],
                    'type': 'suit',
                    'class': 'output',
                    'product_out': output[2],
                })
        return graph_data

    def get_pp_tree(self):
        def get_nodes(node):
            d = {}
            if node == root:
                d['name'] = node
            else:
                d['name'] = node
            parents = get_parents(node)
            if parents:
                d['children'] = [get_nodes(parent) for parent in parents]
            return d

        def get_parents(node):
            return [x[0] for x in parents_children if x[1] == node]

        # if not self.pss.chain:
        #     return []
        tree_data = []
        graph_data = self.get_pp_graph()  # source / target dicts
        parents_children = [(d['source'], d['target']) for d in graph_data]  # not using amount yet
        sources, targets = zip(*parents_children)
        head_nodes = list(set([t for t in targets if not t in sources]))

        root = "PSS database outputs"
        for head in head_nodes:
            parents_children.append((head, root))

        tree_data.append(get_nodes(root))
        return tree_data

    # OTHER METHODS

    def setNewCurrentActivity(self):
        self.signal_activity_key.emit(self.table_PSS_chain.currentItem())

    def pp_graph(self):
        processes, products, matrix = self.get_process_products_as_array()
        self.combo_functional_unit.clear()
        for product in products:
            self.combo_functional_unit.addItem(product)

        print "\nPP-MATRIX:"
        print "PROCESSES:"
        print processes
        print "PRODUCTS"
        print products
        print "MATRIX"
        print matrix

        if self.current_d3_layout == "graph" or self.current_d3_layout == "dagre":
            template_data = {
                'height': self.webview.geometry().height(),
                'width': self.webview.geometry().width(),
                'data': json.dumps(self.get_pp_graph(), indent=1)
            }
            print "\nPP-GRAPH DATA:"
            print self.get_pp_graph()

        elif self.current_d3_layout == "tree":
            template_data = {
                'height': self.webview.geometry().height(),
                'width': self.webview.geometry().width(),
                'data': json.dumps(self.get_pp_tree(), indent=1)
            }
        self.set_webview(template_data, self.current_d3_layout)

    def get_process_products_as_array(self):

        def get_processes(data):
            return sorted([x.name for x in data])

        def get_products(data):
            return sorted(set(itertools.chain(*[[x[0] for x in y.pp
                ] for y in data])))

        PSS_list = []
        for pss in self.PSS_database:
            PSS_list.append(ProcessSubsystem(**pss))
        data = PSS_list
        # Assume that process names are unique
        processes = get_processes(data)
        products = get_products(data)
        matrix = np.zeros((len(processes), len(products)))
        proc_mapping = dict(zip(processes, itertools.count()))
        prod_mapping = dict(zip(products, itertools.count()))
        for sp in data:
            for product, amount in sp.pp:
                matrix[proc_mapping[sp.name], prod_mapping[product]] = amount
        return processes, products, matrix

