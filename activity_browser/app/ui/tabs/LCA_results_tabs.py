# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QRadioButton, \
    QLabel, QCheckBox, QPushButton, QComboBox

from ..style import horizontal_line, vertical_line, header
from ..tables import (
    LCAResultsTable,
    ContributionTable,
    InventoryTable,
)
from ..figures import (
    LCAResultsPlot,
    ContributionPlot,
    CorrelationPlot,
    LCAResultsBarChart
)
from ...bwutils.multilca import MLCA, Contributions
from ...bwutils import commontasks as bc
from ..widgets import CutoffMenu
from ..web.graphnav import SankeyNavigatorWidget


# TODO: LOW PRIORITY: add filtering for tables/graphs


class LCAResultsSubTab(QTabWidget):
    def __init__(self, parent, name):
        super(LCAResultsSubTab, self).__init__(parent)
        # self.panel = parent
        self.cs_name = name
        self.method_dict = dict()

        self.setMovable(True)
        self.setVisible(False)
        self.visible = False

        # self.setTabShape(2)  # Triangular-shaped Tabs
        # self.setTabPosition(1)  # South-facing Tabs

        self.update_calculation()

        # the LCA results tabs (order matters)
        self.inventory_tab = InventoryTab(self)
        self.LCA_scores_tab = LCAScoresTab(self)
        self.lcia_results_tab = LCIAResultsTab(self, relativity=True)

        self.EF_contribution_tab = ElementaryFlowContributionTab(self, relativity=True)

        self.process_contributions_tab = ProcessContributionsTab(self, relativity=True)
        # self.correlations_tab = CorrelationsTab(self)
        self.sankey_tab = SankeyNavigatorWidget(self.cs_name, parent=self)
        self.addTab(self.sankey_tab, "Sankey")

        self.update_setup(calculate=False)
        self.setCurrentWidget(self.LCA_scores_tab)
        self.currentChanged.connect(self.generate_content_on_click)

    def update_calculation(self):
        """ Update the mlca calculation. """
        self.mlca = MLCA(self.cs_name)
        self.contributions = Contributions(self.mlca)

        self.method_dict = bc.get_LCIA_method_name_dict(self.mlca.methods)

        if len(self.mlca.func_units) != 1:
            self.single_func_unit = False
        else:
            self.single_func_unit = True
        if len(self.mlca.methods) != 1:
            self.single_method = False
        else:
            self.single_method = True

    def update_setup(self, calculate=True):
        """ Update the calculation setup. """
        if calculate:
            self.update_calculation()

        # self.LCA_scores_tab.update_analysis_tab()
        self.LCA_scores_tab.update_tab()
        # self.inventory_tab.update_analysis_tab()
        self.EF_contribution_tab.update_analysis_tab()
        self.lcia_results_tab.update_analysis_tab()
        self.process_contributions_tab.update_analysis_tab()
        # self.correlations_tab.update_analysis_tab()

        lca_score_comparison_tab_index = self.indexOf(self.LCA_scores_tab)
        lcia_results_tab_index = self.indexOf(self.lcia_results_tab)
        # correlations_tab_index = self.indexOf(self.correlations_tab)
        self.sankey_tab.update_calculation_setup(cs_name=self.cs_name)

        # if not self.single_func_unit:
        #     self.setTabEnabled(lcia_results_tab_index, True)
        #
        #     # self.setTabEnabled(correlations_tab_index, True)
        #     self.setTabEnabled(lca_score_comparison_tab_index, True)
        # else:
        #     self.lca_score_comparison_tab_index.setVisible(False)
        #     # self.setTabEnabled(lcia_results_tab_index, False)
        #     # self.setTabEnabled(correlations_tab_index, False)
        #     self.setTabEnabled(lca_score_comparison_tab_index, False)

    def generate_content_on_click(self, index):
        if index == self.indexOf(self.sankey_tab):
            if not self.sankey_tab.has_sankey:
                print('Generating Sankey Tab')
                self.sankey_tab.new_sankey()
        elif index == self.indexOf(self.inventory_tab):
            if self.inventory_tab.table.dataframe is None:
                print('Generating Inventory Tab')
                self.inventory_tab.update_table()


class AnalysisTab(QWidget):
    def __init__(self, parent, combobox=None, table=None,\
                 plot=None, export=None, relativity=None, custom=False, *args, **kwargs):
        super(AnalysisTab, self).__init__(parent)
        self.parent = parent
        self.first_time_calculated = False

        self.custom = custom

        self.combobox_menu_combobox = combobox
        self.table = table
        self.plot = plot
        self.export_menu = export
        self.relativity = relativity
        self.relative = True

        self.header = header("Description of the tab")

        self.layout = QVBoxLayout()

        self.TopStrip = QHBoxLayout()
        self.setLayout(self.layout)
        self.TopStrip.addWidget(self.header)
        self.layout.addLayout(self.TopStrip)
        self.layout.addWidget(horizontal_line())

        # self.connect_signals()  # called by the sub-classes

    def connect_signals(self):
        # Combo box signal
        if self.combobox_menu_combobox != None:
            if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
                self.combobox_menu_switch_met.clicked.connect(self.combo_switch_check)
                self.combobox_menu_switch_fun.clicked.connect(self.combo_switch_check)

            if self.plot:
                self.combobox_menu_combobox.currentTextChanged.connect(
                    lambda name: self.update_plot(method=name))

            if self.table:
                self.combobox_menu_combobox.currentTextChanged.connect(
                    lambda name: self.update_table(method=name))

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

    def add_header(self, header_text):
        if isinstance(header_text, str):
            self.header.setText(header_text)

    def combo_switch_check(self):
        """ Show either the functional units or methods combo-box, dependent on button state. """
        if self.combo_box_menu_options == "Compare LCIA Methods":
            self.combo_box_menu_options = "Compare Functional Units"
            self.combobox_menu_label.setText(self.combobox_menu_method_label)
            self.combobox_menu_switch_met.setChecked(False)
            self.combobox_menu_switch_fun.setChecked(True)
        else:
            self.combo_box_menu_options = "Compare LCIA Methods"
            self.combobox_menu_label.setText(self.combobox_menu_func_label)
            self.combobox_menu_switch_met.setChecked(True)
            self.combobox_menu_switch_fun.setChecked(False)
        self.update_combobox()

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

        # Option switches
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
        self.main_space_tb_grph.addWidget(vertical_line())
        self.relativity_button(self.main_space_tb_grph)
        self.main_space_tb_grph.addStretch()

        # Assemble Table and Plot area
        if self.table and self.plot:
            self.main_space_widget_layout.addLayout(self.main_space_tb_grph)
        if self.plot:
            self.main_space_widget_layout.addWidget(self.main_space_plot, 1)
        if self.table:
            self.main_space_widget_layout.addWidget(self.main_space_table)
        self.main_space_widget_layout.addStretch()

        if not self.custom:
            pass
            # self.main_space_widget_layout.addStretch()

        self.layout.addWidget(self.main_space)

    def update_analysis_tab(self):
        if self.combobox_menu_combobox != None:
            self.update_combobox()
        if self.plot:
            self.update_plot()
        if self.table:
            self.update_table()
            self.first_time_calculated = True

    def update_table(self, method=None, *args, **kwargs):
        """ Update the table. """
        # self.table.sync(self.parent.mlca, *args, **kwargs)
        self.table.sync(*args, **kwargs)

    def update_plot(self, method=None):
        """Updates the plot. Method will be added in subclass."""
        pass

    def relativity_button(self, layout):
        if self.relativity is not None:
            self.button1 = QRadioButton("Relative")
            self.button1.setChecked(True)
            self.button2 = QRadioButton("Absolute")
            layout.addStretch(1)
            layout.addWidget(self.button1)
            layout.addWidget(self.button2)
            self.button1.clicked.connect(self.relativity_check)
            self.button2.clicked.connect(self.relativity_check)

    def relativity_check(self):
        if self.relative == False:
            self.button1.setChecked(True)
            self.button2.setChecked(False)
            self.relative = True
        else:
            self.button1.setChecked(False)
            self.button2.setChecked(True)
            self.relative = False
        if self.plot:
            self.update_plot()
        if self.table:
            self.update_table()

    def add_combobox(self, method=True, func=False):
        """ Add the combobox menu to the tab. """
        self.combobox_menu = QHBoxLayout()

        self.combobox_menu_label = QLabel()

        self.combobox_menu_combobox = None
        self.combobox_menu_switch_met = None
        self.combobox_menu_method_label = None
        self.combobox_menu_method_bool = method
        self.combobox_menu_func_bool = func

        if self.combobox_menu_func_bool:
            self.combobox_menu_func_label = "Choose Functional Unit: "
            self.combobox_menu_combobox_func = QComboBox()
            self.combobox_menu_combobox_func.scroll = False
            self.combobox_menu_combobox = self.combobox_menu_combobox_func
            self.combobox_menu_label.setText(self.combobox_menu_func_label)

        if self.combobox_menu_method_bool:
            self.combobox_menu_method_label = "Choose LCIA Method: "
            self.combobox_menu_combobox_method = QComboBox()
            self.combobox_menu_combobox_method.scroll = False
            self.combobox_menu_combobox = self.combobox_menu_combobox_method
            self.combobox_menu_label.setText(self.combobox_menu_method_label)

        if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
            self.combobox_menu.addStretch(1)
            self.combo_box_menu_options = "Functional Units"
            self.combobox_menu_switch_met = QRadioButton("Compare LCIA Methods")
            self.combobox_menu.addWidget(self.combobox_menu_switch_met)

            self.combobox_menu_switch_fun = QRadioButton("Compare Functional Units")
            self.combobox_menu_switch_fun.setChecked(True)

            self.combobox_menu.addWidget(self.combobox_menu_switch_fun)


        self.combobox_menu.addWidget(vertical_line())

        self.combobox_menu.addWidget(self.combobox_menu_label)
        self.combobox_menu.addWidget(self.combobox_menu_combobox, 1)

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
            self.combobox_list = list(self.parent.method_dict.keys())
            if self.parent.single_method:
                visibility = False

        else:
            self.combobox_list = list(self.parent.mlca.func_unit_translation_dict.keys())
            if self.parent.single_func_unit:
                visibility = False

        self.combobox_menu_combobox.insertItems(0, self.combobox_list)
        self.combobox_menu_combobox.blockSignals(False)

        if visibility:
            self.combobox_menu_label.setVisible(True)
            self.combobox_menu_combobox.setVisible(True)
            self.combobox_menu_horizontal.setVisible(True)
            if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
                self.combobox_menu_switch_met.setVisible(True)
        else:
            self.combobox_menu_label.setVisible(False)
            self.combobox_menu_combobox.setVisible(False)
            self.combobox_menu_horizontal.setVisible(False)
            if self.combobox_menu_method_bool and self.combobox_menu_func_bool:
                self.combobox_menu_switch_met.setVisible(False)

    def add_export(self):
        """ Add the export menu to the tab. """
        self.export_menu = QHBoxLayout()

        # Export Plot
        self.export_plot = QHBoxLayout()
        self.export_plot_label = QLabel("Export plot:")
        self.export_plot_buttons_png = QPushButton(".png")
        self.export_plot_buttons_svg = QPushButton(".svg")
        # Export Table
        self.export_table = QHBoxLayout()
        self.export_table_label = QLabel("Export table:")
        self.export_table_buttons_copy = QPushButton("Copy")
        self.export_table_buttons_csv = QPushButton(".csv")
        self.export_table_buttons_excel = QPushButton("Excel")
        # Assemble export plot
        self.export_plot.addWidget(self.export_plot_label)
        self.export_plot.addWidget(self.export_plot_buttons_png)
        self.export_plot.addWidget(self.export_plot_buttons_svg)
        # Assemble export table
        self.export_table.addWidget(self.export_table_label)
        self.export_table.addWidget(self.export_table_buttons_copy)
        self.export_table.addWidget(self.export_table_buttons_csv)
        self.export_table.addWidget(self.export_table_buttons_excel)

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


class NewAnalysisTab(QWidget):
    def __init__(self, parent):
        super(NewAnalysisTab, self).__init__(parent)

        self.header = header("Description of the tab")

        self.layout = QVBoxLayout()

        self.TopStrip = QHBoxLayout()
        self.TopStrip.addWidget(self.header)
        self.layout.addLayout(self.TopStrip)
        self.layout.addWidget(horizontal_line())

        self.setLayout(self.layout)

    def add_header(self, header_text):
        if isinstance(header_text, str):
            self.header.setText(header_text)

    def add_combobox(self, label='Choose LCIA method:'):
        """ Add the combobox menu to the tab. """
        self.combobox_label = QLabel(label)
        self.combobox = QComboBox()
        self.combobox.scroll = False

        self.combobox_menu = QHBoxLayout()
        self.combobox_menu.addWidget(self.combobox_label)
        self.combobox_menu.addWidget(self.combobox, 1)
        self.combobox_menu.addStretch(1)

        self.layout.addLayout(self.combobox_menu)

    def update_combobox(self, labels):
        """ Update the combobox menu. """
        self.combobox.clear()
        self.combobox.blockSignals(True)
        self.combobox.insertItems(0, labels)
        self.combobox.blockSignals(False)

    def add_export(self):
        """ Add the export menu to the tab. """
        self.export_menu = QHBoxLayout()

        # Export Plot
        self.export_plot = QHBoxLayout()
        self.export_plot_label = QLabel("Export plot:")
        self.export_plot_buttons_png = QPushButton(".png")
        self.export_plot_buttons_svg = QPushButton(".svg")
        # Export Table
        self.export_table = QHBoxLayout()
        self.export_table_label = QLabel("Export table:")
        self.export_table_buttons_copy = QPushButton("Copy")
        self.export_table_buttons_csv = QPushButton(".csv")
        self.export_table_buttons_excel = QPushButton("Excel")
        # Assemble export plot
        self.export_plot.addWidget(self.export_plot_label)
        self.export_plot.addWidget(self.export_plot_buttons_png)
        self.export_plot.addWidget(self.export_plot_buttons_svg)
        # Assemble export table
        self.export_table.addWidget(self.export_table_label)
        self.export_table.addWidget(self.export_table_buttons_copy)
        self.export_table.addWidget(self.export_table_buttons_csv)
        self.export_table.addWidget(self.export_table_buttons_excel)

        # Assemble export menu
        if hasattr(self, 'plot'):
            self.export_menu.addLayout(self.export_plot)
        if hasattr(self, 'table') and hasattr(self, 'plot'):
            self.export_menu_vert_line = vertical_line()
            self.export_menu.addWidget(self.export_menu_vert_line)
        if hasattr(self, 'table'):
            self.export_menu.addLayout(self.export_table)
        self.export_menu.addStretch()

        # self.layout.addWidget(horizontal_line())
        self.layout.addLayout(self.export_menu)

        # Export Table
        if hasattr(self, 'table') and self.export_menu:
            self.export_table_buttons_copy.clicked.connect(self.table.to_clipboard)
            self.export_table_buttons_csv.clicked.connect(self.table.to_csv)
            self.export_table_buttons_excel.clicked.connect(self.table.to_excel)

        # Export Plot
        if hasattr(self, 'plot') and self.export_menu:
            self.export_plot_buttons_png.clicked.connect(self.plot.to_png)
            self.export_plot_buttons_svg.clicked.connect(self.plot.to_svg)


class InventoryTab(NewAnalysisTab):
    def __init__(self, parent=None):
        super(InventoryTab, self).__init__(parent)
        self.parent = parent
        self.df_biosphere = None
        self.df_technosphere = None

        self.header_text = "Inventory"
        self.add_header(self.header_text)
        self.add_radio_buttons()
        self.table = InventoryTable(self.parent)
        self.layout.addWidget(self.table)

        # self.add_main_space()

        self.add_export()

        self.parent.addTab(self, self.header_text)

        # self.connect_signals()

    def add_radio_buttons(self):
        """ Add the radio buttons."""
        # buttons
        self.radio_button_biosphere = QRadioButton("Biosphere flows")
        self.radio_button_technosphere = QRadioButton("Technosphere flows")

        self.radio_button_biosphere.setChecked(True)
        self.radio_button_technosphere.setChecked(False)

        # signals
        self.radio_button_biosphere.clicked.connect(self.button_clicked)
        self.radio_button_technosphere.clicked.connect(self.button_clicked)

        # layout
        self.combobox_menu = QHBoxLayout()
        self.combobox_menu.addWidget(self.radio_button_biosphere)
        self.combobox_menu.addWidget(self.radio_button_technosphere)
        self.combobox_menu.addStretch(1)

        self.layout.addLayout(self.combobox_menu)

    def button_clicked(self):
        """Update table according to radiobutton selected."""
        if self.radio_button_technosphere.isChecked():
            self.update_table(type='technosphere')
        else:
            self.update_table(type='biosphere')

    def update_table(self, type='biosphere'):
        if type == 'biosphere':
            if self.df_biosphere is None:
                self.df_biosphere = self.parent.contributions.inventory_df(type='biosphere')
            self.table.sync(self.df_biosphere)

        else:
            if self.df_technosphere is None:
                self.df_technosphere = self.parent.contributions.inventory_df(type='technosphere')
            self.table.sync(self.df_technosphere)


class LCAScoresTab(NewAnalysisTab):
    def __init__(self, parent=None):
        super(LCAScoresTab, self).__init__(parent)
        self.parent = parent

        self.header_text = "LCA scores comparison"
        self.add_header(self.header_text)

        self.add_combobox(label='Choose LCIA method')

        self.plot = LCAResultsBarChart(self.parent)
        self.plot.plot_name = 'LCA scores_' + self.parent.cs_name
        self.layout.addWidget(self.plot)

        self.add_export()
        self.parent.addTab(self, "LCA scores")

        self.connect_signals()

    def connect_signals(self):
        self.combobox.currentIndexChanged.connect(self.update_plot)

    def update_tab(self):
        self.update_combobox([str(m) for m in self.parent.mlca.methods])
        self.update_plot(method_index=0)

    def update_plot(self, method_index=None):
        if method_index is None or isinstance(method_index, str):
            method_index = 0
        self.plot.plot(self.parent.mlca, method=self.parent.mlca.methods[method_index])


class LCIAResultsTab(AnalysisTab):
    def __init__(self, parent, **kwargs):
        super(LCIAResultsTab, self).__init__(parent, **kwargs)
        self.parent = parent
        self.df = None

        self.header_text = "LCIA Results"
        self.add_header(self.header_text)

        if not self.parent.single_func_unit:
            self.plot = LCAResultsPlot(self.parent)
            self.table = LCAResultsTable(self.parent)

        self.add_main_space()
        self.add_export()

        self.parent.addTab(self, self.header_text)

        self.connect_signals()
        self.relative = False

    def update_plot(self):
        if not isinstance(self.plot, LCAResultsPlot):
            self.plot = LCAResultsPlot(self.parent)
        self.df = self.parent.contributions.lca_scores_df(normalized=self.relative)
        self.plot.plot(self.df)

    def update_table(self):
        if not isinstance(self.table, LCAResultsTable):
            self.table = LCAResultsTable()
        self.df = self.parent.contributions.lca_scores_df(normalized=self.relative)
        self.table.sync(self.df)


class ElementaryFlowContributionTab(AnalysisTab):
    def __init__(self, parent, **kwargs):
        super(ElementaryFlowContributionTab, self).__init__(parent, **kwargs)
        self.parent = parent

        self.header_text = "Elementary Flow Contributions"
        self.add_header(self.header_text)

        self.cutoff_menu = CutoffMenu(self, cutoff_value=0.05)
        self.layout.addWidget(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())

        self.df = None
        self.plot = ContributionPlot()
        self.plot.plot_name = 'EF contributions_' + self.parent.cs_name
        self.table = ContributionTable(self)

        self.add_combobox(method=True, func=True)
        self.add_main_space()
        self.add_export()

        self.parent.addTab(self, 'Substance Contributions')

        self.connect_signals()

    def update_plot(self, method=None):
        if self.combobox_menu_label.text() == self.combobox_menu_method_label:
            if method is None or method == '':
                method = self.parent.mlca.methods[0]
            else:
                method = self.parent.method_dict[method]
            func = None
        else:
            func = method
            if func is None or func == '':
                func = self.parent.mlca.func_key_list[0]
            method = None

        self.df = self.parent.contributions.top_elementary_flow_contributions(
            functional_unit=func, method=method, limit=self.cutoff_menu.cutoff_value,
            limit_type=self.cutoff_menu.limit_type, normalize=self.relative)
        self.plot.plot(self.df)


class ProcessContributionsTab(AnalysisTab):
    def __init__(self, parent, **kwargs):
        super(ProcessContributionsTab, self).__init__(parent, **kwargs)
        self.parent = parent

        self.header_text = "Process Contributions"
        self.add_header(self.header_text)

        self.cutoff_menu = CutoffMenu(self, cutoff_value=0.05)
        self.layout.addWidget(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())

        self.plot = ContributionPlot()
        self.plot.plot_name = 'Process contributions_' + self.parent.cs_name
        self.table = ContributionTable(self)

        self.add_combobox(method=True, func=True)
        self.add_main_space()
        self.add_export()

        self.parent.addTab(self, self.header_text)

        self.connect_signals()

    def update_plot(self, method=None):
        if self.combobox_menu_label.text() == self.combobox_menu_method_label:
            if method == None or method == '':
                method = self.parent.mlca.methods[0]
            else:
                method = self.parent.method_dict[method]
            func = None
        else:
            func = method
            if func == None or func == '':
                func = self.parent.mlca.func_key_list[0]
            method = None

        self.df = self.parent.contributions.top_process_contributions(
            functional_unit=func, method=method, limit=self.cutoff_menu.cutoff_value,
            limit_type=self.cutoff_menu.limit_type, normalize=self.relative)
        self.plot.plot(self.df)


class CorrelationsTab(AnalysisTab):
    def __init__(self, parent, **kwargs):
        super(CorrelationsTab, self).__init__(parent, **kwargs)
        self.parent = parent

        self.tab_text = "Correlations"
        self.add_header("Correlation Analysis")

        if not self.parent.single_func_unit:
            self.plot = CorrelationPlot(self.parent)

        self.add_main_space()
        self.add_export()

        self.parent.addTab(self, self.tab_text)

        self.connect_signals()

    def update_plot(self):
        if isinstance(self.plot, CorrelationPlot):
            labels = [str(x + 1) for x in range(len(self.parent.mlca.func_units))]
            self.plot.plot(self.parent.mlca, labels)
        else:
            self.plot = CorrelationPlot(self.parent)
            labels = [str(x + 1) for x in range(len(self.parent.mlca.func_units))]
            self.plot.plot(self.parent.mlca, labels)


class SankeyTab(QWidget):
    def __init__(self, parent):
        super(SankeyTab, self).__init__(parent)
        self.parent = parent
