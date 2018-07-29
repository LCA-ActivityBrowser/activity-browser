

from ..style import horizontal_line, vertical_line, header
from ..tables import LCAResultsTable, ProcessContributionsTable, InventoryTable, InventoryCharacterisationTable
from ..graphics import (
    LCAResultsPlot,
    ProcessContributionPlot,
    InventoryCharacterisationPlot,
    CorrelationPlot,
    LCAResultsBarChart
)
from ...bwutils.multilca import MLCA
from ...bwutils import commontasks as bc
from .log_slider import LogarithmicSlider
from brightway2 import get_activity


from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QRadioButton, QSlider, \
    QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator, QDoubleValidator

# TODO: fix box-in-box of the main space

# TODO: implement parts of each analysis tab as class MM

# TODO: Finish inventory tab (with techno/biosphere options MS
# TODO: add relative/absolute option for plots in characterised inventory and process contributions MS
# TODO: add rest+total row to tables in char. inv. and proc. cont. MM
# TODO: add switch for characterised inventory and process contributions between func unit and method MM
# TODO: Basic plot for LCIA Results + Combobox MS
# TODO: LCIA Results > column specific colour gradients MS
# TODO: LOW PRIORITY: add filtering for tables/graphs ANY


class CalculationSetupTab(QTabWidget):
    def __init__(self, parent, name):
        super(CalculationSetupTab, self).__init__(parent)
        self.panel = parent
        self.setup_name = name
        self.method_dict = dict()

        self.setVisible(False)
        self.visible = False

        self.setTabShape(1)  # Triangular-shaped Tabs
        self.setTabPosition(1)  # South-facing Tabs

        self.update_calculation()

        self.LCAscoreComparison_tab = LCAScoreComparison(self)
        self.inventory_tab = Inventory(self)
        self.inventory_characterisation_tab = InventoryCharacterisation(self)
        self.lcia_results_tab = LCIAAnalysis(self)
        self.process_contributions_tab = ProcessContributions(self)
        self.correlations_tab = Correlations(self)

        self.update_setup(calculate=False)

    def update_setup(self, calculate=True):
        """ Update the calculation setup. """
        if calculate:
            self.update_calculation()

        self.LCAscoreComparison_tab.update_analysis_tab()
        self.inventory_tab.update_analysis_tab()
        self.inventory_characterisation_tab.update_analysis_tab()
        self.lcia_results_tab.update_analysis_tab()
        self.process_contributions_tab.update_analysis_tab()
        self.correlations_tab.update_analysis_tab()

        lcia_results_tab_index = self.indexOf(self.lcia_results_tab)
        correlations_tab_index = self.indexOf(self.correlations_tab)

        if not self.single_func_unit:
            self.setTabEnabled(lcia_results_tab_index, True)
            self.setTabEnabled(correlations_tab_index, True)
        else:
            self.setTabEnabled(lcia_results_tab_index, False)
            self.setTabEnabled(correlations_tab_index, False)

    def update_calculation(self):
        """ Update the mlca calculation. """
        self.mlca = MLCA(self.setup_name)

        self.method_dict = bc.get_LCIA_method_name_dict(self.mlca.methods)

        if len(self.mlca.func_units) != 1:
            self.single_func_unit = False
        else:
            self.single_func_unit = True
        if len(self.mlca.methods) != 1:
            self.single_method = False
        else:
            self.single_method = True

class AnalysisTab(QWidget):
    def __init__(self, parent, cutoff=None, func=None, combobox=None, table=None, plot=None, export=None):
        super(AnalysisTab, self).__init__(parent)
        self.setup = parent

        self.cutoff_menu = cutoff
        self.cutoff_func = func

        self.combobox_menu_combobox = combobox
        self.table = table
        self.plot = plot
        self.limit_type = "percent"
        self.export_menu = export

        self.name = str()
        self.header = header(self.name)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.layout.addWidget(self.header)
        self.layout.addWidget(horizontal_line())

    def connect_analysis_signals(self):
        # Cut-off
        if self.cutoff_menu:
            # Cut-off types
            self.cutoff_type_topx.clicked.connect(self.cutoff_type_topx_check)
            self.cutoff_type_relative.clicked.connect(self.cutoff_type_relative_check)
            self.cutoff_slider_lft_btn.clicked.connect(self.cutoff_increment_left_check)
            self.cutoff_slider_rght_btn.clicked.connect(self.cutoff_increment_right_check)

            # Cut-off log slider
            self.cutoff_slider_log_slider.valueChanged.connect(
                lambda: self.cutoff_slider_relative_check("sl"))
            self.cutoff_slider_line.textChanged.connect(
                lambda: self.cutoff_slider_relative_check("le"))
            # Cut-off slider
            self.cutoff_slider_slider.valueChanged.connect(
                lambda: self.cutoff_slider_topx_check("sl"))
            self.cutoff_slider_line.textChanged.connect(
                lambda: self.cutoff_slider_topx_check("le"))

        # Combo box signal
        if self.combobox_menu_combobox != None:

            if self.combobox_menu_method_bool and not self.combobox_menu_func_bool:
                if self.plot:
                    self.combobox_menu_combobox.currentTextChanged.connect(
                        lambda name: self.update_plot(method=name))

            elif not self.combobox_menu_method_bool and self.combobox_menu_func_bool:
                pass
                # logic for only func

            else:
                self.combobox_menu_switch.clicked.connect(self.combo_switch_check)
                # logic for updating when both are active

                # THIS SHOULD BE REMOVED WHEN THERE IS FUNCTIONALITY FOR THE 'SWITCH' BUTTON
                if self.plot:
                    self.combobox_menu_combobox.currentTextChanged.connect(
                        lambda name: self.update_plot(method=name))
                # UP TO HERE

            if self.table:
                self.combobox_menu_combobox.currentTextChanged.connect(self.update_table)

        # Mainspace Checkboxes
        self.main_space_tb_grph_table.stateChanged.connect(
            lambda: self.main_space_check(self.main_space_tb_grph_table, self.main_space_tb_grph_plot))
        self.main_space_tb_grph_plot.stateChanged.connect(
            lambda: self.main_space_check(self.main_space_tb_grph_table, self.main_space_tb_grph_plot))

        # Export Table
        if self.table and self.export_menu:
            self.export_table_buttons_copy.clicked.connect(self.table.to_clipboard)
            self.export_table_buttons_csv.clicked.connect(self.table.to_csv)
            self.export_table_buttons_excel.clicked.connect(self.table.to_excel)

        # Export Plot
        if self.plot and self.export_menu:
            self.export_plot_buttons_png.clicked.connect(self.plot.to_png)
            self.export_plot_buttons_svg.clicked.connect(self.plot.to_svg)

    def combo_switch_check(self):
        """ Show either the functional units or methods combo-box, dependent on button state. """
        if self.combobox_menu_switch.text() == "Methods":
            self.combobox_menu_switch.setText("Functional Units")
            self.combobox_menu_label.setText(self.combobox_menu_method_label)
        else:
            self.combobox_menu_switch.setText("Methods")
            self.combobox_menu_label.setText(self.combobox_menu_func_label)
        self.update_analysis_tab()


    def cutoff_increment_left_check(self):
        """ Move the slider 1 increment when left button is clicked. """
        if self.cutoff_type_relative.isChecked():
            num = int(self.cutoff_slider_log_slider.value())
            self.cutoff_slider_log_slider.setValue(num + 1)
        else:
            num = int(self.cutoff_slider_slider.value())
            self.cutoff_slider_slider.setValue(num - 1)

    def cutoff_increment_right_check(self):
        """ Move the slider 1 increment when right button is clicked. """
        if self.cutoff_type_relative.isChecked():
            num = int(self.cutoff_slider_log_slider.value())
            self.cutoff_slider_log_slider.setValue(num - 1)
        else:
            num = int(self.cutoff_slider_slider.value())
            self.cutoff_slider_slider.setValue(num + 1)

    def cutoff_type_relative_check(self):
        """ Set cutoff to process that contribute #% or more. """
        self.cutoff_slider_slider.setVisible(False)
        self.cutoff_slider_log_slider.blockSignals(True)
        self.cutoff_slider_slider.blockSignals(True)
        self.cutoff_slider_line.blockSignals(True)
        self.cutoff_slider_unit.setText("%  of total")
        self.cutoff_slider_min.setText("100%")
        self.cutoff_slider_max.setText("0.001%")
        self.limit_type = "percent"
        self.cutoff_slider_log_slider.blockSignals(False)
        self.cutoff_slider_slider.blockSignals(False)
        self.cutoff_slider_line.blockSignals(False)
        self.cutoff_slider_log_slider.setVisible(True)

    def cutoff_type_topx_check(self):
        """ Set cut-off to the top # of processes. """
        self.cutoff_slider_log_slider.setVisible(False)
        self.cutoff_slider_log_slider.blockSignals(True)
        self.cutoff_slider_slider.blockSignals(True)
        self.cutoff_slider_line.blockSignals(True)
        self.cutoff_slider_unit.setText(" top #")
        self.cutoff_slider_min.setText(str(self.cutoff_slider_slider.minimum()))
        self.cutoff_slider_max.setText(str(self.cutoff_slider_slider.maximum()))
        self.limit_type = "number"
        self.cutoff_slider_log_slider.blockSignals(False)
        self.cutoff_slider_slider.blockSignals(False)
        self.cutoff_slider_line.blockSignals(False)
        self.cutoff_slider_slider.setVisible(True)

    def cutoff_slider_relative_check(self, editor):
        """ With relative selected, change the values for plots and tables to reflect the slider/line-edit. """
        if self.cutoff_type_relative.isChecked():
            self.cutoff_validator = self.cutoff_validator_float
            self.cutoff_slider_line.setValidator(self.cutoff_validator)
            cutoff = float

            # If called by slider
            if editor == "sl":
                self.cutoff_slider_line.blockSignals(True)
                cutoff = abs(self.cutoff_slider_log_slider.logValue())
                self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_line.blockSignals(False)

            # if called by line edit
            elif editor == "le":
                self.cutoff_slider_log_slider.blockSignals(True)
                if self.cutoff_slider_line.text() == '-':
                    cutoff = 0.001
                    self.cutoff_slider_line.setText("0.001")
                elif self.cutoff_slider_line.text() == '':
                    cutoff = 0.001
                else:
                    cutoff = abs(float(self.cutoff_slider_line.text()))

                if cutoff > 100:
                    cutoff = 100
                    self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_log_slider.setLogValue(float(cutoff))
                self.cutoff_slider_log_slider.blockSignals(False)

            self.cutoff_value = (cutoff/100)
            if self.plot:
                self.update_plot()
            if self.table:
                self.update_table()

    def cutoff_slider_topx_check(self, editor):
        """ With top # selected, change the values for plots and tables to reflect the slider/line-edit. """
        if self.cutoff_type_topx.isChecked():
            self.cutoff_validator = self.cutoff_validator_int
            self.cutoff_slider_line.setValidator(self.cutoff_validator)
            cutoff = int

            # If called by slider
            if editor == "sl":
                self.cutoff_slider_line.blockSignals(True)
                cutoff = abs(int(self.cutoff_slider_slider.value()))
                self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_line.blockSignals(False)

            # if called by line edit
            elif editor == "le":
                self.cutoff_slider_slider.blockSignals(True)
                if self.cutoff_slider_line.text() == '-':
                    cutoff = self.cutoff_slider_slider.minimum()
                    self.cutoff_slider_line.setText(str(self.cutoff_slider_slider.minimum()))
                elif self.cutoff_slider_line.text() == '':
                    cutoff = self.cutoff_slider_slider.minimum()
                else:
                    cutoff = abs(int(self.cutoff_slider_line.text()))

                if cutoff > self.cutoff_slider_slider.maximum():
                    cutoff = self.cutoff_slider_slider.maximum()
                    self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_slider.setValue(int(cutoff))
                self.cutoff_slider_slider.blockSignals(False)

            self.cutoff_value = int(cutoff)
            if self.plot:
                self.update_plot()
            if self.table:
                self.update_table()

    def add_cutoff(self):
        """ Add the cut-off menu to the tab. """
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
        self.cutoff_value = 5
        self.cutoff_slider_slider = QSlider(Qt.Horizontal)
        self.cutoff_slider_log_slider = LogarithmicSlider(self)
        self.cutoff_slider_log_slider.setInvertedAppearance(True)
        self.cutoff_slider_slider.setMinimum(1)
        self.cutoff_slider_slider.setMaximum(50)
        self.cutoff_slider_slider.setValue(self.cutoff_value)
        self.cutoff_slider_log_slider.setLogValue(0.01)
        self.cutoff_slider_minmax = QHBoxLayout()
        self.cutoff_slider_min = QLabel("100%")
        self.cutoff_slider_max = QLabel("0.001%")
        self.cutoff_slider_ledit = QHBoxLayout()
        self.cutoff_slider_line = QLineEdit()
        self.cutoff_validator_int = QIntValidator(self.cutoff_slider_line)
        self.cutoff_validator_float = QDoubleValidator(self.cutoff_slider_line)
        self.cutoff_validator = self.cutoff_validator_int
        self.cutoff_slider_line.setValidator(self.cutoff_validator)

        self.cutoff_slider_unit = QLabel("%  of total")

        self.cutoff_slider_lft_btn = QPushButton("<")
        self.cutoff_slider_lft_btn.setMaximumWidth(15)
        self.cutoff_slider_rght_btn = QPushButton(">")
        self.cutoff_slider_rght_btn.setMaximumWidth(15)

        # Assemble types
        self.cutoff_type.addWidget(self.cutoff_type_label)
        self.cutoff_type.addWidget(self.cutoff_type_relative)
        self.cutoff_type.addWidget(self.cutoff_type_topx)

        # Assemble slider set
        self.cutoff_slider_set.addWidget(self.cutoff_slider_label)
        self.cutoff_slider_set.addWidget(self.cutoff_slider_slider)
        self.cutoff_slider_slider.setVisible(False)
        self.cutoff_slider_set.addWidget(self.cutoff_slider_log_slider)
        self.cutoff_slider_minmax.addWidget(self.cutoff_slider_min)
        self.cutoff_slider_minmax.addStretch()
        self.cutoff_slider_minmax.addWidget(self.cutoff_slider_max)
        self.cutoff_slider_set.addLayout(self.cutoff_slider_minmax)

        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_line)
        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_lft_btn)
        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_rght_btn)
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

    def main_space_check(self, table_ch, plot_ch):
        """ Show only table or graph, whichever is selected. """
        table_state = table_ch.isChecked()
        plot_state = plot_ch.isChecked()

        if table_state and plot_state:
            self.main_space_table.setVisible(True)
            self.main_space_plot.setVisible(True)

        elif not table_state and plot_state:
            self.main_space_table.setVisible(False)
            self.main_space_plot.setVisible(True)

        else:
            self.main_space_tb_grph_table.setChecked(True)
            self.main_space_table.setVisible(True)
            self.main_space_plot.setVisible(False)


    def add_main_space(self):
        """ Add the main space to the tab. """
        # Why is this a function and not implemented in the init?;
        # This way, the main space can easily be altered for a specific use if required

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

    def update_analysis_tab(self):
        if self.combobox_menu_combobox != None:
            self.update_combobox()
        if self.plot:
            self.update_plot()
        if self.table:
            self.update_table()

    def update_table(self):
        """ Update the table. """
        self.table.sync(self.setup.mlca)

    def add_combobox(self, method=True, func=False):
        """ Add the combobox menu to the tab. """
        self.combobox_menu = QHBoxLayout()

        self.combobox_menu_label = QLabel()

        self.combobox_menu_combobox = None
        self.combobox_menu_switch = None
        self.combobox_menu_method_label = None
        self.combobox_menu_method_bool = method
        self.combobox_menu_func_bool = func

        if self.combobox_menu_func_bool:
            self.combobox_menu_func_label = "Functional Unit: "
            self.combobox_menu_combobox_func = QComboBox()
            self.combobox_menu_combobox_func.scroll = False
            self.combobox_menu_combobox = self.combobox_menu_combobox_func
            self.combobox_menu_label.setText(self.combobox_menu_func_label)

        if self.combobox_menu_method_bool:
            self.combobox_menu_method_label = "Assessment Method: "
            self.combobox_menu_combobox_method = QComboBox()
            self.combobox_menu_combobox_method.scroll = False
            self.combobox_menu_combobox = self.combobox_menu_combobox_method
            self.combobox_menu_label.setText(self.combobox_menu_method_label)

        if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
            self.combobox_menu_switch = QPushButton("Functional Units")

        self.combobox_menu.addWidget(self.combobox_menu_label)
        self.combobox_menu.addWidget(self.combobox_menu_combobox, 1)

        if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
            self.combobox_menu.addWidget(self.combobox_menu_switch)

        self.combobox_menu_horizontal = horizontal_line()
        self.combobox_menu.addStretch(1)

        self.layout.addLayout(self.combobox_menu)
        self.layout.addWidget(self.combobox_menu_horizontal)

    def update_combobox(self):
        """ Update the combobox menu. """
        self.combobox_menu_combobox.clear()
        visibility = True
        self.combobox_menu_combobox.blockSignals(True)

        if self.combobox_menu_label.text() == self.combobox_menu_method_label: # if is assessment methods
            self.combobox_list = list(self.setup.method_dict.keys())
            if self.setup.single_method:
                visibility = False

        else:
            self.combobox_list = list(self.setup.mlca.func_unit_translation_dict.keys())
            if self.setup.single_func_unit:
                visibility = False

        self.combobox_menu_combobox.insertItems(0, self.combobox_list)
        self.combobox_menu_combobox.blockSignals(False)

        if visibility:
            self.combobox_menu_label.setVisible(True)
            self.combobox_menu_combobox.setVisible(True)
            self.combobox_menu_horizontal.setVisible(True)
            if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
                self.combobox_menu_switch.setVisible(True)
        else:
            self.combobox_menu_label.setVisible(False)
            self.combobox_menu_combobox.setVisible(False)
            self.combobox_menu_horizontal.setVisible(False)
            if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
                self.combobox_menu_switch.setVisible(False)

    def add_export(self):
        """ Add the export menu to the tab. """
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


class LCAScoreComparison(AnalysisTab):
    def __init__(self, parent):
        super(LCAScoreComparison, self).__init__(parent)
        self.setup = parent

        self.name = "LCA score comparison"
        self.header.setText(self.name)

        self.plot = LCAResultsBarChart(self.setup)

        self.add_combobox(method=True, func=False)
        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

        self.connect_analysis_signals()

    def update_plot(self, method=None):
        if method == None or method == '':
            method = self.setup.mlca.methods[0]
        else:
            method = self.setup.method_dict[method]
        self.plot.plot(self.setup.mlca, method=method)


class Inventory(AnalysisTab):
    def __init__(self, parent):
        super(Inventory, self).__init__(parent)
        self.setup = parent

        self.name = "Inventory"
        self.header.setText(self.name)

        self.table = InventoryTable(self.setup)

        self.add_combobox(method=False, func=True)
        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

        self.connect_analysis_signals()

    def update_table(self, method=None):
        if method == None:
            method = (list(self.setup.mlca.technosphere_flows))[0]
        else:
            pass
        #print('translated: ', [str(get_activity(list(method.keys())[0]))])
        self.table.sync(self.setup.mlca, method=method)#, limit=self.cutoff_value)


class InventoryCharacterisation(AnalysisTab):
    def __init__(self, parent):
        super(InventoryCharacterisation, self).__init__(parent)
        self.setup = parent

        self.name = "Inventory Characterisation"
        self.header.setText(self.name)

        self.plot = InventoryCharacterisationPlot(self.setup)
        self.table = InventoryCharacterisationTable(self)

        self.add_cutoff()
        self.cutoff_value = 0.01
        self.add_combobox(method=True, func=True)
        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

        self.connect_analysis_signals()

    def update_plot(self, method=None):
        if self.combobox_menu_label.text() == self.combobox_menu_method_label:
            if method == None or method == '':
                method = self.setup.mlca.methods[0]
            else:
                method = self.setup.method_dict[method]
            func = None
            per = "method"
        else:
            func = method
            if func == None or func == '':
                func = self.setup.mlca.func_key_list[0]
            method = None
            per = "func"

        self.plot.plot(self.setup.mlca, method=method, func=func, limit=self.cutoff_value,
                       limit_type=self.limit_type, per=per)


class LCIAAnalysis(AnalysisTab):
    def __init__(self, parent):
        super(LCIAAnalysis, self).__init__(parent)
        self.setup = parent

        self.name = "LCIA Results"
        self.header.setText(self.name)

        if not self.setup.single_func_unit:
            self.plot = LCAResultsPlot(self.setup)
            self.table = LCAResultsTable()

        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

        self.connect_analysis_signals()

    def update_plot(self):
        if isinstance(self.plot, LCAResultsPlot):
            self.plot.plot(self.setup.mlca)
        else:
            self.plot = LCAResultsPlot(self.setup)
            self.plot.plot(self.setup.mlca)

    def update_table(self):
        if isinstance(self.table, LCAResultsTable):
            self.table.sync(self.setup.mlca)
        else:
            self.table = LCAResultsTable()
            self.table.sync(self.setup.mlca)


class ProcessContributions(AnalysisTab):
    def __init__(self, parent):
        super(ProcessContributions, self).__init__(parent)
        self.setup = parent

        self.name = "Process Contributions"
        self.header.setText(self.name)

        self.plot = ProcessContributionPlot(self.setup)
        self.table = ProcessContributionsTable(self)

        self.add_cutoff()
        self.cutoff_value = 0.05
        self.add_combobox(method=True, func=True)
        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

        self.connect_analysis_signals()

    def update_plot(self, method=None):
        if self.combobox_menu_label.text() == self.combobox_menu_method_label:
            if method == None or method == '':
                method = self.setup.mlca.methods[0]
            else:
                method = self.setup.method_dict[method]
            func = None
            per = "method"
        else:
            func = method
            if func == None or func == '':
                func = self.setup.mlca.func_key_list[0]
            method = None
            per = "func"

        self.plot.plot(self.setup.mlca, method=method, func=func, limit=self.cutoff_value,
                       limit_type=self.limit_type, per=per, normalised=False)


class Correlations(AnalysisTab):
    def __init__(self, parent):
        super(Correlations, self).__init__(parent)
        self.setup = parent

        self.name = "Correlations"
        self.header.setText(self.name)

        if not self.setup.single_func_unit:
            self.plot = CorrelationPlot(self.setup)

        self.add_main_space()
        self.add_export()

        self.setup.addTab(self, self.name)

        self.connect_analysis_signals()

    def update_plot(self):
        if isinstance(self.plot, CorrelationPlot):
            labels = [str(x + 1) for x in range(len(self.setup.mlca.func_units))]
            self.plot.plot(self.setup.mlca, labels)
        else:
            self.plot = CorrelationPlot(self.setup)
            labels = [str(x + 1) for x in range(len(self.setup.mlca.func_units))]
            self.plot.plot(self.setup.mlca, labels)