from qtpy import QtWidgets

from activity_browser import signals, actions

from .scenario_section import ScenarioSection
from .functional_unit_section import FunctionalUnitSection
from .impact_category_section import ImpactCategorySection


class CalculationSetupPage(QtWidgets.QWidget):

    def __init__(self, cs_name: str, parent=None):
        super().__init__(parent)

        self.calculation_setup_name = cs_name

        self.type_dropdown = QtWidgets.QComboBox()
        self.type_dropdown.addItems(["Standard", "Scenario"])

        self.run_button = actions.CSCalculate.get_QButton(cs_name)
        self.functional_unit_section = FunctionalUnitSection(cs_name, self)
        self.impact_category_section = ImpactCategorySection(cs_name, self)
        self.scenario_section = ScenarioSection(self)

        # Build the layout of the widget
        self.build_layout()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 10, 0)
        top_layout.addWidget(QtWidgets.QLabel("<b>⠀Functional Units:</b>"))
        top_layout.addStretch()
        top_layout.addWidget(self.type_dropdown)
        top_layout.addWidget(self.run_button)

        # Add fu label and view to the layout
        layout.addLayout(top_layout)
        layout.addWidget(self.functional_unit_section)

        # Add ic label and view to the layout
        layout.addWidget(QtWidgets.QLabel("<b>⠀Impact Categories:</b>"))
        layout.addWidget(self.impact_category_section)

        # Add scenario label and view to the layout

        layout.addWidget(self.scenario_section)

        # Set the layout for the widget
        self.setLayout(layout)
        self.connect_signals()

    def connect_signals(self):
        signals.project.changed.connect(self.sync)
        signals.meta.calculation_setups_changed.connect(self.sync)

    def sync(self) -> None:
        self.functional_unit_section.sync()
        self.impact_category_section.sync()
