from qtpy import QtWidgets

import bw2data as bd

from activity_browser import signals

from .scenario_section import ScenarioSection
from .functional_unit_section import FunctionalUnitSection
from .impact_category_section import ImpactCategorySection
from .toolbar import Toolbar


class CalculationSetupPage(QtWidgets.QWidget):

    def __init__(self, calculation_setup_name: str, parent=None):
        super().__init__(parent)

        self.calculation_setup_name = calculation_setup_name

        self.toolbar = Toolbar(calculation_setup_name, self)
        self.functional_unit_section = FunctionalUnitSection(calculation_setup_name, self)
        self.impact_category_section = ImpactCategorySection(calculation_setup_name, self)
        self.scenario_section = ScenarioSection(self)

        # Build the layout of the widget
        self.build_layout()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.toolbar)

        # Add output label and view to the layout
        layout.addWidget(QtWidgets.QLabel("<b>⠀Functional Units:</b>"))
        layout.addWidget(self.functional_unit_section)

        # Add input label and view to the layout
        layout.addWidget(QtWidgets.QLabel("<b>⠀Impact Categories:</b>"))
        layout.addWidget(self.impact_category_section)

        # Set the layout for the widget
        self.setLayout(layout)
        self.connect_signals()

    def connect_signals(self):
        signals.project.changed.connect(self.sync)
        signals.meta.calculation_setups_changed.connect(self.sync)

    def sync(self) -> None:
        self.functional_unit_section.sync()
        self.impact_category_section.sync()
