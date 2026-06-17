# -*- coding: utf-8 -*-
from collections import namedtuple

from qtpy import QtWidgets

from activity_browser.ui.widgets.combobox import apply_lca_combo_width
from activity_browser.bwutils.lcia_overview import LCIACompareMode, LCIA_COMPARE_LABELS


Switches = namedtuple("switches", ("func", "method", "scenario"))
LCIASwitches = namedtuple(
    "lcia_switches",
    (
        "reference_flows",
        "flows_x_methods",
        "flows_x_scenarios",
        "flows_x_scenarios_x_methods",
    ),
)


class LCAscoresSwitchComboBox(QtWidgets.QComboBox):
    """Compare modes for the LCIA results landing tab."""

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        apply_lca_combo_width(self)
        self.switches = LCIASwitches(
            LCIA_COMPARE_LABELS[LCIACompareMode.REFERENCE_FLOWS],
            LCIA_COMPARE_LABELS[LCIACompareMode.FLOWS_X_METHODS],
            LCIA_COMPARE_LABELS[LCIACompareMode.FLOWS_X_SCENARIOS],
            LCIA_COMPARE_LABELS[LCIACompareMode.FLOWS_X_SCENARIOS_X_METHODS],
        )
        self.indexes = LCIASwitches(0, 1, 2, 3)

    def configure(self, modes: list[str]) -> None:
        self.blockSignals(True)
        self.clear()
        if modes:
            self.addItems(modes)
        self.setVisible(bool(modes))
        self.blockSignals(False)


class ContributionsSwitchComboBox(QtWidgets.QComboBox):
    """For keeping track of contribution tab comparisons."""

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        apply_lca_combo_width(self)
        self.has_scenarios = getattr(parent, "has_scenarios")
        self.switches = Switches("Reference Flows", "Impact Categories", "Scenarios")
        self.indexes = Switches(0, 1, 2)

    def configure(self, has_func: bool = True, has_method: bool = True):
        self.blockSignals(True)
        self.clear()
        if all([has_func, has_method]):
            self.addItems([self.switches.func, self.switches.method])
        if self.has_scenarios:
            self.addItem(self.switches.scenario)
        self.setVisible(self.count() > 0)
        self.blockSignals(False)
