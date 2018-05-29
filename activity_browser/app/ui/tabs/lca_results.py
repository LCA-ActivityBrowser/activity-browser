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

from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QWidget, QTabWidget, QVBoxLayout, QScrollArea


class ImpactAssessmentTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ImpactAssessmentTab, self).__init__(parent)
        self.panel = parent  # e.g. right panel
        self.setVisible(False)
        self.visible = False

        self.combo_LCIA_methods = QtWidgets.QComboBox()
        self.combo_LCIA_methods.scroll = False

        self.results_plot = LCAResultsPlot(self)
        self.correlation_plot = CorrelationPlot(self)
        self.process_contribution_plot = ProcessContributionPlot(self)
        self.elementary_flow_contribution_plot = ElementaryFlowContributionPlot(self)

        self.results_table = LCAResultsTable()

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_widget_layout = QtWidgets.QVBoxLayout()

        self.scroll_widget.setLayout(self.scroll_widget_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)

        self.layout = QtWidgets.QVBoxLayout()

        self.make_layout()

        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.remove_tab)
        signals.lca_calculation.connect(self.calculate)
        self.combo_LCIA_methods.currentTextChanged.connect(
            lambda name: self.get_contribution_analyses(method=name))

    def make_layout(self):
        # Display the information in the scroll widget

        #self.scroll_widget_layout.addWidget(header("Elementary Flow Contributions:"))
        #self.scroll_widget_layout.addWidget(horizontal_line())
        #self.scroll_widget_layout.addWidget(self.elementary_flow_contribution_plot) DONE

        #self.scroll_widget_layout.addWidget(header("LCA Scores Correlation:"))
        #self.scroll_widget_layout.addWidget(horizontal_line())
        #self.scroll_widget_layout.addWidget(self.correlation_plot) DONE

        #self.scroll_widget_layout.addWidget(header("LCA Scores:"))
        #self.scroll_widget_layout.addWidget(horizontal_line())
        #self.scroll_widget_layout.addWidget(self.results_table) DONE

        # TO-DO: make a second combobox for working in the third results tab

        # Initialize tab screen
        self.tabs = QTabWidget()

        #self.make_layout()
        #self.layout.addWidget(self.scroll_area)
        #self.setLayout(self.layout)

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

        # Create first tab
        self.tab1.layout = QVBoxLayout(self)
        #self.tab1.addScrollBarWidget(?,?,?,?)
        # QScrollArea::setWidget()
        #self.tab1.addWidget(header("LCA Scores:"))
        #self.tab1.addWidget(horizontal_line())
        #self.tab1.addWidget(self.results_plot)
        #self.scrollbar = QtWidgets.QWidget()
        #self.tab1.layout.addWidget(self.scrollbar)
        self.tab1scroll = QtWidgets.QScrollArea()
        self.tab1scroll.setWidget(self.results_plot)
        #self.tab1scroll.setWidget(self.results_table)
        self.tab1.layout.addWidget(self.tab1scroll)
        self.tab1.setLayout(self.tab1.layout)

        #self.tab1.scroll_area = QtWidgets.QScrollArea()
        #self.tab1.scroll_widget = QtWidgets.QWidget()
        #self.tab1.scroll_widget_layout = QtWidgets.QVBoxLayout()
        #self.tab1.scroll_widget.setLayout(self.tab1.scroll_widget_layout)
        #self.tab1.scroll_area.setWidget(self.tab1.scroll_widget)

        # Create second tab
        self.tab2.layout = QVBoxLayout(self)
        #self.tab2.addWidget(header("Process Contributions:"))
        #self.tab2.addWidget(horizontal_line())
        self.tab2.layout.addWidget(self.combo_LCIA_methods)
        self.tab2.layout.addWidget(self.process_contribution_plot)
        self.tab2.setLayout(self.tab2.layout)

        # Create third tab
        self.tab3.layout = QVBoxLayout(self)
        #self.tab3.layout.addWidget(self.combo_LCIA_methods)
        self.tab3.layout.addWidget(self.elementary_flow_contribution_plot)
        self.tab3.setLayout(self.tab3.layout)

        # Create fourth tab
        self.tab4.layout = QVBoxLayout(self)
        self.tab4.layout.addWidget(self.correlation_plot)
        self.tab4.setLayout(self.tab4.layout)

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

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

        # update LCIA methods combobox
        self.dict_LCIA_methods_str_tuples = bc.get_LCIA_method_name_dict(self.mlca.methods)
        self.combo_LCIA_methods.clear()
        self.combo_LCIA_methods.insertItems(0, self.dict_LCIA_methods_str_tuples.keys())
        if not single_method:
            self.combo_LCIA_methods.setVisible(True)
        else:
            self.combo_LCIA_methods.setVisible(False)

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


    def get_contribution_analyses(self, method=None):
        if not method:
            method = next(iter(self.mlca.method_dict.keys()))
        else:
            method = self.dict_LCIA_methods_str_tuples[method]

        self.process_contribution_plot.plot(self.mlca, method=method)
        self.elementary_flow_contribution_plot.plot(self.mlca, method=method)
