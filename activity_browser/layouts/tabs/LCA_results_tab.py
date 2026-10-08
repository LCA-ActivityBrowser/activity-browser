# -*- coding: utf-8 -*-
import traceback
from logging import getLogger

from bw2calc.errors import BW2CalcError
from PySide2.QtCore import Qt, Slot
from PySide2.QtWidgets import QApplication, QMessageBox, QVBoxLayout

from activity_browser import signals
from activity_browser.i18n import _
from activity_browser.mod import bw2data as bd

from ...bwutils.errors import ABError
from ..panels import ABTab
from .LCA_results_tabs import LCAResultsSubTab

log = getLogger(__name__)


def calculation_tab_label(name: str, calculation_type: str) -> str:
    """Return a localized label without changing the calculation setup name."""
    if calculation_type == "scenario":
        return _("{name}[Scenarios]", name=name)
    return name


class LCAResultsTab(ABTab):
    """Tab that contains subtabs for each calculation setup."""

    def __init__(self, parent):
        super(LCAResultsTab, self).__init__(parent)

        self.setMovable(True)
        self.setTabsClosable(True)

        # Generate layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.lca_calculation.connect(self.generate_setup)
        self.tabCloseRequested.connect(self.close_tab)
        bd.projects.current_changed.connect(self.close_all)

    @Slot(str, name="removeSetup")
    def remove_setup(self, name: str):
        """When calculation setup is deleted in LCA Setup, remove the tab from LCA Results."""
        if name in self.tabs:
            index = self.indexOf(self.tabs[name])
            self.close_tab(index)

    @Slot(str, name="generateSetup")
    def generate_setup(self, data: dict):
        """Check if the calculation results with this setup name exists, if it does, remove it, then create a new one."""

        cs_name = data.get("cs_name", "new calculation")
        calculation_type = data.get("calculation_type", "simple")

        if calculation_type == "scenario":
            internal_name = "{}[Scenarios]".format(cs_name)
        else:
            internal_name = cs_name
        display_name = calculation_tab_label(cs_name, calculation_type)
        self.remove_setup(internal_name)

        try:
            new_tab = LCAResultsSubTab(data, self)
            self.tabs[internal_name] = new_tab
            self.addTab(new_tab, display_name)
            self.select_tab(self.tabs[internal_name])

            new_tab.destroyed.connect(
                lambda: (
                    self.tabs.pop(internal_name)
                    if id(self.tabs.get(internal_name, None)) == id(new_tab)
                    else None
                )
            )
            new_tab.destroyed.connect(signals.hide_when_empty.emit)

            signals.show_tab.emit("LCA results")
        except (BW2CalcError, ABError) as e:
            initial, *other = e.args
            log.error(traceback.format_exc())
            QApplication.restoreOverrideCursor()
            msg = QMessageBox(
                QMessageBox.Warning,
                _("Calculation problem"),
                str(initial),
                QMessageBox.Ok,
                self,
            )
            msg.setWindowModality(Qt.ApplicationModal)
            if other:
                msg.setDetailedText("\n".join(other))
            msg.exec_()
