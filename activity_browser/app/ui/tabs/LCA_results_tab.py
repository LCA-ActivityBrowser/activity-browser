# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QTabWidget, QVBoxLayout

from .LCA_results_tabs import LCAResultsSubTab
from ..panels import ABTab
from ...signals import signals


class LCAResultsTab(ABTab):
    def __init__(self, parent):
        super(LCAResultsTab, self).__init__(parent)
        # self.panel = parent  # e.g. right panel
        self.setVisible(False)
        self.visible = False

        self.calculation_setups = dict()

        self.setMovable(True)
        # self.setTabShape(1)  # Triangular-shaped Tabs
        self.setTabsClosable(True)  # todo: does not yet work properly

        # Generate layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.lca_calculation.connect(self.generate_setup)
        signals.delete_calculation_setup.connect(self.remove_setup)

        self.tabCloseRequested.connect(
                lambda index: self.removeTab(index)
        )

    def remove_setup(self, name):
        """ When calculation setup is deleted in LCA Setup, remove the tab from LCA Results. """
        del self.calculation_setups[name]

    def generate_setup(self, name):
        """ Check if the calculation setup exists, if it does, update it, if it doesn't, create a new one. """
        if isinstance(self.calculation_setups.get(name), LCAResultsSubTab):  # update
            self.calculation_setups[name].update_setup()
        else:  # add
            self.calculation_setups[name] = LCAResultsSubTab(self, name)
            self.addTab(self.calculation_setups[name], name)
        self.setCurrentIndex(self.indexOf(self.calculation_setups[name]))


