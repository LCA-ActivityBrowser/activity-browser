from qtpy import QtWidgets

from activity_browser import signals, actions
from activity_browser.ui import widgets

from .scenario_section import ScenarioSection
from .functional_unit_section import FunctionalUnitSection
from .impact_category_section import ImpactCategorySection


class CalculationSetupPage(QtWidgets.QWidget):

    def __init__(self, cs_name: str, parent=None):
        super().__init__(parent)
        self.setObjectName(cs_name)

        self.calculation_setup_name = cs_name

        self.type_dropdown = QtWidgets.QComboBox()
        self.type_dropdown.addItems(["Standard", "Scenario"])

        self.run_button = QtWidgets.QPushButton("Run", self)
        self.functional_unit_section = FunctionalUnitSection(cs_name, self)
        self.impact_category_section = ImpactCategorySection(cs_name, self)
        self.scenario_section = ScenarioSection(self)
        self.scenario_section.hide()

        # Build the layout of the widget
        self.build_layout()
        self.sync()
        self.connect_signals()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 10, 0)
        top_layout.addWidget(widgets.ABLabel.demiBold("    Functional Units:", self))
        top_layout.addStretch()
        top_layout.addWidget(self.type_dropdown)
        top_layout.addWidget(self.run_button)

        # Add fu label and view to the layout
        layout.addLayout(top_layout)
        layout.addWidget(self.functional_unit_section)

        # Add ic label and view to the layout
        layout.addWidget(widgets.ABLabel.demiBold("    Impact Categories:", self))
        layout.addWidget(self.impact_category_section)

        # Add scenario label and view to the layout

        layout.addWidget(self.scenario_section)

        # Set the layout for the widget
        self.setLayout(layout)

    def connect_signals(self):
        signals.project.changed.connect(self.sync)
        signals.meta.calculation_setups_changed.connect(self.sync)

        self.type_dropdown.currentTextChanged.connect(self.type_switch)
        self.run_button.released.connect(self.run_calculation)

    def sync(self) -> None:
        self.functional_unit_section.sync()
        self.impact_category_section.sync()

    def type_switch(self, calculation_type: str):
        if calculation_type == "Standard":
            self.scenario_section.hide()
        elif calculation_type == "Scenario":
            self.scenario_section.show()
        else:
            raise ValueError(f"Unknown calculation type: {calculation_type}")

    def run_calculation(self):
        if self.type_dropdown.currentText() == "Standard":
            actions.CSCalculate.run(self.calculation_setup_name)
        elif self.type_dropdown.currentText() == "Scenario":
            scenario_data = self.scenario_section.scenario_dataframe()
            actions.CSCalculate.run(self.calculation_setup_name, scenario_data)

