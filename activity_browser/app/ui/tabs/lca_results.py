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


class ImpactAssessmentTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ImpactAssessmentTab, self).__init__(parent)
        self.panel = parent  # e.g. right panel
        self.setVisible(False)
        self.visible = False

        self.combo_LCIA_methods = QtWidgets.QComboBox()

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
        self.layout.addWidget(self.scroll_area)

        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.remove_tab)
        signals.lca_calculation.connect(self.calculate)
        self.combo_LCIA_methods.currentTextChanged.connect(
            lambda name: self.get_contribution_analyses(method=name))

    def make_layout(self):
        # Display the information in the scroll widget
        self.scroll_widget_layout.addWidget(header("LCA Scores:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(self.results_plot)

        self.scroll_widget_layout.addWidget(header("Process Contributions:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(self.combo_LCIA_methods)
        self.scroll_widget_layout.addWidget(self.process_contribution_plot)

        self.scroll_widget_layout.addWidget(header("Elementary Flow Contributions:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(self.elementary_flow_contribution_plot)

        self.scroll_widget_layout.addWidget(header("LCA Scores Correlation:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(self.correlation_plot)

        self.scroll_widget_layout.addWidget(header("LCA Scores:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(self.results_table)

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

        # update LCIA methods combobox
        self.dict_LCIA_methods_str_tuples = bc.get_LCIA_method_name_dict(self.mlca.methods)
        self.combo_LCIA_methods.clear()
        self.combo_LCIA_methods.insertItems(0, self.dict_LCIA_methods_str_tuples.keys())

        # PLOTS & TABLES

        # LCA Results Plot
        self.results_plot.plot(self.mlca)

        # Contribution Analysis
        # is plotted by the combobox signal

        # Correlation Plot
        labels = [str(x + 1) for x in range(len(self.mlca.func_units))]
        if not single_lca:
            self.correlation_plot.setVisible(True)
            self.correlation_plot.plot(self.mlca, labels)
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
