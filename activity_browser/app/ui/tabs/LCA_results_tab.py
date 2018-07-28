from ..widgets import CalculationSetupTab

from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QRadioButton, QSlider, \
    QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox

from ...signals import signals

class LCAResultsTab(QTabWidget):
    def __init__(self, parent):
        super(LCAResultsTab, self).__init__(parent)
        self.panel = parent  # e.g. right panel
        self.setVisible(False)
        self.visible = False

        self.calculation_setups = dict()

        self.setMovable(True)
        self.setTabsClosable(True)

        # Generate layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project_selected.connect(self.remove_tab)
        signals.lca_calculation.connect(self.add_tab)

        signals.lca_calculation.connect(self.generate_setup)
        signals.delete_calculation_setup.connect(self.remove_setup)

        self.tabCloseRequested.connect(
                lambda index: self.removeTab(index))

    def add_tab(self):
        """ Add the LCA Results tab to the right panel of AB. """
        if not self.visible:
            self.visible = True
            self.panel.addTab(self, "LCIA Results")
        self.panel.select_tab(self)  # put tab to front after LCA calculation

    def remove_tab(self):
        """ Remove the LCA results tab. """
        if self.visible:
            self.visible = False
            self.panel.removeTab(self.panel.indexOf(self))

    def remove_setup(self, name):
        self.removeTab(self.indexOf(self.calculation_setups[name]))
        del self.calculation_setups[name]

    def generate_setup(self, name):
        if isinstance(self.calculation_setups.get(name), CalculationSetupTab):
            self.calculation_setups[name].update_setup()
        else:
            self.calculation_setups[name] = CalculationSetupTab(self, name)
            self.addTab(self.calculation_setups[name], name)
        self.setCurrentIndex(self.indexOf(self.calculation_setups[name]))


