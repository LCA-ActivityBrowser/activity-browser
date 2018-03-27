# -*- coding: utf-8 -*-
from PyQt5 import QtWidgets

from ..style import horizontal_line, header
from ..tables import LCAResultsTable
from ..graphics import (
    CorrelationPlot,
    LCAResultsPlot,
    LCAProcessContributionPlot,
    LCAElementaryFlowContributionPlot
)
from ...bwutils.multilca import MLCA
from ...signals import signals


class ImpactAssessmentTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ImpactAssessmentTab, self).__init__(parent)
        self.panel = parent  # e.g. right panel
        self.visible = False

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_widget_layout = QtWidgets.QVBoxLayout()

        self.scroll_widget.setLayout(self.scroll_widget_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.remove_tab)
        signals.lca_calculation.connect(self.calculate)

    def add_tab(self):
        self.panel.addTab(self, "Impact Assessment")
        self.panel.select_tab(self)
        self.visible = True
        self.layout.addWidget(self.scroll_area)

    def remove_tab(self):
        if self.visible:
            self.panel.removeTab(4)
            self.visible = False
            self.clear_layout()

    def clear_layout(self):
        for index in range(self.scroll_widget_layout.count()):
            try:
                widget = self.scroll_widget_layout.itemAt(index).widget().deleteLater()
            except AttributeError:
                pass

    def calculate(self, name):
        # LCA Results Analysis: (ideas to implement)
        # - LCA score: Barchart (choice LCIA method)
        # - Contribution Analysis (choice process, LCIA method;
        #   THEN BY process, product, geography, ISIC sector)
        #   ALSO: Type of graph: Barchart, Treemap, Piechart, Worldmap (for geo)
        #   CUTOFF
        # - Uncertainties: Monte Carlo, Latin-Hypercube

        self.clear_layout()

        # Multi-LCA calculation
        self.mlca = MLCA(name)
        single_lca = len(self.mlca.func_units) == 1
        normalized_results = self.mlca.results / self.mlca.results.max(axis=0)
        # plots
        lca_results_plot = LCAResultsPlot(self, self.mlca)
        process_contribution_plot = LCAProcessContributionPlot(self, self.mlca)
        elementary_flow_contribution_plot = LCAElementaryFlowContributionPlot(self, self.mlca)
        labels = [str(x + 1) for x in range(len(self.mlca.func_units))]
        if not single_lca:
            corr_chart = CorrelationPlot(self, normalized_results.T, labels)
        # LCA results table
        results_table = LCAResultsTable()
        results_table.sync(self.mlca)

        # Display the information in the scroll widget
        self.scroll_widget_layout.addWidget(header("LCA Scores:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(lca_results_plot)

        self.scroll_widget_layout.addWidget(header("Process Contributions:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(process_contribution_plot)

        self.scroll_widget_layout.addWidget(header("Elementary Flow Contributions:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(elementary_flow_contribution_plot)

        if not single_lca:
            self.scroll_widget_layout.addWidget(header("LCA Scores Correlation:"))
            self.scroll_widget_layout.addWidget(horizontal_line())
            self.scroll_widget_layout.addWidget(corr_chart)

        self.scroll_widget_layout.addWidget(header("LCA Scores:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(results_table)

        self.add_tab()
