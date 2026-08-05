# -*- coding: utf-8 -*-
from collections import namedtuple

from PySide2 import QtWidgets

from activity_browser.i18n import _

Switches = namedtuple("switches", ("func", "method", "scenario"))


class ComparisonMode:
    """Stable IDs for contribution comparison modes."""

    FUNCTIONAL_UNITS = "functional_units"
    IMPACT_CATEGORIES = "impact_categories"
    SCENARIOS = "scenarios"


class SwitchComboBox(QtWidgets.QComboBox):
    """For keeping track of contribution tab comparisons."""

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.has_scenarios = getattr(parent, "has_scenarios")
        self.switches = Switches(
            _("Reference Flows"), _("Impact Categories"), _("Scenarios")
        )
        self.modes = Switches(
            ComparisonMode.FUNCTIONAL_UNITS,
            ComparisonMode.IMPACT_CATEGORIES,
            ComparisonMode.SCENARIOS,
        )
        self.indexes = Switches(0, 1, 2)

    def configure(self, has_func: bool = True, has_method: bool = True):
        self.blockSignals(True)
        if all([has_func, has_method]):
            self.insertItem(self.indexes.func, self.switches.func, self.modes.func)
            self.insertItem(
                self.indexes.method, self.switches.method, self.modes.method
            )
        if self.has_scenarios:
            self.insertItem(
                self.indexes.scenario, self.switches.scenario, self.modes.scenario
            )
        self.setVisible(self.count() > 0)
        self.blockSignals(False)

    @property
    def current_mode(self) -> str:
        """Return the stable ID for the selected comparison mode."""
        return self.currentData()
