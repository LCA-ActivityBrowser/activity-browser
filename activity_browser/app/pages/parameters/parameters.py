from qtpy import QtWidgets, QtCore

from activity_browser.ui import widgets

from .parameters_section import ParametersSection
from .parameterized_exchanges_section import ParameterizedExchangesSection


class ParametersPage(widgets.ABAbstractPage):
    """
    A widget that displays all parameters and parameterized exchanges in the current project.

    This page shows:
    - Parameters section: A tree view of parameters organized by scope
    - Parameterized exchanges section: A table of exchanges with formulas
    """
    basePage = True
    title = "Parameters"

    def __init__(self, parent=None):
        """
        Initializes the ParametersPage widget.

        Args:
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.parameters_section = ParametersSection(self)
        self.parameterized_exchanges_section = ParameterizedExchangesSection(self)

        self.build_layout()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 3, 0, 0)

        # Add both sections in a splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)

        # Parameters section
        params_widget = QtWidgets.QWidget()
        params_layout = QtWidgets.QVBoxLayout(params_widget)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_label = widgets.ABLabel.demiBold("    Parameters")
        params_layout.addWidget(params_label)
        params_layout.addWidget(widgets.ABHLine(self))
        params_layout.addWidget(self.parameters_section)
        splitter.addWidget(params_widget)

        # Parameterized exchanges section
        exchanges_widget = QtWidgets.QWidget()
        exchanges_layout = QtWidgets.QVBoxLayout(exchanges_widget)
        exchanges_layout.setContentsMargins(0, 0, 0, 0)
        exchanges_label = widgets.ABLabel.demiBold("    Parameterized Exchanges")
        exchanges_layout.addWidget(exchanges_label)
        exchanges_layout.addWidget(widgets.ABHLine(self))
        exchanges_layout.addWidget(self.parameterized_exchanges_section)
        splitter.addWidget(exchanges_widget)

        layout.addWidget(splitter)
        self.setLayout(layout)


