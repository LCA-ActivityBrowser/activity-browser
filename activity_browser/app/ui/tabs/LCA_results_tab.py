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

        self.lca_kinds = {}

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

    def close_all(self):
        super().close_all()
        self.lca_kinds = {}

    @Slot(str, name="removeSetup")
    def remove_setup(self, name: str):
        """ When calculation setup is deleted in LCA Setup, remove the tab from LCA Results. """
        if name in self.tabs:
            index = self.indexOf(self.tabs[name])
            self.close_tab(index)

    def adjust_setup_tab(self, name: str, kind: str) -> str:
        """Adjust name of pre-existing tabs if the same CS is run with
        a different LCA type.

        Will return a possibly adjusted name.
        """
        if name not in self.lca_kinds:
            self.lca_kinds[name] = {kind}
            return name
        elif name in self.tabs and kind in self.lca_kinds[name]:
            # The definition of insanity.
            self.remove_setup(name)
            return name

        # We've found the CS name to exist as a tab already.
        new_name = "{} - {}".format(name, kind)
        if new_name in self.tabs:
            # Remove and recreate the specific LCA tab.
            self.remove_setup(new_name)
        elif name in self.tabs and kind not in self.lca_kinds[name]:
            # A new kind of LCA is run on the same CS.
            idx = self.indexOf(self.tabs[name])
            other_kind = next(iter(self.lca_kinds[name]))
            other_name = "{} - {}".format(name, other_kind)
            self.setTabText(idx, other_name)
            self.tabs[other_name] = self.tabs[name]
            del self.tabs[name]
            self.lca_kinds[name].add(kind)
        else:
            # A third (or more) kind of LCA is run on the same CS.
            self.lca_kinds[name].add(kind)
        return new_name

    @Slot(str, name="generateSimpleLCA")
    @Slot(str, str, name="generatePresamplesLCA")
    @Slot(str, object, name="generateSuperstructureLCA")
    def generate_setup(self, cs_name: str, presamples: Union[str, pd.DataFrame] = None):
        """ Check if the calculation setup exists, if it does, remove it, then create a new one. """
        kind = "Standard"
        if isinstance(presamples, str):
            kind = "Presamples"
        elif isinstance(presamples, pd.DataFrame):
            kind = "Scenarios"
        name = self.adjust_setup_tab(cs_name, kind)

        try:
            new_tab = LCAResultsSubTab(cs_name, presamples, self)
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
