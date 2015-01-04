#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui, QtWebKit

from utils import *
from jinja2 import Template
import json
import pickle
import xlsxwriter
import os
from mpcreator import ProcessSubsystemCreator
from metaprocess import MetaProcess
from linkedmetaprocess import LinkedMetaProcessSystem
import numpy as np
import itertools
import networkx as nx  # TODO get rid of this dependency?
import pprint
import operator

class MPWidget(QtGui.QWidget):
    signal_activity_key = QtCore.pyqtSignal(MyQTableWidgetItem)
    signal_status_bar_message = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super(MPWidget, self).__init__(parent)
        self.PSC = ProcessSubsystemCreator()
        self.lmp = LinkedMetaProcessSystem()
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
        # Checkboxes
        self.checkbox_output_based_scaling = QtGui.QCheckBox('Output based scaling (default)')
        self.checkbox_output_based_scaling.setChecked(True)
        # PSS data
        VL_PSS_data = QtGui.QVBoxLayout()
        self.PSSdataWidget.setLayout(VL_PSS_data)
        self.line_edit_PSS_name = QtGui.QLineEdit(self.PSC.pss.name)
        VL_PSS_data.addWidget(self.line_edit_PSS_name)
        VL_PSS_data.addWidget(self.checkbox_output_based_scaling)
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
        self.checkbox_output_based_scaling.stateChanged.connect(self.set_output_based_scaling)
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
        # Labels
        label_functional_unit = QtGui.QLabel("Functional Unit:")
        self.label_FU_unit = QtGui.QLabel("unit")
        # Line edits
        self.line_edit_FU = QtGui.QLineEdit("1.0")
        # Buttons
        self.button_PP_lca = QtGui.QPushButton("LCA")
        self.button_PP_pathways = QtGui.QPushButton("Pathways")
        self.button_PP_lca_pathways = QtGui.QPushButton("LCA-Pathways")
        # Dropdown
        self.combo_functional_unit = QtGui.QComboBox(self)
        self.combo_functional_unit.setMinimumWidth(200)
        self.combo_lcia_method = QtGui.QComboBox(self)
        # Tables
        self.table_PP_comparison = QtGui.QTableWidget()
        # HL
        self.HL_functional_unit = QtGui.QHBoxLayout()
        self.HL_functional_unit.setAlignment(QtCore.Qt.AlignLeft)
        self.HL_functional_unit.addWidget(label_functional_unit)
        self.HL_functional_unit.addWidget(self.line_edit_FU)
        self.HL_functional_unit.addWidget(self.label_FU_unit)
        self.HL_functional_unit.addWidget(self.combo_functional_unit)

        self.HL_PP_analysis = QtGui.QHBoxLayout()
        self.HL_PP_analysis.setAlignment(QtCore.Qt.AlignLeft)
        self.HL_PP_analysis.addWidget(self.button_PP_lca)
        self.HL_PP_analysis.addWidget(self.button_PP_pathways)
        self.HL_PP_analysis.addWidget(self.button_PP_lca_pathways)
        self.HL_PP_analysis.addWidget(self.combo_lcia_method)
        self.combo_lcia_method.addItem(str((u'IPCC 2007', u'climate change', u'GWP 100a')))
        # VL
        self.VL_PP_analyzer = QtGui.QVBoxLayout()
        self.VL_PP_analyzer.addLayout(self.HL_functional_unit)
        self.VL_PP_analyzer.addLayout(self.HL_PP_analysis)
        self.VL_PP_analyzer.addWidget(self.table_PP_comparison)
        self.PP_analyzer.setLayout(self.VL_PP_analyzer)
        # Connections
        self.button_PP_pathways.clicked.connect(self.show_all_pathways)
        self.button_PP_lca.clicked.connect(self.get_meta_process_lcas)
        self.button_PP_lca_pathways.clicked.connect(self.compare_pathway_lcas)
        self.combo_functional_unit.currentIndexChanged.connect(self.update_FU_unit)
        self.table_PP_comparison.itemSelectionChanged.connect(self.show_path_graph)

    # MP DATABASE

    def loadPSSDatabase(self, mode="load new"):
        file_types = "Pickle (*.pickle);;All (*.*)"
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Open File', '.\MetaProcessDatabases', file_types)
        if filename:
            print "Load mode: " + str(mode)
            if mode == "load new" or not mode:  # if called via connect: mode = False
                self.lmp.load_from_file(filename)
            elif mode == "append":
                self.lmp.load_from_file(filename, append=True)
            self.signal_status_bar_message.emit("Loaded PSS Database successfully.")
            self.updateTablePSSDatabase()

    def addPSSDatabase(self):
        self.loadPSSDatabase(mode="append")

    def closePSSDatabase(self):
        msg = "If you close the database, all unsaved Data will be lost. Continue?"
        reply = QtGui.QMessageBox.question(self, 'Message',
                    msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            self.lmp = LinkedMetaProcessSystem()
            self.updateTablePSSDatabase()
            self.signal_status_bar_message.emit("Closed PSS Database.")

    def savePSSDatabase(self, filename=None):
        self.lmp.save_to_file(filename)
        self.signal_status_bar_message.emit("PSS Database saved.")
        # self.updateTablePSSDatabase()

    def saveAsPSSDatabase(self):
        if self.lmp.mp_list:
            file_types = "Pickle (*.pickle);;All (*.*)"
            filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '.\MetaProcessDatabases', file_types)
            if filename:
                self.savePSSDatabase(filename)
                self.signal_status_bar_message.emit("PSS Database saved.")

    def export_as_JSON(self):
        outdata = []
        for mp_data in self.lmp.raw_data:
            outdata.append(self.PSC.getHumanReadiblePSS(mp_data))
        file_types = "Python (*.py);;JSON (*.json);;All (*.*)"
        filename = QtGui.QFileDialog.getSaveFileName(self, 'Save File', '.\MetaProcessDatabases', file_types)
        with open(filename, 'w') as outfile:
            json.dump(outdata, outfile, indent=4, sort_keys=True)

    def updateTablePSSDatabase(self):
        data = []
        for mp_data in self.lmp.raw_data:
            numbers = [len(mp_data['outputs']), len(set(mp_data['chain'])), len(set(mp_data['cuts']))]
            data.append({
                'name': mp_data['name'],
                'out/chain/cuts': "/".join(map(str, numbers)),
                'outputs': ", ".join([o[1] for o in mp_data['outputs']]),
                'chain': "//".join([self.PSC.getActivityData(o)['name'] for o in mp_data['chain']]),
                'cuts': ", ".join([o[2] for o in mp_data['cuts']]),
            })
        keys = ['name', 'out/chain/cuts', 'outputs', 'cuts', 'chain']
        self.table_PSS_database = self.helper.update_table(self.table_PSS_database, data, keys)

    # MP <--> MP DATABASE

    def loadPSS(self):
        item = self.table_PSS_database.currentItem()
        for pss in self.lmp.raw_data:
            if pss['name'] == str(item.text()):
                self.PSC.load_pss(pss)
        self.signal_status_bar_message.emit("Loaded PSS: " + str(item.text()))
        self.showGraph()

    def addPSStoDatabase(self):
        if self.PSC.pss_data['chain']:
            add = False
            mp_name = self.PSC.pss_data['name']
            if mp_name not in self.lmp.processes:
                add = True
            else:
                mgs = "Do you want to overwrite the existing PSS?"
                reply = QtGui.QMessageBox.question(self, 'Message',
                            mgs, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                    add = True
                    self.lmp.remove_mp(mp_name)  # first remove pss that is to be replaced
            if add:
                self.lmp.add_mp([self.PSC.pss_data])
                self.update_widget_PSS_data()
                self.signal_status_bar_message.emit("Added PSS to working database (not saved).")

    def deletePSSfromDatabase(self):
        if self.PSC.pss_data['chain']:
            self.lmp.remove_mp([self.PSC.pss_data['name']])
            self.updateTablePSSDatabase()
            self.signal_status_bar_message.emit(str("Deleted (from working database): " + self.PSC.pss_data['name']))

    def delete_selected_PSS(self):
        processes_to_delete = [item.text() for item in self.table_PSS_database.selectedItems()]
        self.lmp.remove_mp(processes_to_delete)
        print "Deleted from working PSS database: " + processes_to_delete
        self.updateTablePSSDatabase()
        self.signal_status_bar_message.emit("Deleted selected items.")

    # MP

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

    def set_output_based_scaling(self):
        self.PSC.set_output_based_scaling(self.checkbox_output_based_scaling.isChecked())
        self.showGraph()

    def set_output_custom_data(self):

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
        elif item.column() == 1 and self.helper.is_number(text):  # quantity
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

    # MP LCA

    # UPDATING TABLES AND TREEWIDGET

    def update_widget_PSS_data(self):
        self.line_edit_PSS_name.setText(self.PSC.pss.name)
        self.updateTablePSSDatabase()
        self.update_PSS_table_widget_outputs()
        self.update_PSS_table_widget_chain()
        self.update_PSS_tree_widget_cuts()
        self.update_checkbox_output_based_scaling()

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
            # TODO: fix bug for multi-output activities (e.g. sawing): cut too high (activity scaled by several outputs)!
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

    def update_checkbox_output_based_scaling(self):
        self.checkbox_output_based_scaling.setChecked(self.PSC.pss_data['output_based_scaling'])

    def update_FU_unit(self):
        for mp in self.lmp.mp_list:
            for o in mp.outputs:
                if str(self.combo_functional_unit.currentText()) == o[1]:
                    unit = self.PSC.getActivityData(o[0])['unit']
        self.label_FU_unit.setText(QtCore.QString(unit))

    def update_PP_path_comparison_table(self, data):
        keys = ['LCA score', 'path']
        self.table_PP_comparison = self.helper.update_table(self.table_PP_comparison, data, keys)

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
            "dagre_path": os.path.join(os.getcwd(), "HTML", "dagre_graph_path.html"),
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

    def show_path_graph(self):
        item = self.table_PP_comparison.currentItem()
        template_data = {
            'height': self.webview.geometry().height(),
            'width': self.webview.geometry().width(),
            'data': json.dumps(self.get_pp_path_graph(item.path), indent=1)
        }
        self.set_webview(template_data, "dagre_path")

    def get_pp_path_graph(self, path):
        print "PATH:", path
        path_data = [pd for pd in self.path_data if path == pd['path']][0]
        print path_data

        graph_data = []
        for mp in self.lmp.mp_list:
            part_of_path = True if mp.name in path else False
            if part_of_path:
                lca_score = path_data['process contribution'][mp.name]
                lca_score_rel = path_data['relative process contribution'][mp.name]
                lca_result = "{0:.3g} ({1:.3g}%)".format(lca_score, lca_score_rel*100)

            for input in mp.cuts:
                graph_data.append({
                    'source': input[2],
                    'target': mp.name,
                    'type': 'suit',
                    'class': 'chain',  # this gets overwritten with "activity" in dagre_graph.html
                    'product_in': input[3],
                    'part_of_path': part_of_path,
                    # 'lca_score': '' if not part_of_path else lca_result,
                })
            for output in mp.outputs:
                graph_data.append({
                    'source': mp.name,
                    'target': output[1],
                    'type': 'suit',
                    'class': 'output',
                    'product_out': output[2],
                    'part_of_path': part_of_path,
                    'lca_score': '' if not part_of_path else lca_result,
                })
        return graph_data

    def show_all_pathways(self):
        functional_unit = str(self.combo_functional_unit.currentText())
        data = [{'path': p} for p in self.lmp.all_pathways(functional_unit)]
        keys = ['path']
        self.table_PP_comparison = self.helper.update_table(self.table_PP_comparison, data, keys)

    def get_meta_process_lcas(self, process_list=None, method=None):
        """
        returns dict where: keys = PSS name, value = LCA score
        """
        if not method:
            print "Using default LCIA method: (u'IPCC 2007', u'climate change', u'GWP 100a')"
            method = (u'IPCC 2007', u'climate change', u'GWP 100a')
        mapping_lca = self.lmp.lca_processes(method, process_names=process_list)
        print "\nLCA results:"
        # print mapping_lca
        for k, v in mapping_lca.items():
            print "{0}: {1:.2g}".format(k, v)
        return mapping_lca

# TODO: check if demand propagates all the way through mp.lca
    # TODO: get method from combobox
    def compare_pathway_lcas(self):
        method = (u'IPCC 2007', u'climate change', u'GWP 100a')
        demand = {str(self.combo_functional_unit.currentText()): 1.0}
        self.path_data = self.lmp.lca_alternatives(method, demand)
        self.update_PP_path_comparison_table(self.path_data)

    def get_pp_graph(self):
        graph_data = []
        for mp in self.lmp.mp_list:
            for input in mp.cuts:
                graph_data.append({
                    'source': input[2],
                    'target': mp.name,
                    'type': 'suit',
                    'class': 'chain',  # this gets overwritten with "activity" in dagre_graph.html
                    'product_in': input[3],
                    # 'lca_score': "0.555",
                })
            for output in mp.outputs:
                graph_data.append({
                    'source': mp.name,
                    'target': output[1],
                    'type': 'suit',
                    'class': 'output',
                    'product_out': output[2],
                    # 'lca_score': "0.415",
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
        self.save_pp_matrix()
        self.combo_functional_unit.clear()
        for product in self.lmp.products:
            self.combo_functional_unit.addItem(product)

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

    def save_pp_matrix(self):
        matrix, processes, products = self.lmp.get_pp_matrix()  # self.get_process_products_as_array()

        print "\nPP-MATRIX:"
        print "PROCESSES:"
        print processes
        print "PRODUCTS"
        print products
        print "MATRIX"
        print matrix

        # export pp-matrix data to pickle file
        # order processes/products by number in dictionary
        data = {
            'processes': [x[0] for x in sorted(processes.items(), key=operator.itemgetter(1))],
            'products': [x[0] for x in sorted(products.items(), key=operator.itemgetter(1))],
            'matrix': matrix,
        }
        filename = os.path.join(os.getcwd(), "MetaProcessDatabases", "pp-matrix.pickle")
        with open(filename, 'w') as output:
            pickle.dump(data, output)
        # Excel export
        try:
            self.export_pp_matrix_to_excel(processes, products, matrix)
        except:
            print "An error has occured saving the PP-Matrix as .xlsx file."
        # filename = os.path.join(os.getcwd(), "MetaProcessDatabases", "pp-matrix.json")
        # with open(filename, 'w') as outfile:
        #     json.dump(data, outfile, indent=2)

    def export_pp_matrix_to_excel(self, processes, products, matrix, filename='pp-matrix.xlsx'):
        filename = os.path.join(os.getcwd(), "MetaProcessDatabases", filename)
        workbook = xlsxwriter.Workbook(filename)
        ws = workbook.add_worksheet('pp-matrix')
        # formatting
        # border
        format_border = workbook.add_format()
        format_border.set_border(1)
        format_border.set_font_size(9)
        # border + text wrap
        format_border_text_wrap = workbook.add_format()
        format_border_text_wrap.set_text_wrap()
        format_border_text_wrap.set_border(1)
        format_border_text_wrap.set_font_size(9)
        # set column width
        ws.set_column(0, 1, width=15, cell_format=None)
        ws.set_column(1, 50, width=9, cell_format=None)
        # write data
        for i, p in enumerate(processes):  # process names
            ws.write(0, i+1, p, format_border_text_wrap)
        for i, p in enumerate(products):  # product names
            ws.write(i+1, 0, p, format_border)
        for i, row in enumerate(range(matrix.shape[0])):  # matrix
            ws.write_row(i+1, 1, matrix[i, :], format_border)
        workbook.close()

