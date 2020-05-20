# -*- coding: utf-8 -*-
"""Classes related to the LCA results sub-tabs in the main LCA results tab.

Each of these classes is either a parent for - or a sub-LCA results tab.
"""

from collections import namedtuple
from typing import List, Optional, Union

from bw2calc.errors import BW2CalcError
from PySide2.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QRadioButton,
    QLabel, QLineEdit, QCheckBox, QPushButton, QComboBox, QTableView,
    QButtonGroup, QMessageBox, QGroupBox, QGridLayout
)
from PySide2 import QtGui, QtCore
from stats_arrays.errors import InvalidParamsError
import traceback

from ...bwutils import (
    Contributions, CSMonteCarloLCA, MLCA, PresamplesContributions,
    PresamplesMLCA, SuperstructureContributions, SuperstructureMLCA,
    commontasks as bc
)
from ...signals import signals
from ..figures import (
    LCAResultsPlot, ContributionPlot, CorrelationPlot, LCAResultsBarChart, MonteCarloPlot
)
from ..style import horizontal_line, vertical_line, header
from ..tables import ContributionTable, InventoryTable, LCAResultsTable
from ..widgets import CutoffMenu, SwitchComboBox
from ..web import SankeyNavigatorWidget


def get_header_layout(header_text: str) -> QVBoxLayout:
    vlayout = QVBoxLayout()
    vlayout.addWidget(header(header_text))
    vlayout.addWidget(horizontal_line())
    return vlayout


def get_unit(method: tuple, relative: bool = False) -> str:
    """Get the unit for plot axis naming.

    Determine the unit based on whether a plot is shown:
    - for a number of functional units
    - for a number of impact categories
    and whether the axis are related to:
    - relative or
    - absolute numbers.
    """
    if relative:
        return "relative share"
    if method:  # for all functional units
        return bc.unit_of_method(method)
    return "units of each LCIA method"


# Special namedtuple for the LCAResults TabWidget.
Tabs = namedtuple(
    "tabs", ("inventory", "results", "ef", "process", "mc", "sankey")
)
Relativity = namedtuple("relativity", ("relative", "absolute"))
ExportTable = namedtuple("export_table", ("label", "copy", "csv", "excel"))
ExportPlot = namedtuple("export_plot", ("label", "png", "svg"))
PlotTableCheck = namedtuple("plot_table_space", ("plot", "table"))
Combobox = namedtuple(
    "combobox_menu", (
        "func", "func_label", "method", "method_label",
        "agg", "agg_label", "scenario", "scenario_label",
    )
)


class LCAResultsSubTab(QTabWidget):
    """Class for the main 'LCA Results' tab.

    Shows:
        One sub-tab for each calculation setup
        For each calculation setup-tab one array of relevant tabs.
    """

    update_scenario_box_index = QtCore.Signal(int)

    def __init__(self, name: str, presamples=None, parent=None):
        super().__init__(parent)
        self.cs_name = name
        self.presamples = presamples
        self.mlca: Optional[Union[MLCA, PresamplesMLCA, SuperstructureMLCA]] = None
        self.contributions: Optional[Contributions] = None
        self.mc: Optional[CSMonteCarloLCA] = None
        self.method_dict = dict()
        self.single_func_unit = False
        self.single_method = False

        self.setMovable(True)
        self.setVisible(False)
        self.visible = False

        self.do_calculations()
        self.tabs = Tabs(
            inventory=InventoryTab(self),
            results=LCAResultsTab(self),
            ef=ElementaryFlowContributionTab(self),
            process=ProcessContributionsTab(self),
            # mc=None if self.mc is None else MonteCarloTab(self),
            mc=MonteCarloTab(self),
            sankey=SankeyNavigatorWidget(self.cs_name, parent=self),
        )
        self.tab_names = Tabs(
            inventory="Inventory",
            results="LCA Results",
            ef="EF Contributions",
            process="Process Contributions",
            mc="Monte Carlo",
            sankey="Sankey",
        )
        self.setup_tabs()
        self.setCurrentWidget(self.tabs.results)
        self.currentChanged.connect(self.generate_content_on_click)

    def do_calculations(self):
        """Perform the MLCA calculation."""
        if self.presamples is None:
            self.mlca = MLCA(self.cs_name)
            self.contributions = Contributions(self.mlca)
        elif isinstance(self.presamples, str):
            try:
                self.mlca = PresamplesMLCA(self.cs_name, self.presamples)
                self.contributions = PresamplesContributions(self.mlca)
            except IndexError as e:
                # Occurs when a presamples package is used that refers to old
                # or non-existing array indices.
                msg = ("Given scenario package refers to non-existent exchanges."
                       " It is suggested to remove or edit this package.")
                raise BW2CalcError(msg, str(e)).with_traceback(e.__traceback__)
        else:
            try:
                self.mlca = SuperstructureMLCA(self.cs_name, self.presamples)
                self.contributions = SuperstructureContributions(self.mlca)
            except AssertionError as e:
                raise BW2CalcError("Scenario LCA failed.", str(e)).with_traceback(e.__traceback__)
        self.mlca.calculate()
        self.mc = CSMonteCarloLCA(self.cs_name)

        # self.mct = CSMonteCarloLCAThread()
        # self.mct.start()
        # self.mct.initialize(self.cs_name)

        self.method_dict = bc.get_LCIA_method_name_dict(self.mlca.methods)
        self.single_func_unit = True if len(self.mlca.func_units) == 1 else False
        self.single_method = True if len(self.mlca.methods) == 1 else False

    @property
    def using_presamples(self) -> bool:
        """Used to determine if a Scenario Analysis is performed."""
        return all([
            self.presamples is not None,
            isinstance(self.mlca, (PresamplesMLCA, SuperstructureMLCA))
        ])

    def setup_tabs(self):
        """Have all of the tabs pull in their required data and add them."""
        self._update_tabs()
        for name, tab in zip(self.tab_names, self.tabs):
            if tab:
                self.addTab(tab, name)
                if hasattr(tab, "configure_scenario"):
                    tab.configure_scenario()

    def _update_tabs(self):
        """Update each sub-tab that can be updated."""
        for tab in self.tabs:
            if tab and hasattr(tab, "update_tab"):
                tab.update_tab()
        self.tabs.sankey.update_calculation_setup(cs_name=self.cs_name)

    @QtCore.Slot(int, name="updateUnderlyingMatrices")
    def update_scenario_data(self, index: int) -> None:
        """Will calculate which presamples array to use and update all child tabs."""
        if index == self.mlca.current:
            return
        self.mlca.set_scenario(index)
        self._update_tabs()
        self.update_scenario_box_index.emit(index)

    @QtCore.Slot(int, name="generateSankeyOnClick")
    def generate_content_on_click(self, index):
        if index == self.indexOf(self.tabs.sankey):
            if not self.tabs.sankey.has_sankey:
                print('Generating Sankey Tab')
                self.tabs.sankey.new_sankey()


class NewAnalysisTab(QWidget):
    """Parent class around which all sub-tabs are built."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        # Important variables optionally used in subclasses
        self.table: Optional[QTableView] = None
        self.plot: Optional[QWidget] = None
        self.plot_table: Optional[PlotTableCheck] = None
        self.relativity: Optional[Relativity] = None
        self.relative: Optional[bool] = None
        self.export_plot: Optional[ExportPlot] = None
        self.export_table: Optional[ExportTable] = None

        self.scenario_box = QComboBox()
        self.pt_layout = QVBoxLayout()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

    def build_main_space(self) -> QScrollArea:
        """Assemble main space where plots, tables and relevant options are shown."""
        space = QScrollArea()
        widget = QWidget()
        self.pt_layout.setAlignment(QtCore.Qt.AlignTop)
        widget.setLayout(self.pt_layout)
        space.setWidget(widget)
        space.setWidgetResizable(True)

        # Option switches
        self.plot_table = PlotTableCheck(
            QCheckBox("Plot"), QCheckBox("Table")
        )
        self.plot_table.plot.setChecked(True)
        self.plot_table.table.setChecked(True)
        self.plot_table.table.stateChanged.connect(self.space_check)
        self.plot_table.plot.stateChanged.connect(self.space_check)

        # Assemble option row
        row = QHBoxLayout()
        row.addWidget(self.plot_table.plot)
        row.addWidget(self.plot_table.table)
        row.addWidget(vertical_line())
        if self.relativity:
            row.addWidget(self.relativity.relative)
            row.addWidget(self.relativity.absolute)
            self.relativity.relative.toggled.connect(self.relativity_check)
        row.addStretch()

        # Assemble Table and Plot area
        if self.table and self.plot:
            self.pt_layout.addLayout(row)
        if self.plot:
            self.pt_layout.addWidget(self.plot, 1)
        if self.table:
            self.pt_layout.addWidget(self.table)
        self.pt_layout.addStretch()
        return space

    @QtCore.Slot(name="checkboxChanges")
    def space_check(self):
        """Show graph and/or table, whichever is selected.

        Can also hide both, if you want to do that.
        """
        self.table.setVisible(self.plot_table.table.isChecked())
        self.plot.setVisible(self.plot_table.plot.isChecked())

    @QtCore.Slot(bool, name="isRelativeToggled")
    def relativity_check(self, checked: bool):
        """Check if the relative or absolute option is selected."""
        self.relative = checked
        self.update_tab()

    @property
    def using_presamples(self) -> bool:
        """Check if presamples is used."""
        return self.parent.using_presamples if self.parent else False

    def get_scenario_labels(self) -> List[str]:
        """Get scenario labels if presamples is used."""
        return self.parent.mlca.scenario_names if self.using_presamples else []

    def configure_scenario(self):
        """Determine if scenario Qt widgets are visible or not and retrieve
        scenario labels for the selection drop-down box.
        """
        if self.scenario_box:
            self.scenario_box.setVisible(self.using_presamples)
            self.update_combobox(self.scenario_box, self.get_scenario_labels())

    @staticmethod
    @QtCore.Slot(int, name="setBoxIndex")
    def set_combobox_index(box: QComboBox, index: int) -> None:
        """Update the index on the given QComboBox without sending a signal."""
        box.blockSignals(True)
        box.setCurrentIndex(index)
        box.blockSignals(False)

    @staticmethod
    def update_combobox(box: QComboBox, labels: List[str]) -> None:
        """Update the combobox menu."""
        box.blockSignals(True)
        box.clear()
        box.insertItems(0, labels)
        box.blockSignals(False)

    def update_tab(self):
        """Update the plot and table if they are present."""
        if self.plot:
            self.update_plot()
        if self.table:
            self.update_table()

    def update_table(self, *args, **kwargs):
        """Update the table."""
        self.table.sync(*args, **kwargs)

    def update_plot(self, *args, **kwargs):
        """Update the plot."""
        self.plot.plot(*args, **kwargs)

    def build_export(self, has_table: bool = True, has_plot: bool = True) -> QHBoxLayout:
        """Construct a custom export button layout.
        
        Produces layout with buttons for export of relevant sections (plot, table).
        Options for figure are: 
            .png (image format useful for computer generated graphics)
            .svg (scalable vector graphic, image is not pixels but data on where lines are, 
                useful in reports)
        Options for Table are:
            copy (copies the table to clipboard)
            .csv (a comma separated values file of the table, useful for data storage)
            Excel (an excel file, useful for exchanging with people and making visualizations) 
        """
        export_menu = QHBoxLayout()

        # Export Plot
        if has_plot:
            plot_layout = QHBoxLayout()
            self.export_plot = ExportPlot(
                QLabel("Export plot:"),
                QPushButton(".png"),
                QPushButton(".svg"),
            )
            self.export_plot.png.clicked.connect(self.plot.to_png)
            self.export_plot.svg.clicked.connect(self.plot.to_svg)
            for obj in self.export_plot:
                plot_layout.addWidget(obj)
            export_menu.addLayout(plot_layout)

        # Add seperator if both table and plot exist
        if has_table and has_plot:
            export_menu.addWidget(vertical_line())

        # Export Table
        if has_table:
            table_layout = QHBoxLayout()
            self.export_table = ExportTable(
                QLabel("Export table:"),
                QPushButton("Copy"),
                QPushButton(".csv"),
                QPushButton("Excel"),
            )
            self.export_table.copy.clicked.connect(self.table.to_clipboard)
            self.export_table.csv.clicked.connect(self.table.to_csv)
            self.export_table.excel.clicked.connect(self.table.to_excel)
            for obj in self.export_table:
                table_layout.addWidget(obj)
            export_menu.addLayout(table_layout)

        export_menu.addStretch()
        return export_menu


class InventoryTab(NewAnalysisTab):
    """Class for the 'Inventory' sub-tab.

    This tab allows for investigation of the inventories of the calculation.

    Shows:
        Option to choose between 'Biosphere flows' and 'Technosphere flows'
        Inventory table for either 'Biosphere flows' or 'Technosphere flows'
        Export options
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_biosphere = None
        self.df_technosphere = None

        self.layout.addLayout(get_header_layout('Inventory'))

        # buttons
        button_layout = QHBoxLayout()
        self.radio_button_biosphere = QRadioButton("Biosphere flows")
        self.radio_button_biosphere.setChecked(True)
        button_layout.addWidget(self.radio_button_biosphere)
        self.radio_button_technosphere = QRadioButton("Technosphere flows")
        self.scenario_label = QLabel("Scenario:")
        button_layout.addWidget(self.radio_button_technosphere)
        button_layout.addWidget(self.scenario_label)
        button_layout.addWidget(self.scenario_box)
        button_layout.addStretch(1)
        self.layout.addLayout(button_layout)

        # table
        self.table = InventoryTable(self.parent)
        self.table.table_name = 'Inventory_' + self.parent.cs_name
        self.layout.addWidget(self.table)

        self.layout.addLayout(self.build_export(has_plot=False, has_table=True))
        self.connect_signals()

    def connect_signals(self):
        self.radio_button_biosphere.toggled.connect(self.button_clicked)
        if self.using_presamples:
            self.scenario_box.currentIndexChanged.connect(self.parent.update_scenario_data)
            self.parent.update_scenario_box_index.connect(
                lambda index: self.set_combobox_index(self.scenario_box, index)
            )

    @QtCore.Slot(bool, name="isBiosphereToggled")
    def button_clicked(self, toggled: bool):
        """Update table according to radiobutton selected."""
        if not toggled:
            self.update_table(inventory='technosphere')
            self.table.table_name = self.parent.cs_name + '_Inventory_technosphere'
        else:
            self.update_table(inventory='biosphere')
            self.table.table_name = self.parent.cs_name + '_Inventory'

    def configure_scenario(self):
        """Allow scenarios options to be visible when used."""
        super().configure_scenario()
        self.scenario_label.setVisible(self.using_presamples)

    def update_tab(self):
        """Update the tab."""
        self.clear_tables()
        super().update_tab()

    def update_table(self, inventory='biosphere'):
        """Update the table."""
        if inventory == 'biosphere':
            if self.df_biosphere is None:
                self.df_biosphere = self.parent.contributions.inventory_df(
                    inventory_type='biosphere')
            self.table.sync(self.df_biosphere)
        else:
            if self.df_technosphere is None:
                self.df_technosphere = self.parent.contributions.inventory_df(
                    inventory_type='technosphere')
            self.table.sync(self.df_technosphere)

    def clear_tables(self) -> None:
        """Set the biosphere and technosphere to None."""
        self.df_biosphere, self.df_technosphere = None, None


class LCAResultsTab(NewAnalysisTab):
    """Class for the 'LCA Results' sub-tab.

    This tab allows the user to get a basic overview of the results of the calculation setup.

    Shows:
        'Overview' and 'by LCIA method' options for different plots/graphs
        Plots/graphs
        Export buttons
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.lca_scores_widget = LCAScoresTab(parent)
        self.lca_overview_widget = LCIAResultsTab(parent)

        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.addLayout(get_header_layout('LCA Results'))

        # buttons
        button_layout = QHBoxLayout()
        self.button_group = QButtonGroup()
        self.button_overview = QRadioButton("Overview")
        self.button_overview.setToolTip(
            "Show a matrix of all functional units and all impact categories")
        button_layout.addWidget(self.button_overview)
        self.button_by_method = QRadioButton("by LCIA method")
        self.button_by_method.setToolTip(
            "Show the impacts of each functional unit for the selected impact categories")
        self.button_by_method.setChecked(True)
        self.scenario_label = QLabel("Scenario:")
        self.button_group.addButton(self.button_overview, 0)
        self.button_group.addButton(self.button_by_method, 1)
        button_layout.addWidget(self.button_by_method)
        button_layout.addWidget(self.scenario_label)
        button_layout.addWidget(self.scenario_box)
        button_layout.addStretch(1)
        self.layout.addLayout(button_layout)

        self.layout.addWidget(self.lca_scores_widget)
        self.layout.addWidget(self.lca_overview_widget)

        self.button_clicked(False)
        self.connect_signals()

    def connect_signals(self):
        self.button_overview.toggled.connect(self.button_clicked)
        if self.using_presamples:
            self.scenario_box.currentIndexChanged.connect(self.parent.update_scenario_data)
            self.parent.update_scenario_box_index.connect(
                lambda index: self.set_combobox_index(self.scenario_box, index)
            )
            self.button_by_method.toggled.connect(
                lambda on_lcia: self.scenario_box.setHidden(on_lcia)
            )
            self.button_by_method.toggled.connect(
                lambda on_lcia: self.scenario_label.setHidden(on_lcia)
            )

    @QtCore.Slot(bool, name="overviewToggled")
    def button_clicked(self, is_overview: bool):
        self.lca_overview_widget.setVisible(is_overview)
        self.lca_scores_widget.setHidden(is_overview)

    def configure_scenario(self):
        """Allow scenarios options to be visible when used."""
        super().configure_scenario()
        self.scenario_box.setHidden(self.button_by_method.isChecked())
        self.scenario_label.setHidden(self.button_by_method.isChecked())

    def update_tab(self):
        """Update the tab."""
        self.lca_scores_widget.update_tab()
        self.lca_overview_widget.update_plot()
        self.lca_overview_widget.update_table()


class LCAScoresTab(NewAnalysisTab):
    """Class for when 'by LCIA method' is chosen in the 'LCA Results' sub-tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.combobox_menu = QHBoxLayout()
        self.combobox_label = QLabel("Choose LCIA method:")
        self.combobox = QComboBox()
        self.combobox.scroll = False
        self.combobox_menu.addWidget(self.combobox_label)
        self.combobox_menu.addWidget(self.combobox, 1)
        self.combobox_menu.addStretch(1)
        self.layout.addLayout(self.combobox_menu)

        self.plot = LCAResultsBarChart(self.parent)
        self.plot.plot_name = 'LCA scores_' + self.parent.cs_name
        self.layout.addWidget(self.plot)

        self.layout.addLayout(self.build_export(has_plot=True, has_table=False))

        self.connect_signals()

    def connect_signals(self):
        self.combobox.currentIndexChanged.connect(self.update_plot)

    def update_tab(self):
        """Update the tab."""
        self.update_combobox(self.combobox, [str(m) for m in self.parent.mlca.methods])
        super().update_tab()

    @QtCore.Slot(int, name="updatePlotWithIndex")
    def update_plot(self, method_index: int = 0):
        """Update the plot."""
        method = self.parent.mlca.methods[method_index]
        df = self.parent.mlca.get_results_for_method(method_index)
        labels = [
            bc.format_activity_label(next(iter(fu.keys())), style='pnld')
            for fu in self.parent.mlca.func_units
        ]
        idx = self.layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.deleteLater()
        self.plot = LCAResultsBarChart(self.parent)
        self.layout.insertWidget(idx, self.plot)
        self.plot.plot(df, method=method, labels=labels)
        self.updateGeometry()
        self.plot.plot_name = '_'.join([self.parent.cs_name, 'LCA scores', str(method)])


class LCIAResultsTab(NewAnalysisTab):
    """Class for when 'Overview' is chosen in the 'LCA Results' sub-tab."""

    def __init__(self, parent, **kwargs):
        super(LCIAResultsTab, self).__init__(parent, **kwargs)
        self.parent = parent
        self.df = None

        # if not self.parent.single_func_unit:
        self.plot = LCAResultsPlot(self.parent)
        self.plot.plot_name = self.parent.cs_name + '_LCIA results'
        self.table = LCAResultsTable(self.parent)
        self.table.table_name = self.parent.cs_name + '_LCIA results'
        self.relative = False

        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(self.build_export(True, True))

    def update_plot(self):
        """Update the plot."""
        idx = self.pt_layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.deleteLater()
        self.plot = LCAResultsPlot(self.parent)
        self.pt_layout.insertWidget(idx, self.plot)
        self.df = self.parent.contributions.lca_scores_df(normalized=self.relative)
        self.plot.plot(self.df)
        if self.pt_layout.parentWidget():
            self.pt_layout.parentWidget().updateGeometry()

    def update_table(self):
        """Update the table."""
        if not isinstance(self.table, LCAResultsTable):
            self.table = LCAResultsTable()
        self.df = self.parent.contributions.lca_scores_df(normalized=self.relative)
        self.table.sync(self.df)


class ContributionTab(NewAnalysisTab):
    """Parent class for any 'XXX Contributions' sub-tab."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.cutoff_menu = CutoffMenu(self, cutoff_value=0.05)
        self.combobox_menu = Combobox(
            func=QComboBox(self),
            func_label=QLabel("Functional Unit:"),
            method=QComboBox(self),
            method_label=QLabel("Impact Category:"),
            agg=QComboBox(self),
            agg_label=QLabel("Aggregate by:"),
            scenario=self.scenario_box,
            scenario_label=QLabel("Scenario:"),
        )
        self.switch_label = QLabel("Compare:")
        self.switches = SwitchComboBox(self)

        self.relativity = Relativity(
            QRadioButton("Relative"),
            QRadioButton("Absolute"),
        )
        self.relativity.relative.setChecked(True)
        self.relative = True
        self.relativity.relative.setToolTip(
            "Show relative values (compare fraction of each contribution)")
        self.relativity.absolute.setToolTip(
            "Show absolute values (compare magnitudes of each contribution)")

        self.df = None
        self.plot = ContributionPlot()
        self.table = ContributionTable(self)
        self.contribution_fn = None
        self.has_method, self.has_func = False, False
        self.unit = None

    def set_filename(self, optional_fields: dict = None):
        """Given a dictionary of fields, put together a usable filename for the plot and table."""
        optional = optional_fields or {}
        fields = (
            self.parent.cs_name, self.contribution_fn, optional.get("method"),
            optional.get("functional_unit"), self.unit
        )
        filename = '_'.join((str(x) for x in fields if x is not None))
        self.plot.plot_name, self.table.table_name = filename, filename

    def build_combobox(self, has_method: bool = True, has_func: bool = False) -> QHBoxLayout:
        """Construct a horizontal layout for picking and choosing what data to show and how."""
        menu = QHBoxLayout()
        # Populate the drop-down boxes with their relevant values.
        self.combobox_menu.func.addItems(
            list(self.parent.mlca.func_unit_translation_dict.keys())
        )
        self.combobox_menu.method.addItems(list(self.parent.method_dict.keys()))

        menu.addWidget(self.switch_label)
        menu.addWidget(self.switches)
        menu.addWidget(vertical_line())
        menu.addWidget(self.combobox_menu.scenario_label)
        menu.addWidget(self.combobox_menu.scenario)
        menu.addWidget(self.combobox_menu.method_label)
        menu.addWidget(self.combobox_menu.method)
        menu.addWidget(self.combobox_menu.func_label)
        menu.addWidget(self.combobox_menu.func)
        menu.addWidget(self.combobox_menu.agg_label)
        menu.addWidget(self.combobox_menu.agg)
        menu.addStretch()

        self.has_method = has_method
        self.has_func = has_func
        return menu

    def configure_scenario(self):
        """Supplement the superclass method because there are more things to hide in these tabs."""
        super().configure_scenario()
        visible = self.using_presamples
        self.combobox_menu.scenario_label.setVisible(visible)

    @QtCore.Slot(int, name="changeComparisonView")
    def toggle_comparisons(self, index: int):
        self.toggle_func(index == self.switches.indexes.func)
        self.toggle_method(index == self.switches.indexes.method)
        self.toggle_scenario(index == self.switches.indexes.scenario)
        self.update_tab()

    @QtCore.Slot(bool, name="hideScenarioCombo")
    def toggle_scenario(self, active: bool):
        """Allow scenarios options to be visible when used."""
        if self.using_presamples:
            self.combobox_menu.scenario.setHidden(active)
            self.combobox_menu.scenario_label.setHidden(active)

    @QtCore.Slot(bool, name="hideFuCombo")
    def toggle_func(self, active: bool):
        self.combobox_menu.func.setHidden(active)
        self.combobox_menu.func_label.setHidden(active)

    @QtCore.Slot(bool, name="hideMethodCombo")
    def toggle_method(self, active: bool):
        self.combobox_menu.method.setHidden(active)
        self.combobox_menu.method_label.setHidden(active)

    @QtCore.Slot(name="comboboxTriggerUpdate")
    def set_combobox_changes(self):
        """Update fields based on user-made changes in combobox.
        
        Any trigger linked to this slot will cause the values in the
        combobox objects to be read out (which comparison, drop-down indexes,
        etc.) and fed into update calls.
        """
        if self.combobox_menu.agg.currentText() != 'none':
            compare_fields = {"aggregator": self.combobox_menu.agg.currentText()}
        else:
            compare_fields = {"aggregator": None}

        # Determine which comparison is active and update the comparison.
        if self.switches.currentIndex() == self.switches.indexes.func:
            compare_fields.update({
                "method": self.parent.method_dict[self.combobox_menu.method.currentText()],
            })
        elif self.switches.currentIndex() == self.switches.indexes.method:
            compare_fields.update({
                "functional_unit": self.combobox_menu.func.currentText(),
            })
        elif self.switches.currentIndex() == self.switches.indexes.scenario:
            compare_fields.update({
                "method": self.parent.method_dict[self.combobox_menu.method.currentText()],
                "functional_unit": self.combobox_menu.func.currentText(),
            })

        # Determine the unit for the figure, update the filenames and the
        # underlying dataframe.
        self.unit = get_unit(compare_fields.get("method"), self.relative)
        self.set_filename(compare_fields)
        self.df = self.update_dataframe(**compare_fields)

    def connect_signals(self):
        """Override the inherited method to perform the same thing plus aggregation."""
        self.cutoff_menu.slider_change.connect(self.update_tab)
        self.switches.currentIndexChanged.connect(self.toggle_comparisons)
        self.combobox_menu.method.currentIndexChanged.connect(self.update_tab)
        self.combobox_menu.func.currentIndexChanged.connect(self.update_tab)
        self.combobox_menu.agg.currentIndexChanged.connect(self.update_tab)

        # Add wiring for presamples scenarios
        if self.using_presamples:
            self.scenario_box.currentIndexChanged.connect(self.parent.update_scenario_data)
            self.parent.update_scenario_box_index.connect(
                lambda index: self.set_combobox_index(self.scenario_box, index)
            )

    def update_tab(self):
        """Update the tab."""
        self.set_combobox_changes()
        super().update_tab()

    def update_dataframe(self, *args, **kwargs):
        """Update the underlying dataframe. 
        
        Implement in subclass."""
        raise NotImplementedError

    def update_plot(self):
        """Update the plot."""
        idx = self.pt_layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.deleteLater()
        self.plot = ContributionPlot()
        self.pt_layout.insertWidget(idx, self.plot)
        self.plot.plot(self.df, unit=self.unit)
        if self.pt_layout.parentWidget():
            self.pt_layout.parentWidget().updateGeometry()


class ElementaryFlowContributionTab(ContributionTab):
    """Class for the 'Elementary flow Contributions' sub-tab.

    This tab allows for analysis of elementary flows.

    Example questions that can be answered by this tab:
        What is the CO2 production caused by functional unit XXX?
        Which impact is largest on the impact category YYY?
        What are the 5 largest elementary flows caused by functional unit ZZZ?

    Shows:
        Cutoff menu for determining cutoff values
        Compare options button to change between 'Functional Units' and 'Impact Categories'
        'Impact Category'/'Functional Unit' chooser with aggregation method
        Plot/Table on/off and Relative/Absolute options for data
        Plot/Table
        Export options
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout.addLayout(get_header_layout('Elementary Flow Contributions'))
        self.layout.addWidget(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())
        combobox = self.build_combobox(has_method=True, has_func=True)
        self.layout.addLayout(combobox)
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(self.build_export(True, True))

        self.contribution_fn = 'EF contributions'
        self.switches.configure(self.has_func, self.has_method)
        self.connect_signals()
        self.toggle_comparisons(self.switches.indexes.func)

    def build_combobox(self, has_method: bool = True,
                       has_func: bool = False) -> QHBoxLayout:
        self.combobox_menu.agg.addItems(self.parent.contributions.DEFAULT_EF_AGGREGATES)
        return super().build_combobox(has_method, has_func)

    def update_dataframe(self, *args, **kwargs):
        """Retrieve the top elementary flow contributions."""
        return self.parent.contributions.top_elementary_flow_contributions(
            **kwargs, limit=self.cutoff_menu.cutoff_value,
            limit_type=self.cutoff_menu.limit_type, normalize=self.relative
        )


class ProcessContributionsTab(ContributionTab):
    """Class for the 'Process Contributions' sub-tab.

    This tab allows for analysis of process contributions.

    Example questions that can be answered by this tab:
        What is the contribution of electricity production to functional unit XXX?
        Which process contributes the most to impact category YYY?
        What are the top 5 contributing processes to functional unit ZZZ?

    Shows:
        Cutoff menu for determining cutoff values
        Compare options button to change between 'Functional Units' and 'Impact Categories'
        'Impact Category'/'Functional Unit' chooser with aggregation method
        Plot/Table on/off and Relative/Absolute options for data
        Plot/Table
        Export options
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.layout.addLayout(get_header_layout('Process Contributions'))
        self.layout.addWidget(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())
        combobox = self.build_combobox(has_method=True, has_func=True)
        self.layout.addLayout(combobox)
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(self.build_export(True, True))

        self.contribution_fn = 'Process contributions'
        self.switches.configure(self.has_func, self.has_method)
        self.connect_signals()
        self.toggle_comparisons(self.switches.indexes.func)

    def build_combobox(self, has_method: bool = True,
                       has_func: bool = False) -> QHBoxLayout:
        self.combobox_menu.agg.addItems(self.parent.contributions.DEFAULT_ACT_AGGREGATES)
        return super().build_combobox(has_method, has_func)

    def update_dataframe(self, *args, **kwargs):
        """Retrieve the top process contributions"""
        return self.parent.contributions.top_process_contributions(
            **kwargs, limit=self.cutoff_menu.cutoff_value,
            limit_type=self.cutoff_menu.limit_type, normalize=self.relative
        )


class CorrelationsTab(NewAnalysisTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.tab_text = "Correlations"
        self.layout.addLayout(get_header_layout('Correlation Analysis'))

        if not self.parent.single_func_unit:
            self.plot = CorrelationPlot(self.parent)

        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(self.build_export(
            has_table=False, has_plot=not self.parent.single_func_unit
        ))

    def update_plot(self):
        """Update the plot."""
        idx = self.pt_layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.deleteLater()
        self.plot = CorrelationPlot(self.parent)
        self.pt_layout.insertWidget(idx, self.plot)
        df = self.parent.mlca.get_normalized_scores_df()
        self.plot.plot(df)
        if self.pt_layout.parentWidget():
            self.pt_layout.parentWidget().updateGeometry()


class SankeyTab(QWidget):
    def __init__(self, parent):
        super(SankeyTab, self).__init__(parent)
        self.parent = parent


class MonteCarloTab(NewAnalysisTab):
    def __init__(self, parent=None):
        super(MonteCarloTab, self).__init__(parent)
        self.parent: LCAResultsSubTab = parent

        self.layout.addLayout(get_header_layout('Monte Carlo Simulation'))
        self.scenario_label = QLabel("Scenario:")
        self.include_box = QGroupBox("Include uncertainty for:", self)
        grid = QGridLayout()
        self.include_tech = QCheckBox("Technosphere", self)
        self.include_tech.setChecked(True)
        self.include_bio = QCheckBox("Biosphere", self)
        self.include_bio.setChecked(True)
        self.include_cf = QCheckBox("Characterization Factors", self)
        self.include_cf.setChecked(True)
        self.include_parameters = QCheckBox("Parameters", self)
        self.include_parameters.setChecked(True)
        grid.addWidget(self.include_tech, 0, 0)
        grid.addWidget(self.include_bio, 0, 1)
        grid.addWidget(self.include_cf, 1, 0)
        grid.addWidget(self.include_parameters, 1, 1)
        self.include_box.setLayout(grid)

        self.add_MC_ui_elements()

        self.table = LCAResultsTable()
        self.table.table_name = 'MonteCarlo_' + self.parent.cs_name
        self.plot = MonteCarloPlot(self.parent)
        self.plot.hide()
        self.plot.plot_name = 'MonteCarlo_' + self.parent.cs_name
        self.layout.addWidget(self.plot)
        self.export_widget = self.build_export(has_plot=True, has_table=True)
        self.layout.addWidget(self.export_widget)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.connect_signals()

    def connect_signals(self):
        self.button_run.clicked.connect(self.calculate_mc_lca)
        # signals.monte_carlo_ready.connect(self.update_mc)
        # self.combobox_fu.currentIndexChanged.connect(self.update_plot)
        self.combobox_methods.currentIndexChanged.connect(
            # ignore the index and send the cs_name instead
            lambda x: self.update_mc(cs_name=self.parent.cs_name)
        )

        # signals
        # self.radio_button_biosphere.clicked.connect(self.button_clicked)
        # self.radio_button_technosphere.clicked.connect(self.button_clicked)

        if self.using_presamples:
            self.scenario_box.currentIndexChanged.connect(self.parent.update_scenario_data)
            self.parent.update_scenario_box_index.connect(
                lambda index: self.set_combobox_index(self.scenario_box, index)
            )

    def add_MC_ui_elements(self):
        layout_mc = QVBoxLayout()

        # H-LAYOUT start simulation
        self.button_run = QPushButton('Run Simulation')
        self.label_iterations = QLabel('Iterations:')
        self.iterations = QLineEdit('10')
        self.iterations.setFixedWidth(40)
        self.iterations.setValidator(QtGui.QIntValidator(1, 1000))
        self.label_seed = QLabel('Random seed:')
        self.label_seed.setToolTip('Seed value (integer) for the random number generator. '
                                   'Use this for reproducible samples.')
        self.seed = QLineEdit('')
        self.seed.setFixedWidth(30)



        self.hlayout_run = QHBoxLayout()
        self.hlayout_run.addWidget(self.scenario_label)
        self.hlayout_run.addWidget(self.scenario_box)
        self.hlayout_run.addWidget(self.button_run)
        self.hlayout_run.addWidget(self.label_iterations)
        self.hlayout_run.addWidget(self.iterations)
        self.hlayout_run.addWidget(self.label_seed)
        self.hlayout_run.addWidget(self.seed)
        self.hlayout_run.addWidget(self.include_box)
        self.hlayout_run.addStretch(1)
        layout_mc.addLayout(self.hlayout_run)

        # self.label_running = QLabel('Running a Monte Carlo simulation. Please allow some time for this. '
        #                             'Please do not run another simulation at the same time.')
        # self.layout_mc.addWidget(self.label_running)
        # self.label_running.hide()

        # # buttons for all FUs or for all methods
        # self.radio_button_all_fu = QRadioButton("For all functional units")
        # self.radio_button_all_methods = QRadioButton("Technosphere flows")
        #
        # self.radio_button_biosphere.setChecked(True)
        # self.radio_button_technosphere.setChecked(False)
        #
        # self.label_for_all_fu = QLabel('For all functional units')
        # self.combobox_fu = QRadioButton()
        # self.hlayout_fu = QHBoxLayout()

        # FU selection
        # self.label_fu = QLabel('Choose functional unit')
        # self.combobox_fu = QComboBox()
        # self.hlayout_fu = QHBoxLayout()
        #
        # self.hlayout_fu.addWidget(self.label_fu)
        # self.hlayout_fu.addWidget(self.combobox_fu)
        # self.hlayout_fu.addStretch()
        # self.layout_mc.addLayout(self.hlayout_fu)

        # method selection
        self.method_selection_widget = QWidget()
        self.label_methods = QLabel('Choose LCIA method')
        self.combobox_methods = QComboBox()
        self.hlayout_methods = QHBoxLayout()

        self.hlayout_methods.addWidget(self.label_methods)
        self.hlayout_methods.addWidget(self.combobox_methods)
        self.hlayout_methods.addStretch()
        self.method_selection_widget.setLayout(self.hlayout_methods)

        layout_mc.addWidget(self.method_selection_widget)
        self.method_selection_widget.hide()

        self.layout.addLayout(layout_mc)

    def build_export(self, has_table: bool = True, has_plot: bool = True) -> QWidget:
        """Construct the export layout but set it into a widget because we
         want to hide it."""
        export_layout = super().build_export(has_table, has_plot)
        export_widget = QWidget()
        export_widget.setLayout(export_layout)
        # Hide widget until MC is calculated
        export_widget.hide()
        return export_widget

    @QtCore.Slot(name="calculateMcLca")
    def calculate_mc_lca(self):
        self.method_selection_widget.hide()
        self.plot.hide()
        self.export_widget.hide()

        iterations = int(self.iterations.text())
        seed = None
        if self.seed.text():
            print('SEED: ', self.seed.text())
            try:
                seed = int(self.seed.text())
            except ValueError:
                traceback.print_exc()
                QMessageBox.warning(self, 'Warning', 'Seed value must be an integer number or left empty.')
                self.seed.setText('')
                return
        includes = {
            "technosphere": self.include_tech.isChecked(),
            "biosphere": self.include_bio.isChecked(),
            "cf": self.include_cf.isChecked(),
            "parameters": self.include_parameters.isChecked(),
        }

        try:
            self.parent.mc.calculate(iterations=iterations, seed=seed, **includes)
            self.update_mc()
        except InvalidParamsError as e:  # This can occur if uncertainty data is missing or otherwise broken
            # print(e)
            traceback.print_exc()
            QMessageBox.warning(self, 'Could not perform Monte Carlo simulation', str(e))

        # a threaded way for this - unfortunatley this crashes as:
        # pypardsio_solver is used for the 'spsolve' and 'factorized' functions. Python crashes on windows if multiple
        # instances of PyPardisoSolver make calls to the Pardiso library
        # worker_thread = WorkerThread()
        # print('Created local worker_thread')
        # worker_thread.set_mc(self.parent.mc, iterations=iterations)
        # print('Passed object to thread.')
        # worker_thread.start()
        # self.label_running.show()

        #

        # thread = NewCSMCThread() #self.parent.mc
        # thread.calculation_finished.connect(
        #     lambda x: print('Calculation finished.'))
        # thread.start()

        # # give us a thread and start it
        # thread = QtCore.QThread()
        # thread.start()
        #
        # # create a worker and move it to our extra thread
        # worker = Worker()
        # worker.moveToThread(thread)

        # self.parent.mct.start()
        # self.parent.mct.run(iterations=iterations)
        # self.parent.mct.finished()

        # objThread = QtCore.QThread()
        # obj = QObjectMC()  # self.parent.cs_name
        # obj.moveToThread(objThread)
        # obj.finished.connect(objThread.quit)
        # objThread.started.connect(obj.long_running)
        # # objThread.finished.connect(app.exit)
        # objThread.finished.connect(
        #     lambda x: print('Finished Thread!')
        # )
        # objThread.start()

        # objThread = QtCore.QThread()
        # obj = SomeObject()
        # obj.moveToThread(objThread)
        # obj.finished.connect(objThread.quit)
        # objThread.started.connect(obj.long_running)
        # objThread.finished.connect(
        #     lambda x: print('Finished Thread!')
        # )
        # objThread.start()

        # self.method_selection_widget.show()
        # self.plot.show()
        # self.export_widget.show()

    def configure_scenario(self):
        super().configure_scenario()
        self.scenario_label.setVisible(self.using_presamples)

    def update_tab(self):
        self.update_combobox(self.combobox_methods, [str(m) for m in self.parent.mc.methods])
        # self.update_combobox(self.combobox_methods, [str(m) for m in self.parent.mct.mc.methods])

    def update_mc(self, cs_name=None):
        # act = self.combobox_fu.currentText()
        # activity_index = self.combobox_fu.currentIndex()
        # act_key = self.parent.mc.activity_keys[activity_index]
        # if cs_name != self.parent.cs_name:  # relevant if several CS are open at the same time
        #     return

        # self.label_running.hide()
        self.method_selection_widget.show()
        self.export_widget.show()

        method_index = self.combobox_methods.currentIndex()
        method = self.parent.mc.methods[method_index]

        # data = self.parent.mc.get_results_by(act_key=act_key, method=method)
        self.df = self.parent.mc.get_results_dataframe(method=method)

        self.update_table()
        self.update_plot(method=method)
        filename = '_'.join([str(x) for x in [self.parent.cs_name, 'Monte Carlo results', str(method)]])
        self.plot.plot_name, self.table.table_name = filename, filename

    def update_plot(self, method):
        idx = self.layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.deleteLater()
        self.plot = MonteCarloPlot(self.parent)
        self.layout.insertWidget(idx, self.plot)
        self.plot.plot(self.df, method=method)
        self.plot.show()
        if self.layout.parentWidget():
            self.layout.parentWidget().updateGeometry()

    def update_table(self):
        self.table.sync(self.df)


class MonteCarloWorkerThread(QtCore.QThread):
    """A worker for Monte Carlo simulations.

    Unfortunately, pyparadiso does not allow parallel calculations on Windows (crashes).
    So this is for future reference in case this issue is solved... """
    def set_mc(self, mc, iterations=10):
        self.mc = mc
        self.iterations = iterations

    def run(self):
        print('Starting new Worker Thread. Iterations:', self.iterations)
        self.mc.calculate(iterations=self.iterations)
        # res = bw.GraphTraversal().calculate(self.demand, self.method, self.cutoff, self.max_calc)
        print('in thread {}'.format(QtCore.QThread.currentThread()))
        signals.monte_carlo_ready.emit(self.mc.cs_name)

worker_thread = MonteCarloWorkerThread()

# class Worker(QtCore.QObject):
#
#     def __init__(self):
#         super().__init__()
#
#     def do_something(self, text):
#         print('in thread {} message {}'.format(QtCore.QThread.currentThread(), text))
#
#
# class SomeObject(QtCore.QObject):
#
#     finished = QtCore.pyqtSignal()
#
#     def long_running(self):
#         count = 0
#         while count < 5:
#             time.sleep(1)
#             print("B Increasing")
#             count += 1
#         self.finished.emit()
