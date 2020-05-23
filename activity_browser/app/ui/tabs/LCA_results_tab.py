# -*- coding: utf-8 -*-
from typing import Union
import traceback

from bw2calc.errors import BW2CalcError
from PySide2.QtCore import Qt, Slot
from PySide2.QtWidgets import QMessageBox, QVBoxLayout
import pandas as pd

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
        signals.lca_presamples_calculation.connect(self.generate_setup)
        signals.lca_scenario_calculation.connect(self.generate_setup)
        signals.delete_calculation_setup.connect(self.remove_setup)
        self.tabCloseRequested.connect(self.close_tab)
        signals.project_selected.connect(self.close_all)
        signals.parameters_changed.connect(self.close_all)

    def remove_setup(self, name):
        """ When calculation setup is deleted in LCA Setup, remove the tab from LCA Results. """
        if name in self.tabs:
            index = self.indexOf(self.tabs[name])
            self.close_tab(index)

    @Slot(str, name="generateSimpleLCA")
    @Slot(str, str, name="generatePresamplesLCA")
    @Slot(str, object, name="generateSuperstructureLCA")
    def generate_setup(self, name: str, presamples: Union[str, pd.DataFrame] = None):
        """ Check if the calculation setup exists, if it does, remove it, then create a new one. """
        self.remove_setup(name)

        try:
            new_tab = LCAResultsSubTab(name, presamples, self)
            self.tabs[name] = new_tab
            self.addTab(new_tab, name)
            self.select_tab(self.tabs[name])
            signals.show_tab.emit("LCA results")
        except BW2CalcError as e:
            initial, *other = e.args
            print(traceback.format_exc())
            msg = QMessageBox(
                QMessageBox.Warning, "Calculation problem", str(initial),
                QMessageBox.Ok, self
            )
            msg.setWindowModality(Qt.ApplicationModal)
            if other:
                msg.setDetailedText("\n".join(other))
            msg.exec_()
