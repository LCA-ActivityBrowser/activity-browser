# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets

from ..style import horizontal_line, header
from ..tables import LCAResultsTable
from ..graphics import (
    CorrelationPlot,
    LCAResultsPlot,
    ProcessContributionPlot,
    ElementaryFlowContributionPlot
)
from ...bwutils.multilca import MLCA
from ...bwutils import commontasks as bc
from ...signals import signals

from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QScrollArea


class ImpactAssessmentTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ImpactAssessmentTab, self).__init__(parent)
        self.panel = parent  # e.g. right panel
        self.setVisible(False)
        self.visible = False

        # Comboboxes
        self.combo_process_cont_methods = QtWidgets.QComboBox()
        self.combo_process_cont_methods.scroll = False
        self.combo_flow_cont_methods = QtWidgets.QComboBox()
        self.combo_flow_cont_methods.scroll = False

        # Plots & Table
        self.results_plot = LCAResultsPlot(self)
        self.correlation_plot = CorrelationPlot(self)
        self.process_contribution_plot = ProcessContributionPlot(self)
        self.elementary_flow_contribution_plot = ElementaryFlowContributionPlot(self)
        self.results_table = LCAResultsTable()

        # Buttons
        self.to_clipboard_button = QtWidgets.QPushButton('Copy')
        self.to_csv_button = QtWidgets.QPushButton('.csv')
        self.to_excel_button = QtWidgets.QPushButton('Excel')

        self.to_png_button = QtWidgets.QPushButton('png')
        self.to_svg_button = QtWidgets.QPushButton('svg')

        self.button_area = QtWidgets.QScrollArea()
        self.button_widget = QtWidgets.QWidget()
        self.button_widget_layout = QtWidgets.QVBoxLayout()

        self.button_widget.setLayout(self.button_widget_layout)
        self.button_area.setWidget(self.button_widget)
        self.button_area.setWidgetResizable(True)
        self.button_area.setFixedHeight(44)  # This is ugly, how do we make this automatic?
        self.layout = QtWidgets.QVBoxLayout()

        # Generate layout & Connect
        self.make_layout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.remove_tab)
        signals.lca_calculation.connect(self.calculate)
        self.combo_process_cont_methods.currentTextChanged.connect(
            lambda name: self.get_process_contribution(method=name))
        self.combo_flow_cont_methods.currentTextChanged.connect(
            lambda name: self.get_flow_contribution(method=name))
        self.to_clipboard_button.clicked.connect(self.results_table.to_clipboard)
        self.to_csv_button.clicked.connect(self.results_table.to_csv)
        self.to_excel_button.clicked.connect(self.results_table.to_excel)
        self.to_png_button.clicked.connect(self.results_plot.to_png)
        self.to_svg_button.clicked.connect(self.results_plot.to_svg)

    def createtab(self, Tabname, Widgets):
        Tabname.layout = QVBoxLayout()
        self.tabscroll = QtWidgets.QScrollArea()
        header_height = 17
        Widgets[0].setFixedHeight(header_height)
        if len(Widgets) == 8:
            Widgets[3].setFixedHeight(header_height)
            Widgets[6].setFixedHeight(header_height)

        self.group = QVBoxLayout()
        for i in Widgets:
            self.group.addWidget(i)
        self.tabwidget = QtWidgets.QGroupBox()
        self.tabwidget.setLayout(self.group)
        self.tabscroll.setWidget(self.tabwidget)
        self.tabscroll.setWidgetResizable(True)

        Tabname.layout.addWidget(self.tabscroll)
        Tabname.setLayout(Tabname.layout)
        return ()

    def make_layout(self):
    # TO-DO: get buttons out of the Q(H/V?)box

        # Initialize tabs as layouts
        self.tabs = QTabWidget()
        self.tabs.setTabShape(1)  # Triangular-shaped Tabs
        self.tabs.setTabPosition(1)  # South-facing Tabs
        self.tab1 = QScrollArea()
        self.tab2 = QScrollArea()
        self.tab3 = QScrollArea()
        self.tab4 = QScrollArea()

        # Add tabs
        self.tabs.addTab(self.tab1, "LCIA Results")
        self.tabs.addTab(self.tab2, "Process Contributions")
        self.tabs.addTab(self.tab3, "Elementary Flow Contributions")
        self.tabs.addTab(self.tab4, "Correlations")

        # Create export buttons
        self.buttons = QtWidgets.QHBoxLayout()
        self.buttons.addWidget(self.to_clipboard_button)
        self.buttons.addWidget(self.to_csv_button)
        self.buttons.addWidget(self.to_excel_button)
        self.buttons.addWidget(self.to_png_button)
        self.buttons.addWidget(self.to_svg_button)
        self.buttons.addStretch()

        self.button_widget_layout.addLayout(self.buttons)

        # Create first tab
        self.createtab(self.tab1, [header("LCA Scores Plot:"), horizontal_line(), self.results_plot, \
                                    header("LCA Scores Table:"), self.results_table, horizontal_line(), \
                                    header("Export"), self.button_area])

        # Create second tab
        self.createtab(self.tab2, [header("Process Contributions:"), horizontal_line(), self.combo_process_cont_methods, \
                                    self.process_contribution_plot])

        # Create third tab
        self.createtab(self.tab3, [header("Elementary Flow Contributions:"), horizontal_line(),self.combo_flow_cont_methods, \
                                   self.elementary_flow_contribution_plot])

        # Create fourth tab
        self.createtab(self.tab4, [header("LCA Scores Correlation:"), horizontal_line(), self.correlation_plot])

        # Add tabs to widget
        self.layout.addWidget(self.tabs)

    def add_tab(self):
        if not self.visible:
            self.visible = True
            self.panel.addTab(self, "LCA results")
        self.panel.select_tab(self)  # put tab to front after LCA calculation

    def remove_tab(self):
        if self.visible:
            self.visible = False
            self.panel.removeTab(self.panel.indexOf(self))

    def calculate(self, name):
        # LCA Results Analysis: (ideas to implement)
        # - LCA score: Barchart (choice LCIA method)
        # - Contribution Analysis (choice process, LCIA method;
        #   THEN BY process, product, geography, ISIC sector)
        #   ALSO: Type of graph: Barchart, Treemap, Piechart, Worldmap (for geo)
        #   CUTOFF
        # - Uncertainties: Monte Carlo, Latin-Hypercube

        # Multi-LCA calculation
        self.mlca = MLCA(name)
        single_lca = len(self.mlca.func_units) == 1
        single_method = len(self.mlca.methods) == 1

        # update process and elementary flow contribution combo boxes
        self.dict_LCIA_methods_str_tuples = bc.get_LCIA_method_name_dict(self.mlca.methods)

        self.combo_process_cont_methods.clear()
        self.combo_flow_cont_methods.clear()
        self.combo_process_cont_methods.insertItems(0, self.dict_LCIA_methods_str_tuples.keys())
        self.combo_flow_cont_methods.insertItems(0, self.dict_LCIA_methods_str_tuples.keys())
        if not single_method:
            self.combo_process_cont_methods.setVisible(True)
            self.combo_flow_cont_methods.setVisible(True)
        else:
            self.combo_process_cont_methods.setVisible(False)
            self.combo_flow_cont_methods.setVisible(False)

        # PLOTS & TABLES

        # LCA Results Plot
        self.results_plot.plot(self.mlca)
        if not single_lca:
            self.results_plot.setVisible(True)
        else:
            self.results_plot.setVisible(False)

        # Contribution Analysis
        # is plotted by the combobox signal

        # Correlation Plot
        if not single_lca:
            labels = [str(x + 1) for x in range(len(self.mlca.func_units))]
            self.correlation_plot.plot(self.mlca, labels)
            self.correlation_plot.setVisible(True)
        else:
            self.correlation_plot.setVisible(False)

        # LCA results table
        self.results_table.sync(self.mlca)

        self.add_tab()

    def get_process_contribution(self, method=None):
        if not method:
            method = next(iter(self.mlca.method_dict.keys()))
        else:
            method = self.dict_LCIA_methods_str_tuples[method]

        self.process_contribution_plot.plot(self.mlca, method=method)

    def get_flow_contribution(self, method=None):
        if not method:
            method = next(iter(self.mlca.method_dict.keys()))
        else:
            method = self.dict_LCIA_methods_str_tuples[method]

        self.elementary_flow_contribution_plot.plot(self.mlca, method=method)
