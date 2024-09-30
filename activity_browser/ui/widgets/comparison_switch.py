# -*- coding: utf-8 -*-
from collections import namedtuple

from qtpy import QtWidgets

Switches = namedtuple("switches", ("func", "method", "scenario"))


class SwitchComboBox(QtWidgets.QComboBox):
    """For keeping track of contribution tab comparisons."""

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.has_scenarios = getattr(parent, "has_scenarios")
        self.switches = Switches("Reference Flows", "Impact Categories", "Scenarios")
        self.indexes = Switches(0, 1, 2)

    def configure(self, has_func: bool = True, has_method: bool = True):
        self.blockSignals(True)
        if all([has_func, has_method]):
            self.insertItems(0, [self.switches.func, self.switches.method])
        if self.has_scenarios:
            self.insertItems(self.indexes.scenario, [self.switches.scenario])
        self.setVisible(self.count() > 0)
        self.blockSignals(False)
