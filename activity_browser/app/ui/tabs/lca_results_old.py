# -*- coding: utf-8 -*-
from ..style import horizontal_line, vertical_line, header
from ..tables import LCAResultsTable
from activity_browser.app.ui.tables.lca_results import InventoryTable
from ..graphics import (
    CorrelationPlot,
    LCAResultsPlot,
    ProcessContributionPlot,
    # ElementaryFlowContributionPlot,
)
from ...bwutils.multilca import MLCA
from ...bwutils import commontasks as bc


from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QRadioButton, QSlider, \
    QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator

from ...signals import signals

class ImpactAssessmentTab(QWidget):
    def __init__(self, parent):
        super(ImpactAssessmentTab, self).__init__(parent)
        self.panel = parent  # e.g. right panel
        self.setVisible(False)
        self.visible = False

        # Calculate the LCA data
        self.single_lca = bool
        self.single_method = bool
        self.calculate_data()

        # Generate plots and tables
        self.results_table = LCAResultsTable()
        self.results_plot = LCAResultsPlot(self)

        self.process_contribution_table = None
        self.process_contribution_plot = ProcessContributionPlot(self)

        self.elementary_flow_contribution_table = None
        # self.elementary_flow_contribution_plot = ElementaryFlowContributionPlot(self)

        self.correlation_table = None
        self.correlation_plot = CorrelationPlot(self)

        self.Inventory_table = InventoryTable()
        self.Inventory_plot = None

        # Generate tabs
        self.tabs = QTabWidget()
        self.tabs.setTabShape(1)  # Triangular-shaped Tabs
        self.tabs.setTabPosition(1)  # South-facing Tabs

        # Default tab settings: combobox_list=False, cutoff=False, export=True
        # TabPanel(self.tabs, "LCIA Results",
        #          table=self.results_table,
        #          graph=self.results_plot)
        # TabPanel(self.tabs, "Process Contributions",
        #          table=self.process_contribution_table,
        #          graph=self.process_contribution_plot,
        #          combobox_list=True,
        #          cutoff=True,)
        # # TabPanel(self.tabs, "Elementary Flow Contributions",
        # #          table=self.elementary_flow_contribution_table,
        # #          graph=self.elementary_flow_contribution_plot,
        # #          combobox_list=True,
        # #          cutoff=True)
        # TabPanel(self.tabs, "Correlations",
        #          table=self.correlation_table,
        #          graph=self.correlation_plot)
        # TabPanel(self.tabs, "Inventory",
        #          table=self.Inventory_table,
        #          graph=self.Inventory_plot,
        #          export=False)

        # Generate layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

    def calculate_data(self):
        """ Wrap remove_tab, calculate and add_tab. """
        signals.project_selected.connect(self.remove_tab)
        signals.lca_calculation.connect(self.calculate)
        signals.lca_calculation.connect(self.add_tab)

    def add_tab(self, name):
        """ Add the LCA Results tab to the right panel of AB. """
        if not self.visible:
            self.visible = True
            self.panel.addTab(self, name)
        self.panel.select_tab(self)  # put tab to front after LCA calculation

    def remove_tab(self):
        """ Remove the LCA results tab. """
        if self.visible:
            self.visible = False
            self.panel.removeTab(self.panel.indexOf(self))

    def calculate(self, name):
        """ Calculate the (M)LCA and generate plots and tables. """
        # LCA Results Analysis: (ideas to implement)
        # - LCA score: Barchart (choice LCIA method)
        # - Contribution Analysis (choice process, LCIA method;
        #   THEN BY process, product, geography, ISIC sector)
        #   ALSO: Type of graph: Barchart, Treemap, Piechart, Worldmap (for geo)
        #   CUTOFF
        # - Uncertainties: Monte Carlo, Latin-Hypercube

        # Multi-LCA calculation
        self.mlca = MLCA(name)
        # self.single_lca = len(self.mlca.func_units) == 1
        # self.single_method = len(self.mlca.methods) == 1
        # signals.mlca_results.emit(self.mlca)

#
# class TabPanel(QTabWidget):
#     def __init__(self, tabs, name, table, graph, combobox_list=False, cutoff=False, export=True):
#         super(TabPanel, self).__init__()
#
#         # Generate generic tab items
#         self.tab_layout = QVBoxLayout()
#         self.setLayout(self.tab_layout)
#
#         self.tabs = tabs
#         self.name = name
#         self.table = table
#         self.graph = graph
#         self.combobox_list = combobox_list
#         self.cutoff = cutoff
#         self.export = export
#         self.mlca = object
#
#         # Generate Cut-off menu
#         self.cutoff_menu = QHBoxLayout()
#         if cutoff:
#             # Cut-off types
#             self.cutoff_type = QVBoxLayout()
#             self.cutoff_type_label = QLabel("Cut-off type")
#             self.cutoff_type_absolute = QRadioButton("Absolute")
#             self.cutoff_type_absolute.setChecked(True)
#             self.cutoff_type_relative = QRadioButton("Relative")
#             self.cutoff_type_topx = QRadioButton("Top x")
#             # Cut-off slider
#             self.cutoff_slider = QVBoxLayout()
#             self.cutoff_slider_set = QVBoxLayout()
#             self.cutoff_slider_label = QLabel("Cut-off level")
#             self.cutoff_slider_slider = QSlider(Qt.Horizontal)
#             self.cutoff_slider_slider.setMinimum(1)  # temporary
#             self.cutoff_slider_slider.setMaximum(99)  # temporary
#             self.cutoff_slider_slider.sizeHint()
#             self.cutoff_slider_minmax = QHBoxLayout()
#             self.cutoff_slider_min = QLabel(str(self.cutoff_slider_slider.minimum()))
#             self.cutoff_slider_max = QLabel(str(self.cutoff_slider_slider.maximum()))
#             self.cutoff_slider_ledit = QHBoxLayout()
#             self.cutoff_slider_line = QLineEdit()
#             self.cutoff_validator = QIntValidator(self.cutoff_slider_line)
#             self.cutoff_slider_line.setValidator(self.cutoff_validator)
#             self.cutoff_value = int()  # set to max when known how to port data to this class
#             self.cutoff_slider_unit = QLabel("unit")
#
#         # Generate Combobox for method selection
#         self.combobox_menu = QHBoxLayout()
#         if combobox_list:
#             self.combobox_menu_label = QLabel("Assesment method: ")
#             self.combobox_menu_combobox = QComboBox()
#             self.combobox_menu_combobox.scroll = False
#             # add stuff for in the box
#
#         # Generate Table and Graph area
#         self.main_space = QScrollArea()
#         self.main_space_widget = QWidget()
#         self.main_space_widget_layout = QVBoxLayout()
#         self.main_space_widget.setLayout(self.main_space_widget_layout)
#         self.main_space.setWidget(self.main_space_widget)
#         self.main_space.setWidgetResizable(True)
#         # Option switch
#         self.main_space_tb_grph = QHBoxLayout()
#         self.main_space_tb_grph_table = QCheckBox("Table")
#         self.main_space_tb_grph_table.setChecked(True)
#         self.main_space_tb_grph_graph = QCheckBox("Graph")
#         self.main_space_tb_grph_graph.setChecked(True)
#         # Table
#         self.main_space_table = self.table
#         # Graph
#         self.main_space_graph = self.graph
#
#         # Generate Export buttons
#         self.export_menu = QHBoxLayout()
#         if export:
#             # Export Table
#             self.export_table = QVBoxLayout()
#             self.export_table_label = QLabel("Export table")
#             self.export_table_buttons = QHBoxLayout()
#             self.export_table_buttons_copy = QPushButton("Copy")
#             self.export_table_buttons_csv = QPushButton(".csv")
#             self.export_table_buttons_excel = QPushButton("Excel")
#             # Export Graph
#             self.export_graph = QVBoxLayout()
#             self.export_graph_label = QLabel("Export graph")
#             self.export_graph_buttons = QHBoxLayout()
#             self.export_graph_buttons_png = QPushButton(".png")
#             self.export_graph_buttons_svg = QPushButton(".svg")
#
#         # Assemble complete tab panel and add to tabs
#         if cutoff:
#             self.assemble_cutoff()
#         if combobox_list:
#             self.assemble_combobox()
#         self.assemble_main_space()
#         if export:
#             self.assemble_export()
#         self.assemble_panel(cutoff, combobox_list, export)
#
#         self.tabs.addTab(self, name)
#
#         # Connect signals
#         self.connect_signals()
#
#     def connect_signals(self):
#         """ Connect all signals relevant to specific LCA Results tab. """
#         # Receive mlca
#         signals.mlca_results.connect(self.get_mlca_results)
#
#         # Update graph and table to selected method from combobox
#         if self.combobox_list:
#             self.combobox_menu_combobox.currentTextChanged.connect(
#                 lambda name: self.get_new_combobox_list(method=name))
#
#         # Generate tables, graphs and combobox
#         signals.mlca_results.connect(self.generate_table_plot_combobox)
#
#         # Cut-off
#         if self.cutoff:
#             # Cut-off types
#             self.cutoff_type_absolute.clicked.connect(self.cutoff_type_absolute_check)
#             self.cutoff_type_relative.clicked.connect(self.cutoff_type_relative_check)
#             self.cutoff_type_topx.clicked.connect(self.cutoff_type_topx_check)
#
#             # Cut-off slider
#             self.cutoff_slider_slider.valueChanged.connect(
#                 lambda: self.cutoff_slider_check("S"))
#             self.cutoff_slider_line.textChanged.connect(
#                 lambda: self.cutoff_slider_check("L"))
#
#         # Main space checkboxes
#         if self.table and self.graph:
#             self.main_space_tb_grph_table.stateChanged.connect(
#                 lambda: self.main_space_check(self.main_space_tb_grph_table, self.main_space_tb_grph_graph))
#             self.main_space_tb_grph_graph.stateChanged.connect(
#                 lambda: self.main_space_check(self.main_space_tb_grph_table, self.main_space_tb_grph_graph))
#
#         # Export Table
#         if self.table and self.export:
#             self.export_table_buttons_copy.clicked.connect(self.table.to_clipboard)
#             self.export_table_buttons_csv.clicked.connect(self.table.to_csv)
#             self.export_table_buttons_excel.clicked.connect(self.table.to_excel)
#
#         # Export Graph
#         if self.graph and self.export:
#             self.export_graph_buttons_png.clicked.connect(self.graph.to_png)
#             self.export_graph_buttons_svg.clicked.connect(self.graph.to_svg)
#
#     def get_mlca_results(self, mlca):
#         """ Port mlca data from ImpactAssessmentTab to sub-tab. """
#         self.mlca = mlca
#         self.method_dict = bc.get_LCIA_method_name_dict(self.mlca.methods)
#
#         if self.combobox_list:
#             self.combobox_menu_combobox.clear()
#             self.combobox_list = list(self.method_dict.keys())
#             self.combobox_menu_combobox.insertItems(0, self.combobox_list)
#
#     def generate_table_plot_combobox(self):
#         """ Populate the relevant tables, graphs and comboboxes. """
#         if self.name == "LCIA Results":
#             if self.table:
#                 self.table.sync(self.mlca)
#             if self.graph:
#                 self.graph.plot(self.mlca)
#
#         elif self.name == "Process Contributions":
#             if self.table:
#                 self.table = False
#             if self.graph:
#                 self.graph.plot(self.mlca, method=self.mlca.methods[0])
#
#         elif self.name == "Elementary Flow Contributions":
#             if self.table:
#                 self.table = False
#             if self.graph:
#                 self.graph.plot(self.mlca, method=self.mlca.methods[0])
#
#         elif self.name == "Correlations":
#             if self.table:
#                 self.table = False
#             if self.graph:
#                 labels = [str(x + 1) for x in range(len(self.mlca.func_units))]
#                 self.graph.plot(self.mlca, labels)
#
#         elif self.name == "Inventory":
#             if self.table:
#                 pass
#                 # self.table.sync(self.mlca)
#             if self.graph:
#                 self.graph = None
#                 #labels = [str(x + 1) for x in range(len(self.mlca.func_units))]
#                 #self.graph.plot(self.mlca, labels)
#
#         if self.combobox_list:
#             self.method_dict = bc.get_LCIA_method_name_dict(self.mlca.methods)
#             self.combobox_menu_combobox.clear()
#             self.combobox_list = list(self.method_dict.keys())
#             self.combobox_menu_combobox.insertItems(0, self.combobox_list)
#
#     def get_new_combobox_list(self, method=None):
#         """ Update the plot with method selected from combobox. """
#         if not method:
#             method = next(iter(self.mlca.method_dict.keys()))
#         else:
#             method = self.method_dict[method]
#
#         self.graph.plot(self.mlca, method=method)
#
#     def cutoff_type_absolute_check(self):
#         """ Work in progress. """
#         # set cutoff to some number
#         self.cutoff_slider_unit.setText("absolute selected, functionality to be added later")
#
#     def cutoff_type_relative_check(self):
#         """ Work in progress. """
#         # set cutoff to some %
#         self.cutoff_slider_unit.setText("relative selected, functionality to be added later")
#
#     def cutoff_type_topx_check(self):
#         """ Work in progress. """
#         # set cutoff to some number
#         self.cutoff_slider_unit.setText("topx selected, functionality to be added later")
#
#     def set_cutoff(self):
#         pass
#
#     def cutoff_slider_check(self, editor):
#         """ Update the slider and line-edit field when either one changes. """
#         cutoff = int
#         if editor == "S":
#             cutoff = abs(int(self.cutoff_slider_slider.value()))
#             self.cutoff_slider_line.setText(str(cutoff))
#         elif editor == "L":
#             if self.cutoff_slider_line.text() == '-':
#                 cutoff = self.cutoff_slider_slider.minimum()
#                 self.cutoff_slider_line.setText(str(self.cutoff_slider_slider.minimum()))
#             elif self.cutoff_slider_line.text() == '':
#                 cutoff = self.cutoff_slider_slider.minimum()
#             else:
#                 cutoff = abs(int(self.cutoff_slider_line.text()))
#
#             if cutoff > self.cutoff_slider_slider.maximum():
#                 cutoff = self.cutoff_slider_slider.maximum()
#                 self.cutoff_slider_line.setText(str(cutoff))
#             self.cutoff_slider_slider.setValue(int(cutoff))
#         self.cutoff_value = cutoff
#
#     def main_space_check(self, table_ch, graph_ch):
#         """ Show graph or table and related export functions, dependent on which is selected. """
#         table_state = table_ch.isChecked()
#         graph_state = graph_ch.isChecked()
#
#         if table_state and graph_state:
#             self.main_space_table.setVisible(True)
#             self.main_space_graph.setVisible(True)
#
#             self.export_table_label.setVisible(True)
#             self.export_table_buttons_copy.setVisible(True)
#             self.export_table_buttons_csv.setVisible(True)
#             self.export_table_buttons_excel.setVisible(True)
#             self.export_menu_vert_line.setVisible(True)
#             self.export_graph_label.setVisible(True)
#             self.export_graph_buttons_png.setVisible(True)
#             self.export_graph_buttons_svg.setVisible(True)
#         elif not table_state and graph_state:
#             self.main_space_table.setVisible(False)
#             self.main_space_graph.setVisible(True)
#
#             self.export_table_label.setVisible(False)
#             self.export_table_buttons_copy.setVisible(False)
#             self.export_table_buttons_csv.setVisible(False)
#             self.export_table_buttons_excel.setVisible(False)
#             self.export_menu_vert_line.setVisible(False)
#             self.export_graph_label.setVisible(True)
#             self.export_graph_buttons_png.setVisible(True)
#             self.export_graph_buttons_svg.setVisible(True)
#         else:
#             self.main_space_tb_grph_table.setChecked(True)
#             self.main_space_table.setVisible(True)
#             self.main_space_graph.setVisible(False)
#
#             self.export_table_label.setVisible(True)
#             self.export_table_buttons_copy.setVisible(True)
#             self.export_table_buttons_csv.setVisible(True)
#             self.export_table_buttons_excel.setVisible(True)
#             self.export_menu_vert_line.setVisible(False)
#             self.export_graph_label.setVisible(False)
#             self.export_graph_buttons_png.setVisible(False)
#             self.export_graph_buttons_svg.setVisible(False)
#
#     def assemble_cutoff(self):
#         """ Assemble the cut-off section of the tab. """
#         # Assemble types
#         self.cutoff_type.addWidget(self.cutoff_type_label)
#         self.cutoff_type.addWidget(self.cutoff_type_absolute)
#         self.cutoff_type.addWidget(self.cutoff_type_relative)
#         self.cutoff_type.addWidget(self.cutoff_type_topx)
#
#         # Assemble slider set
#         self.cutoff_slider_set.addWidget(self.cutoff_slider_label)
#         self.cutoff_slider_set.addWidget(self.cutoff_slider_slider)
#         self.cutoff_slider_minmax.addWidget(self.cutoff_slider_min)
#         self.cutoff_slider_minmax.addStretch()
#         self.cutoff_slider_minmax.addWidget(self.cutoff_slider_max)
#         self.cutoff_slider_set.addLayout(self.cutoff_slider_minmax)
#
#         self.cutoff_slider_ledit.addWidget(self.cutoff_slider_line)
#         self.cutoff_slider_ledit.addWidget(self.cutoff_slider_unit)
#         self.cutoff_slider_ledit.addStretch(1)
#
#         self.cutoff_slider.addLayout(self.cutoff_slider_set)
#         self.cutoff_slider.addLayout(self.cutoff_slider_ledit)
#
#         # Assemble cut-off menu
#         self.cutoff_menu.addLayout(self.cutoff_type)
#         self.cutoff_menu.addWidget(vertical_line())
#         self.cutoff_menu.addLayout(self.cutoff_slider)
#         self.cutoff_menu.addStretch()
#
#     def assemble_combobox(self):
#         """ Assemble the combobox section of the tab. """
#         self.combobox_menu.addWidget(self.combobox_menu_label)
#         self.combobox_menu.addWidget(self.combobox_menu_combobox, 1)
#         self.combobox_menu.addStretch(1)
#
#     def assemble_main_space(self):
#         """ Assemble the main space section of the tab. """
#         # Assemble option switch
#         self.main_space_tb_grph.addWidget(self.main_space_tb_grph_table)
#         self.main_space_tb_grph.addWidget(self.main_space_tb_grph_graph)
#         self.main_space_tb_grph.addStretch()
#
#         # Assemble Table and Graph area
#         if self.table and self.graph:
#             self.main_space_widget_layout.addLayout(self.main_space_tb_grph)
#         if self.table:
#             self.main_space_widget_layout.addWidget(self.main_space_table)
#         if self.graph:
#             self.main_space_widget_layout.addWidget(self.main_space_graph, 1)
#         self.main_space_widget_layout.addStretch()
#
#     def assemble_export(self):
#         """ Assemble the export section of the tab. """
#         # Assemble export table
#         self.export_table.addWidget(self.export_table_label)
#         self.export_table_buttons.addWidget(self.export_table_buttons_copy)
#         self.export_table_buttons.addWidget(self.export_table_buttons_csv)
#         self.export_table_buttons.addWidget(self.export_table_buttons_excel)
#         self.export_table.addLayout(self.export_table_buttons)
#
#         # Assemble export graph
#         self.export_graph.addWidget(self.export_graph_label)
#         self.export_graph_buttons.addWidget(self.export_graph_buttons_png)
#         self.export_graph_buttons.addWidget(self.export_graph_buttons_svg)
#         self.export_graph.addLayout(self.export_graph_buttons)
#
#         # Assemble export menu
#         if self.table:
#             self.export_menu.addLayout(self.export_table)
#         if self.table and self.graph:
#             self.export_menu_vert_line = vertical_line()
#             self.export_menu.addWidget(self.export_menu_vert_line)
#         if self.graph:
#             self.export_menu.addLayout(self.export_graph)
#         # self.export_menu.addLayout(self.export_table)
#         # self.export_menu_vert_line = vertical_line()
#         # self.export_menu.addWidget(self.export_menu_vert_line)
#         # self.export_menu.addLayout(self.export_graph)
#         # if self.main_space_tb_grph_table.isChecked():
#         #     self.export_table.setVisible(True)
#         #     self.export_menu_vert_line.setVisible(False)
#         #     self.export_graph.setVisible(False)
#         # elif self.main_space_tb_grph_table.isChecked() and \
#         #         self.main_space_tb_grph_graph.isChecked():
#         #     self.export_table.setVisible(True)
#         #     self.export_menu_vert_line.setVisible(True)
#         #     self.export_graph.setVisible(True)
#         # elif self.main_space_tb_grph_table.isChecked():
#         #     self.export_table.setVisible(False)
#         #     self.export_menu_vert_line.setVisible(False)
#         #     self.export_graph.setVisible(True)
#
#         self.export_menu.addStretch()
#
#     def assemble_panel(self, cutoff, combobox, export):
#         """ Assemble the tab. """
#         self.tab_layout.addWidget(header(self.name))
#         self.tab_layout.addWidget(horizontal_line())
#         if cutoff:
#             self.tab_layout.addLayout(self.cutoff_menu)
#             self.tab_layout.addWidget(horizontal_line())
#         if combobox:
#             self.tab_layout.addLayout(self.combobox_menu)
#             self.tab_layout.addWidget(horizontal_line())
#         self.tab_layout.addWidget(self.main_space)
#         if export:
#             self.tab_layout.addWidget(horizontal_line())
#             self.tab_layout.addLayout(self.export_menu)
