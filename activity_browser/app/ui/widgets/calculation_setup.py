from ..style import horizontal_line, vertical_line, header
from ..tables import LCAResultsTable
from ..tables.lca_results import InventoryTable
from ..graphics import (
    LCAResultsPlot,
    ProcessContributionPlot,
    ElementaryFlowContributionPlot,
    CorrelationPlot,
)
from ...bwutils.multilca import MLCA
from ...bwutils import commontasks as bc


from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QRadioButton, QSlider, \
    QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator

from ...signals import signals

class CalculationSetupTab(QTabWidget):
    def __init__(self, parent, name):
        super(CalculationSetupTab, self).__init__(parent)
        self.panel = parent  # e.g. right panel
        self.setup_name = name
        self.setVisible(False)
        self.visible = False

        self.setTabShape(1)  # Triangular-shaped Tabs
        self.setTabPosition(1)  # South-facing Tabs

        self.lcia_results_tab = LCIAAnalysis(self)
        self.process_contributions_tab = ProcessContributions(self)
        self.elementary_flows_tab = ElementaryFlowContributions(self)
        self.correlations_tab = Correlations(self)
        self.inventory_tab = Inventory(self)

        self.update()
        self.connect_signals()

    def connect_signals(self):
        pass

    def update(self):
        self.mlca = MLCA(self.setup_name)

        self.lcia_results_tab.update_table()
        self.lcia_results_tab.update_plot()

        self.process_contributions_tab.update_plot()

        self.elementary_flows_tab.update_plot()

        self.correlations_tab.update_plot()

        self.inventory_tab.update_table()
        # TODO: Make sure the right setup moves to front after update/new tab


class AnalysisTab(QWidget):
    def __init__(self, parent):
        super(AnalysisTab, self).__init__(parent)
        self.tab = parent

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(header(self.tab.setup_name))
        self.layout.addWidget(horizontal_line())

    def connect_signals(self):
        pass

    def update_table(self):
        self.table.sync(self.setup.mlca)

    def add_cutoff(self):
        self.cutoff_menu = QHBoxLayout()

        # Cut-off types
        self.cutoff_type = QVBoxLayout()
        self.cutoff_type_label = QLabel("Cut-off type")
        self.cutoff_type_relative = QRadioButton("Relative")
        self.cutoff_type_relative.setChecked(True)
        self.cutoff_type_topx = QRadioButton("Top #")

        # Cut-off slider
        self.cutoff_slider = QVBoxLayout()
        self.cutoff_slider_set = QVBoxLayout()
        self.cutoff_slider_label = QLabel("Cut-off level")
        self.cutoff_slider_slider = QSlider(Qt.Horizontal)
        self.cutoff_slider_slider.setMinimum(1)  # temporary
        self.cutoff_slider_slider.setMaximum(99)  # temporary
        self.cutoff_slider_slider.sizeHint()
        self.cutoff_slider_minmax = QHBoxLayout()
        self.cutoff_slider_min = QLabel(str(self.cutoff_slider_slider.minimum()))
        self.cutoff_slider_max = QLabel(str(self.cutoff_slider_slider.maximum()))
        self.cutoff_slider_ledit = QHBoxLayout()
        self.cutoff_slider_line = QLineEdit()
        self.cutoff_validator = QIntValidator(self.cutoff_slider_line)
        self.cutoff_slider_line.setValidator(self.cutoff_validator)
        self.cutoff_value = int()  # set to max when known how to port data to this class
        self.cutoff_slider_unit = QLabel("unit")

        # Assemble types
        self.cutoff_type.addWidget(self.cutoff_type_label)
        self.cutoff_type.addWidget(self.cutoff_type_relative)
        self.cutoff_type.addWidget(self.cutoff_type_topx)

        # Assemble slider set
        self.cutoff_slider_set.addWidget(self.cutoff_slider_label)
        self.cutoff_slider_set.addWidget(self.cutoff_slider_slider)
        self.cutoff_slider_minmax.addWidget(self.cutoff_slider_min)
        self.cutoff_slider_minmax.addStretch()
        self.cutoff_slider_minmax.addWidget(self.cutoff_slider_max)
        self.cutoff_slider_set.addLayout(self.cutoff_slider_minmax)

        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_line)
        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_unit)
        self.cutoff_slider_ledit.addStretch(1)

        self.cutoff_slider.addLayout(self.cutoff_slider_set)
        self.cutoff_slider.addLayout(self.cutoff_slider_ledit)

        # Assemble cut-off menu
        self.cutoff_menu.addLayout(self.cutoff_type)
        self.cutoff_menu.addWidget(vertical_line())
        self.cutoff_menu.addLayout(self.cutoff_slider)
        self.cutoff_menu.addStretch()

        self.layout.addLayout(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())

    def add_combobox(self):
        self.combobox_menu = QHBoxLayout()

        self.combobox_menu_label = QLabel("Assesment method: ")
        self.combobox_menu_combobox = QComboBox()
        self.combobox_menu_combobox.scroll = False

        self.combobox_menu.addWidget(self.combobox_menu_label)
        self.combobox_menu.addWidget(self.combobox_menu_combobox, 1)
        self.combobox_menu.addStretch(1)

        self.layout.addLayout(self.combobox_menu)
        self.layout.addWidget(horizontal_line())

    def add_main_space(self):

        # Generate Table and Plot area
        self.main_space = QScrollArea()
        self.main_space_widget = QWidget()
        self.main_space_widget_layout = QVBoxLayout()
        self.main_space_widget.setLayout(self.main_space_widget_layout)
        self.main_space.setWidget(self.main_space_widget)
        self.main_space.setWidgetResizable(True)
        # Option switch
        self.main_space_tb_grph = QHBoxLayout()
        self.main_space_tb_grph_plot = QCheckBox("Plot")
        self.main_space_tb_grph_plot.setChecked(True)
        self.main_space_tb_grph_table = QCheckBox("Table")
        self.main_space_tb_grph_table.setChecked(True)
        # Plot
        self.main_space_plot = self.plot
        # Table
        self.main_space_table = self.table

        # Assemble option switch
        self.main_space_tb_grph.addWidget(self.main_space_tb_grph_plot)
        self.main_space_tb_grph.addWidget(self.main_space_tb_grph_table)
        self.main_space_tb_grph.addStretch()

        # Assemble Table and Plot area
        if self.table and self.plot:
            self.main_space_widget_layout.addLayout(self.main_space_tb_grph)
        if self.plot:
            self.main_space_widget_layout.addWidget(self.main_space_plot, 1)
        if self.table:
            self.main_space_widget_layout.addWidget(self.main_space_table)
        self.main_space_widget_layout.addStretch()

        self.layout.addWidget(self.main_space)

    def add_export(self):
        self.export_menu = QHBoxLayout()

        # Export Plot
        self.export_plot = QVBoxLayout()
        self.export_plot_label = QLabel("Export plot")
        self.export_plot_buttons = QHBoxLayout()
        self.export_plot_buttons_png = QPushButton(".png")
        self.export_plot_buttons_svg = QPushButton(".svg")
        # Export Table
        self.export_table = QVBoxLayout()
        self.export_table_label = QLabel("Export table")
        self.export_table_buttons = QHBoxLayout()
        self.export_table_buttons_copy = QPushButton("Copy")
        self.export_table_buttons_csv = QPushButton(".csv")
        self.export_table_buttons_excel = QPushButton("Excel")

        # Assemble export plot
        self.export_plot.addWidget(self.export_plot_label)
        self.export_plot_buttons.addWidget(self.export_plot_buttons_png)
        self.export_plot_buttons.addWidget(self.export_plot_buttons_svg)
        self.export_plot.addLayout(self.export_plot_buttons)

        # Assemble export table
        self.export_table.addWidget(self.export_table_label)
        self.export_table_buttons.addWidget(self.export_table_buttons_copy)
        self.export_table_buttons.addWidget(self.export_table_buttons_csv)
        self.export_table_buttons.addWidget(self.export_table_buttons_excel)
        self.export_table.addLayout(self.export_table_buttons)

        # Assemble export menu
        if self.plot:
            self.export_menu.addLayout(self.export_plot)
        if self.table and self.plot:
            self.export_menu_vert_line = vertical_line()
            self.export_menu.addWidget(self.export_menu_vert_line)
        if self.table:
            self.export_menu.addLayout(self.export_table)
        self.export_menu.addStretch()

        self.layout.addWidget(horizontal_line())
        self.layout.addLayout(self.export_menu)

class LCIAAnalysis(AnalysisTab):
    def __init__(self, parent):
        super(LCIAAnalysis, self).__init__(parent)
        self.setup = parent

        self.name = "LCIA Results"

        self.table = LCAResultsTable()
        self.plot = LCAResultsPlot(self.setup)

        self.add_cutoff()
        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

    def update_plot(self):
        self.plot.plot(self.setup.mlca)

class ProcessContributions(AnalysisTab):
    def __init__(self, parent):
        super(ProcessContributions, self).__init__(parent)
        self.setup = parent

        self.name = "Process Contributions"

        self.table = None
        self.plot = ProcessContributionPlot(self.setup)

        self.add_cutoff()
        self.add_combobox()
        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

    def update_plot(self):
        self.plot.plot(self.setup.mlca, method=self.setup.mlca.methods[0])

class ElementaryFlowContributions(AnalysisTab):
    def __init__(self, parent):
        super(ElementaryFlowContributions, self).__init__(parent)
        self.setup = parent

        self.name = "Elementary Flow Contributions"

        self.table = None
        self.plot = ElementaryFlowContributionPlot(self.setup)

        self.add_cutoff()
        self.add_combobox()
        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

    def update_plot(self):
        self.plot.plot(self.setup.mlca, method=self.setup.mlca.methods[0])

class Correlations(AnalysisTab):
    def __init__(self, parent):
        super(Correlations, self).__init__(parent)
        self.setup = parent

        self.name = "Correlations"

        self.table = None
        self.plot = CorrelationPlot(self.setup)

        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

    def update_plot(self):
        labels = [str(x + 1) for x in range(len(self.setup.mlca.func_units))]
        self.plot.plot(self.setup.mlca, labels)

class Inventory(AnalysisTab):
    def __init__(self, parent):
        super(Inventory, self).__init__(parent)
        self.setup = parent

        self.name = "Inventory"

        self.table = InventoryTable(self.setup)
        self.plot = None

        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)