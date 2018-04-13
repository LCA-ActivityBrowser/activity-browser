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
        self.visible = False

        self.combo_LCIA_methods = QtWidgets.QComboBox()

        self.process_contribution_plot = ProcessContributionPlot(self)
        self.elementary_flow_contribution_plot = ElementaryFlowContributionPlot(self)

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
        self.combo_LCIA_methods.currentTextChanged.connect(
            lambda name: self.get_contribution_analyses(method=name))

    def add_tab(self):
        self.panel.addTab(self, "LCA results")
        self.panel.select_tab(self)
        self.visible = True
        self.layout.addWidget(self.scroll_area)

    def remove_tab(self):
        if self.visible:
            self.panel.removeTab(self.panel.indexOf(self))

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
        self.combo_LCIA_methods.clear()

        # Multi-LCA calculation
        self.mlca = MLCA(name)
        single_lca = len(self.mlca.func_units) == 1
        normalized_results = self.mlca.results / self.mlca.results.max(axis=0)

        # LCIA methods combobox
        self.dict_LCIA_methods_str_tuples = bc.get_LCIA_method_name_dict(self.mlca.methods)
        self.combo_LCIA_methods.insertItems(0, self.dict_LCIA_methods_str_tuples.keys())

        # PLOTS & TABLES

        # LCA Results Plot
        lca_results_plot = LCAResultsPlot(self, self.mlca)

        # Contribution Analysis
        # self.process_contribution_plot, self.elementary_flow_contribution_plot = \
        self.get_contribution_analyses(method=self.combo_LCIA_methods.currentText())

        # Correlation Plot
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
        self.scroll_widget_layout.addWidget(self.combo_LCIA_methods)
        self.scroll_widget_layout.addWidget(self.process_contribution_plot)

        self.scroll_widget_layout.addWidget(header("Elementary Flow Contributions:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(self.elementary_flow_contribution_plot)

        if not single_lca:
            self.scroll_widget_layout.addWidget(header("LCA Scores Correlation:"))
            self.scroll_widget_layout.addWidget(horizontal_line())
            self.scroll_widget_layout.addWidget(corr_chart)

        self.scroll_widget_layout.addWidget(header("LCA Scores:"))
        self.scroll_widget_layout.addWidget(horizontal_line())
        self.scroll_widget_layout.addWidget(results_table)

        self.add_tab()

    def get_contribution_analyses(self, method=None):
        if not method:
            method = next(iter(self.mlca.method_dict.keys()))
        else:
            method = self.dict_LCIA_methods_str_tuples[method]

        print("Updating contribution analysis:", method)

        # self.process_contribution_plot = LCAProcessContributionPlot(self, self.mlca, method=method)
        # self.elementary_flow_contribution_plot = LCAElementaryFlowContributionPlot(self, self.mlca, method=method)

        # if self.mlca:
        #     self.process_contribution_plot.update(self.mlca, method=method)
        #
        # self.process_contribution_plot.draw()
        self.process_contribution_plot.plot(self.mlca, method=method)
        self.elementary_flow_contribution_plot.plot(self.mlca, method=method)
        # self.scroll_widget_layout.replaceWidget(self.process_contribution_plot, self.process_contribution_plot)
        # self.process_contribution_plot.d
        # return process_contribution_plot, elementary_flow_contribution_plot
