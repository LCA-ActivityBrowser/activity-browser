# -*- coding: utf-8 -*-
from PySide2.QtWidgets import QVBoxLayout

from .LCA_results_tabs import LCAResultsSubTab
from ..panels import ABTab
from ...signals import signals


class LCAResultsTab(ABTab):
    """Tab that contains subtabs for each calculation setup."""
    def __init__(self, parent):
        super(LCAResultsTab, self).__init__(parent)

        self.setMovable(True)
        # self.setTabShape(1)  # Triangular-shaped Tabs
        self.setTabsClosable(True)

        # Generate layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.lca_calculation.connect(self.generate_setup)
        signals.delete_calculation_setup.connect(self.remove_setup)
        self.tabCloseRequested.connect(self.close_tab)
        signals.project_selected.connect(self.close_all)
        signals.parameters_changed.connect(self.close_all)

    def remove_setup(self, name):
        """ When calculation setup is deleted in LCA Setup, remove the tab from LCA Results. """
        if name in self.tabs:
            index = self.indexOf(self.tabs[name])
            self.close_tab(index)

    def generate_setup(self, name):
        """ Check if the calculation setup exists, if it does, remove it, then create a new one. """
        if isinstance(self.tabs.get(name), LCAResultsSubTab):  # remove, if necessary
            self.remove_setup(name)

        new_tab = LCAResultsSubTab(self, name)
        self.tabs[name] = new_tab
        self.addTab(new_tab, name)

        self.select_tab(self.tabs[name])
        signals.show_tab.emit("LCA results")
