from collections import namedtuple
from copy import deepcopy
from typing import List, Optional
from logging import getLogger
from datetime import datetime

import numpy as np
import pandas as pd
import bw2data as bd
from qtpy import QtCore, QtGui, QtWidgets

from stats_arrays.errors import InvalidParamsError

from activity_browser import signals, bwutils, settings
from activity_browser.mod.bw2analyzer import ABContributionAnalysis
from activity_browser.ui import icons, web, widgets

from .style import header, horizontal_line, vertical_line
from .tables import ContributionTable, InventoryTable, LCAResultsTable
from .plots import ContributionPlot, CorrelationPlot, LCAResultsBarChart, LCAResultsPlot, MonteCarloPlot

ca = ABContributionAnalysis()

log = getLogger(__name__)


def get_header_layout(header_text: str) -> QtWidgets.QVBoxLayout:
    vlayout = QtWidgets.QVBoxLayout()
    vlayout.addWidget(header(header_text))
    vlayout.addWidget(horizontal_line())
    return vlayout


def get_header_layout_w_help(header_text: str, help_widget) -> QtWidgets.QVBoxLayout:
    hlayout = QtWidgets.QHBoxLayout()
    hlayout.addWidget(header(header_text))
    hlayout.addWidget(help_widget)
    hlayout.setStretch(0, 1)

    vlayout = QtWidgets.QVBoxLayout()
    vlayout.addLayout(hlayout)
    vlayout.addWidget(horizontal_line())
    return vlayout


def get_unit(method: tuple, relative: bool = False) -> str:
    """Get the unit for plot axis naming.

    Determine the unit based on whether a plot is shown:
    - for a number of reference flows
    - for a number of impact categories
    and whether the axis are related to:
    - relative or
    - absolute numbers.
    """
    if relative:
        return "relative share"
    if method:  # for all reference flows
        return bwutils.commontasks.unit_of_method(method)
    return "units of each impact category"


# Special namedtuple for the LCAResults TabWidget.
Tabs = namedtuple(
    "tabs", ("inventory", "results", "ef", "process", "sankey", "tree", "mc", "gsa")
)
Relativity = namedtuple("relativity", ("relative", "absolute"))
TotalMenu = namedtuple("total_menu", ("score", "range"))
ExportTable = namedtuple("export_table", ("label", "copy", "csv", "excel"))
ExportPlot = namedtuple("export_plot", ("label", "png", "svg"))
PlotTableCheck = namedtuple("plot_table_space", ("plot", "table", "invert"))
Combobox = namedtuple(
    "combobox_menu",
    (
        "func",
        "func_label",
        "method",
        "method_label",
        "agg",
        "agg_label",
        "scenario",
        "scenario_label",
    ),
)


class LCAResultsPage(QtWidgets.QTabWidget):
    """Class for the main 'LCA Results' tab.

    Shows:
        One sub-tab for each calculation setup
        For each calculation setup-tab one array of relevant tabs.
    """

    update_scenario_box_index: QtCore.SignalInstance = QtCore.Signal(int)

    def __init__(self, cs_name, mlca, contributions, mc, parent=None):
        super().__init__(parent)
        self.setObjectName(f"{cs_name}-{datetime.now().strftime('%H:%M:%S')}")
        self.setWindowTitle(f"{cs_name} [{datetime.now().strftime('%H:%M')}]")

        self.cs_name, self.mlca, self.contributions, self.mc = cs_name, mlca, contributions, mc
        self.cs = bd.calculation_setups[self.cs_name]
        self.has_scenarios: bool = hasattr(mlca, "scenario_names")
        self.method_dict = bwutils.commontasks.get_LCIA_method_name_dict(self.mlca.methods)
        self.single_func_unit = len(self.mlca.func_units) == 1
        self.single_method = len(self.mlca.methods) == 1

        self.setMovable(True)
        self.setVisible(False)
        self.visible = False

        self.tabs = Tabs(
            inventory=InventoryTab(self),
            results=LCAResultsTab(self),
            ef=ElementaryFlowContributionTab(self),
            process=ProcessContributionsTab(self),
            # ft=FirstTierContributionsTab(self.cs_name, parent=self),
            sankey=web.SankeyNavigatorWidget(self.cs_name, parent=self),
            tree=web.TreeNavigatorWidget(self.cs_name, parent=self),
            mc=MonteCarloTab(
                self
            ),  # mc=None if self.mc is None else MonteCarloTab(self),
            gsa=GSATab(self),
        )
        self.tab_names = Tabs(
            inventory="Inventory",
            results="LCA Results",
            ef="EF Contributions",
            process="Process Contributions",
            # ft="FT Contributions",
            sankey="Sankey",
            tree="Tree",
            mc="Monte Carlo",
            gsa="Sensitivity Analysis",
        )
        self.setup_tabs()
        self.setCurrentWidget(self.tabs.results)
        self.currentChanged.connect(self.generate_content_on_click)

    def setup_tabs(self):
        """Have all the tabs pull in their required data and add them."""
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
        """Will calculate which scenario array to use and update all child tabs."""
        if index == self.mlca.current:
            return
        self.mlca.set_scenario(index)
        self._update_tabs()
        self.update_scenario_box_index.emit(index)

    @QtCore.Slot(int, name="generateSankeyOnClick")
    def generate_content_on_click(self, index):
        if index == self.indexOf(self.tabs.sankey):
            if not self.tabs.sankey.has_sankey:
                log.info("Generating Sankey Tab")
                self.tabs.sankey.new_sankey()
        # elif index == self.indexOf(self.tabs.ft):
        #     if not self.tabs.ft.has_been_opened:
        #         log.info("Generating First Tier results")
        #         self.tabs.ft.has_been_opened = True
        #         self.tabs.ft.update_tab()

        if index == self.indexOf(self.tabs.tree):
            if not self.tabs.tree.has_rendered_once:
                log.info("Generating Tree Tab")
                self.tabs.tree.new_tree()

    @QtCore.Slot(name="lciaScenarioExport")
    def generate_lcia_scenario_csv(self):
        """Create a dataframe of the impact category results for all reference flows,
        impact categories and scenarios, then call the 'export to csv'
        """
        df = self.mlca.lca_scores_to_dataframe()
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Choose location to save lca results",
            filter="Comma Separated Values (*.csv);; All Files (*.*)",
        )
        if filepath:
            if not filepath.endswith(".csv"):
                filepath += ".csv"
            df.to_csv(filepath)

    @QtCore.Slot(name="lciaScenarioExport")
    def generate_lcia_scenario_excel(self):
        """Create a dataframe of the impact category results for all reference flows,
        impact categories and scenarios, then call the 'export to excel'
        """
        df = self.mlca.lca_scores_to_dataframe()
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Choose location to save lca results",
            filter="Excel (*.xlsx);; All Files (*.*)",
        )
        if filepath:
            if not filepath.endswith(".xlsx"):
                filepath += ".xlsx"
            df.to_excel(filepath)


class NewAnalysisTab(QtWidgets.QWidget):
    """Parent class around which all sub-tabs are built."""
    explain_text = "I explain what happens here"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.help_button: Optional[QtWidgets.QToolBar] = None

        self.parent = parent
        self.has_scenarios = self.parent.has_scenarios

        # Important variables optionally used in subclasses
        self.table: Optional[QtWidgets.QTableView] = None
        self.plot: Optional[QtWidgets.QWidget] = None
        self.plot_table: Optional[PlotTableCheck] = None
        self.relativity: Optional[Relativity] = None
        self.relative: Optional[bool] = None
        self.total_menu: Optional[TotalMenu] = None
        self.total_range: Optional[bool] = None
        self.score_marker: Optional[bool] = None
        self.export_plot: Optional[ExportPlot] = None
        self.export_table: Optional[ExportTable] = None

        self.scenario_box = SmallComboBox()
        self.pt_layout = QtWidgets.QVBoxLayout()
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

    def build_main_space(self, invertable: bool = False) -> QtWidgets.QScrollArea:
        """Assemble main space where plots, tables and relevant options are shown."""
        space = QtWidgets.QScrollArea()
        widget = QtWidgets.QWidget()
        self.pt_layout.setAlignment(QtCore.Qt.AlignTop)
        widget.setLayout(self.pt_layout)
        space.setWidget(widget)
        space.setWidgetResizable(True)

        # Option switches
        self.plot_table = PlotTableCheck(QtWidgets.QCheckBox("Plot"), QtWidgets.QCheckBox("Table"), None)
        if invertable:
            self.plot_table = PlotTableCheck(
                QtWidgets.QCheckBox("Plot"), QtWidgets.QCheckBox("Table"), QtWidgets.QCheckBox("Invert")
            )
            self.plot_table.invert.setChecked(False)
            self.plot_table.invert.stateChanged.connect(self.invert_plot)
        self.plot_table.plot.setChecked(True)
        self.plot_table.table.setChecked(True)
        self.plot_table.table.stateChanged.connect(self.space_check)
        self.plot_table.plot.stateChanged.connect(self.space_check)

        # Assemble option row
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.plot_table.plot)
        row.addWidget(self.plot_table.table)
        row.addWidget(vertical_line())
        if invertable:
            row.addWidget(self.plot_table.invert)
        if self.relativity:
            row.addWidget(self.relativity.relative)
            row.addWidget(self.relativity.absolute)
            self.relativity.relative.toggled.connect(self.relativity_check)
        if self.total_menu:
            row.addWidget(vertical_line())
            row.addWidget(self.total_menu.score)
            row.addWidget(self.total_menu.range)
            self.total_menu.range.toggled.connect(self.total_check)
        if hasattr(self, "score_mrk_checkbox"):
            row.addStretch()
            row.addWidget(self.score_mrk_checkbox)
            self.score_mrk_checkbox.toggled.connect(self.score_mrk_check)
        if not hasattr(self, "score_mrk_checkbox"):
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

    @QtCore.Slot(name="invertPlot")
    def invert_plot(self):
        self.plot_inversion = self.plot_table.invert.isChecked()
        self.space_check()
        self.update_plot()

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

    @QtCore.Slot(bool, name="isTotalToggled")
    def total_check(self, checked: bool):
        """Check if the relative or absolute option is selected."""
        self.total_range = checked
        self.update_tab()

    @QtCore.Slot(bool, name="isScoreMarkerToggled")
    def score_mrk_check(self, checked: bool):
        self.score_marker = checked

        settings.project_settings.settings["analysis_tab"] = settings.project_settings.settings.get("analysis_tab", {})
        settings.project_settings.settings["analysis_tab"][f"{self.__class__.__name__}score_marker_enabled"] = checked
        settings.project_settings.write_settings()

        self.update_tab()

    def get_scenario_labels(self) -> List[str]:
        """Get scenario labels if scenarios are used."""
        return self.parent.mlca.scenario_names if self.has_scenarios else []

    def configure_scenario(self):
        """Determine if scenario Qt widgets are visible or not and retrieve
        scenario labels for the selection drop-down box.
        """
        if self.scenario_box:
            self.scenario_box.setVisible(self.has_scenarios)
            self.update_combobox(self.scenario_box, self.get_scenario_labels())

    @staticmethod
    @QtCore.Slot(int, name="setBoxIndex")
    def set_combobox_index(box: QtWidgets.QComboBox, index: int) -> None:
        """Update the index on the given QComboBox without sending a signal."""
        box.blockSignals(True)
        box.setCurrentIndex(index)
        box.blockSignals(False)

    @staticmethod
    def update_combobox(box: QtWidgets.QComboBox, labels: List[str]) -> None:
        """Update the combobox menu."""
        box.blockSignals(True)
        box.clear()
        box.insertItems(0, labels)
        box.blockSignals(False)

    def update_tab(self):
        """Update the plot and table if they are present."""
        if self.plot and self.plot.isVisible:
            self.update_plot()
        if self.table and self.table.isVisible:
            self.update_table()
        if self.plot and self.plot.isVisible and self.table and self.table.isVisible:
            self.space_check()

    def update_table(self, *args, **kwargs):
        """Update the table."""
        self.table.model.sync(*args, **kwargs)

    def update_plot(self, *args, **kwargs):
        """Update the plot."""
        self.plot.plot(*args, **kwargs)
        self.export_plot.png.clicked.connect(self.plot.to_png)
        self.export_plot.svg.clicked.connect(self.plot.to_svg)

    def build_export(
        self, has_table: bool = True, has_plot: bool = True
    ) -> QtWidgets.QHBoxLayout:
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
        export_menu = QtWidgets.QHBoxLayout()

        # Export Plot
        if has_plot:
            plot_layout = QtWidgets.QHBoxLayout()
            self.export_plot = ExportPlot(
                QtWidgets.QLabel("Export plot:"),
                QtWidgets.QPushButton(".png"),
                QtWidgets.QPushButton(".svg"),
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
            table_layout = QtWidgets.QHBoxLayout()
            self.export_table = ExportTable(
                QtWidgets.QLabel("Export table:"),
                QtWidgets.QPushButton("Copy"),
                QtWidgets.QPushButton(".csv"),
                QtWidgets.QPushButton("Excel"),
            )
            self.export_table.copy.clicked.connect(self.table.to_clipboard)
            self.export_table.csv.clicked.connect(self.table.to_csv)
            self.export_table.excel.clicked.connect(self.table.to_excel)
            for obj in self.export_table:
                table_layout.addWidget(obj)
            export_menu.addLayout(table_layout)

        export_menu.addStretch()
        return export_menu

    def explanation(self):
        """Builds and shows a message box containing whatever text is set
        on self.explain_text
        """
        return QtWidgets.QMessageBox.question(
            self, "Explanation", self.explain_text, QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Ok
        )


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

        self.layout.addLayout(get_header_layout("Inventory"))
        self.bio_tech_button_group = QtWidgets.QButtonGroup()
        self.bio_categorisation_factor_group = QtWidgets.QComboBox()
        # buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.radio_button_biosphere = QtWidgets.QRadioButton("Biosphere flows")
        self.radio_button_biosphere.setChecked(True)

        self.radio_button_technosphere = QtWidgets.QRadioButton("Technosphere flows")
        self.remove_zeros_checkbox = QtWidgets.QCheckBox("Remove '0' values")
        self.remove_zero_state = False

        self.categorisation_factor_filters = [
            "No filtering with categorisation factors",
            "Flows without categorisation factors",
            "Flows with categorisation factors",
        ]
        self.categorisation_factor_state = None
        self.old_categorisation_factor_state = self.categorisation_factor_state

        self.last_remove_zero_state = self.remove_zero_state
        self.remove_zeros_checkbox.setChecked(self.remove_zero_state)
        self.remove_zeros_checkbox.setToolTip(
            "Choose whether to show '0' values or not.\n"
            "When selected, '0' values are not shown.\n"
            "Rows are only removed when all reference flows are '0'."
        )
        self.scenario_label = QtWidgets.QLabel("Scenario:")

        # Group the radio buttons into the appropriate groups for the window
        self.update_combobox(
            self.bio_categorisation_factor_group, self.categorisation_factor_filters
        )
        self.bio_categorisation_factor_group.setMaximumWidth(300)
        self.bio_categorisation_factor_group.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContentsOnFirstShow
        )

        # Setup the Qt environment for the buttons, including the arrangement
        self.categorisation_filter_layout = QtWidgets.QVBoxLayout()
        self.categorisation_filter_layout.addWidget(QtWidgets.QLabel("Filter flows:"))
        self.categorisation_filter_layout.addWidget(
            self.bio_categorisation_factor_group
        )
        self.categorisation_filter_box = QtWidgets.QWidget()
        self.categorisation_filter_box.setLayout(self.categorisation_filter_layout)
        self.categorisation_filter_box.setVisible(True)
        self.categorisation_filter_with_flows = None

        button_layout.addWidget(self.radio_button_biosphere)
        button_layout.addWidget(self.radio_button_technosphere)
        button_layout.addWidget(self.scenario_label)
        button_layout.addWidget(self.scenario_box)
        button_layout.addStretch(1)
        button_layout.addWidget(self.remove_zeros_checkbox)
        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.categorisation_filter_box)
        # table
        self.table = InventoryTable(self.parent)
        self.table.table_name = "Inventory_" + self.parent.cs_name
        self.layout.addWidget(self.table)

        self.layout.addLayout(self.build_export(has_plot=False, has_table=True))
        self.connect_signals()

    def connect_signals(self):
        self.radio_button_biosphere.toggled.connect(self.button_clicked)
        self.remove_zeros_checkbox.toggled.connect(self.remove_zeros_checked)
        self.bio_tech_button_group.buttonClicked.connect(
            self.toggle_categorisation_factor_filter_buttons
        )
        self.bio_categorisation_factor_group.activated.connect(
            self.add_categorisation_factor_filter
        )
        if self.has_scenarios:
            self.scenario_box.currentIndexChanged.connect(
                self.parent.update_scenario_data
            )
            self.parent.update_scenario_box_index.connect(
                lambda index: self.set_combobox_index(self.scenario_box, index)
            )

    @QtCore.Slot(QtWidgets.QRadioButton, name="addCategorisationFactorFilter")
    def add_categorisation_factor_filter(self, index: int):
        if (
            self.bio_categorisation_factor_group.currentText()
            == "Flows without categorisation factors"
        ):
            self.categorisation_filter_with_flows = False
            self.categorisation_factor_state = False
        elif (
            self.bio_categorisation_factor_group.currentText()
            == "Flows with categorisation factors"
        ):
            self.categorisation_filter_with_flows = True
            self.categorisation_factor_state = True
        else:
            self.categorisation_filter_with_flows = None
            self.categorisation_factor_state = None
        self.update_table()
        self.old_categorisation_factor_state = self.categorisation_factor_state

    @QtCore.Slot(QtWidgets.QRadioButton, name="toggleCategorisationFactorFilterButtons")
    def toggle_categorisation_factor_filter_buttons(self, bttn: QtWidgets.QRadioButton):
        if bttn.text() == "Biosphere flows":
            self.categorisation_filter_box.setVisible(True)
        else:
            self.categorisation_filter_box.setVisible(False)
            self.categorisation_factor_state = None

    @QtCore.Slot(bool, name="isRemoveZerosToggled")
    def remove_zeros_checked(self, toggled: bool):
        """Update table according to remove-zero selected."""
        self.remove_zero_state = toggled
        self.update_table()
        self.last_remove_zero_state = self.remove_zero_state

    @QtCore.Slot(bool, name="isBiosphereToggled")
    def button_clicked(self, toggled: bool):
        """Update table according to radiobutton selected."""
        ext = "_Inventory" if toggled else "_Inventory_technosphere"
        self.table.table_name = "{}{}".format(self.parent.cs_name, ext)
        self.update_table()

    def configure_scenario(self):
        """Allow scenarios options to be visible when used."""
        super().configure_scenario()
        self.scenario_label.setVisible(self.has_scenarios)

    def update_tab(self):
        """Update the tab."""
        self.clear_tables()
        super().update_tab()

    def elementary_flows_contributing_to_IA_methods(
        self, contributary: bool = True, bios: pd.DataFrame = None
    ) -> pd.DataFrame:
        """Returns a biosphere dataframe filtered for the presence in the impact assessment methods
        Requires a boolean argument for whether those flows included in the impact assessment method
        should be returned (True), or not (False)
        """
        incl_flows = {
            self.parent.contributions.inventory_data["biosphere"][1][k]
            for mthd in self.parent.mlca.method_matrices
            for k in mthd.indices
        }
        data = bios if bios is not None else self.df_biosphere
        if contributary:
            flows = incl_flows
        else:
            flows = (
                set(self.parent.contributions.inventory_data["biosphere"][1].values())
            ).difference(incl_flows)
        return data.loc[data["id"].isin(flows)]

    def update_table(self):
        """Update the table."""
        inventory = (
            "biosphere" if self.radio_button_biosphere.isChecked() else "technosphere"
        )
        self.table.showing = inventory
        # We handle both 'df_biosphere' and 'df_technosphere' variables here.
        attr_name = "df_{}".format(inventory)
        if (
            getattr(self, attr_name) is None
            or self.remove_zero_state != self.last_remove_zero_state
            or self.old_categorisation_factor_state != self.categorisation_factor_state
        ):
            setattr(
                self,
                attr_name,
                self.parent.contributions.inventory_df(inventory_type=inventory),
            )

        # filter the biosphere flows for the relevance to the CFs
        if (
            self.categorisation_filter_with_flows is not None
            and inventory == "biosphere"
        ):
            self.df_biosphere = self.elementary_flows_contributing_to_IA_methods(
                self.categorisation_filter_with_flows, self.df_biosphere
            )

        # filter the flows to remove those that have relevant exchanges
        def filter_zeroes(df):
            filter_on = [x for x in df.columns.tolist() if "|" in x]
            return df[df[filter_on].sum(axis=1) != 0].reset_index(drop=True)

        if self.remove_zero_state and getattr(self, "df_biosphere") is not None:
            self.df_biosphere = filter_zeroes(self.df_biosphere)
        if self.remove_zero_state and getattr(self, "df_technosphere") is not None:
            self.df_technosphere = filter_zeroes(self.df_technosphere)

        self._update_table(getattr(self, attr_name))

    def clear_tables(self) -> None:
        """Set the biosphere and technosphere to None."""
        self.df_biosphere, self.df_technosphere = None, None

    def _update_table(self, table: pd.DataFrame, drop: tuple = ("code", "id")):
        """Update the table."""
        self.table.model.sync((table.drop(list(drop), axis=1)).reset_index(drop=True))


class LCAResultsTab(NewAnalysisTab):
    """Class for the 'LCA Results' sub-tab.

    This tab allows the user to get a basic overview of the results of the calculation setup.

    Shows:
        'Overview' and 'by impact category' options for different plots/graphs
        Plots/graphs
        Export buttons
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.lca_scores_widget = LCAScoresTab(parent)
        self.lca_overview_widget = LCIAResultsTab(parent)

        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.layout.addLayout(get_header_layout("LCA Results"))

        # buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.button_group = QtWidgets.QButtonGroup()
        self.button_overview = QtWidgets.QRadioButton("Overview")
        self.button_overview.setToolTip(
            "Show a matrix of all reference flows and all impact categories"
        )
        button_layout.addWidget(self.button_overview)
        self.button_by_method = QtWidgets.QRadioButton("by impact category")
        self.button_by_method.setToolTip(
            "Show the impacts of each reference flow for the selected impact categories"
        )
        self.button_by_method.setChecked(True)
        self.scenario_label = QtWidgets.QLabel("Scenario:")
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
        if self.has_scenarios:
            self.scenario_box.currentIndexChanged.connect(
                self.parent.update_scenario_data
            )
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
        self.lca_overview_widget.update_tab()


class LCAScoresTab(NewAnalysisTab):
    """Class for when 'by impact category' is chosen in the 'LCA Results' sub-tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.combobox_menu = QtWidgets.QHBoxLayout()
        self.combobox_label = QtWidgets.QLabel("Choose impact category:")
        self.combobox = QtWidgets.QComboBox()
        self.combobox.scroll = False
        self.combobox_menu.addWidget(self.combobox_label)
        self.combobox_menu.addWidget(self.combobox, 1)
        self.combobox_menu.addStretch(1)
        self.layout.addLayout(self.combobox_menu)

        self.plot = LCAResultsBarChart(self.parent)
        self.plot.plot_name = "LCA scores_" + self.parent.cs_name
        self.layout.addWidget(self.plot)

        self.layout.addLayout(self.build_export(has_plot=True, has_table=False))

        self.connect_signals()

    def connect_signals(self):
        self.combobox.currentIndexChanged.connect(self.update_plot)

    def build_export(
        self, has_table: bool = True, has_plot: bool = True
    ) -> QtWidgets.QHBoxLayout:
        """Add 3d excel export if scenario-type LCA is performed."""
        layout = super().build_export(has_table, has_plot)
        if self.has_scenarios:
            # Remove the last QSpacerItem from the layout,
            stretch = layout.takeAt(layout.count() - 1)
            # Then add the additional label and export btn, plus new stretch.
            exp_layout = QtWidgets.QHBoxLayout()
            exp_layout.addWidget(QtWidgets.QLabel("Export all data"))

            csv_btn = QtWidgets.QPushButton(".csv")
            csv_btn.setToolTip(
                "Include all reference flows, impact categories and scenarios"
            )
            if self.parent:
                csv_btn.clicked.connect(self.parent.generate_lcia_scenario_csv)

            excel_btn = QtWidgets.QPushButton("Excel")
            excel_btn.setToolTip(
                "Include all reference flows, impact categories and scenarios"
            )
            if self.parent:
                excel_btn.clicked.connect(self.parent.generate_lcia_scenario_excel)

            exp_layout.addWidget(csv_btn)
            exp_layout.addWidget(excel_btn)
            layout.addWidget(vertical_line())
            layout.addLayout(exp_layout)
            layout.addSpacerItem(stretch)
        return layout

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
            bwutils.commontasks.format_activity_label(next(iter(fu.keys())), style="pnld")
            for fu in self.parent.mlca.func_units
        ]
        idx = self.layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.setVisible(False)
        self.plot.deleteLater()
        self.plot = LCAResultsBarChart(self.parent)
        self.layout.insertWidget(idx, self.plot)
        super().update_plot(df, method=method, labels=labels)
        self.updateGeometry()
        self.plot.plot_name = "_".join([self.parent.cs_name, "LCA scores", str(method)])


class LCIAResultsTab(NewAnalysisTab):
    """Class for when 'Overview' is chosen in the 'LCA Results' sub-tab."""

    def __init__(self, parent, **kwargs):
        super(LCIAResultsTab, self).__init__(parent, **kwargs)
        self.parent = parent
        self.df = None
        self.plot_inversion = False

        # if not self.parent.single_func_unit:
        self.plot = LCAResultsPlot(self.parent)
        self.plot.plot_name = self.parent.cs_name + "_LCIA results"
        self.table = LCAResultsTable(self.parent)
        self.table.table_name = self.parent.cs_name + "_LCIA results"
        self.relative = False

        self.layout.addWidget(self.build_main_space(True))
        self.layout.addLayout(self.build_export(True, True))

    def build_export(
        self, has_table: bool = True, has_plot: bool = True
    ) -> QtWidgets.QHBoxLayout:
        """Add 3d excel export if scenario-type LCA is performed."""
        layout = super().build_export(has_table, has_plot)
        if self.has_scenarios:
            # Remove the last QSpacerItem from the layout,
            stretch = layout.takeAt(layout.count() - 1)
            # Then add the additional label and export btn, plus new stretch.
            exp_layout = QtWidgets.QHBoxLayout()
            exp_layout.addWidget(QtWidgets.QLabel("Export all data"))

            csv_btn = QtWidgets.QPushButton(".csv")
            csv_btn.setToolTip(
                "Include all reference flows, impact categories and scenarios"
            )
            if self.parent:
                csv_btn.clicked.connect(self.parent.generate_lcia_scenario_csv)

            excel_btn = QtWidgets.QPushButton("Excel")
            excel_btn.setToolTip(
                "Include all reference flows, impact categories and scenarios"
            )
            if self.parent:
                excel_btn.clicked.connect(self.parent.generate_lcia_scenario_excel)

            exp_layout.addWidget(csv_btn)
            exp_layout.addWidget(excel_btn)
            layout.addWidget(vertical_line())
            layout.addLayout(exp_layout)
            layout.addSpacerItem(stretch)
        return layout

    def update_tab(self):
        self.df = self.parent.contributions.lca_scores_df(normalized=self.relative)
        super().update_tab()

    def update_plot(self):
        """Update the plot."""
        idx = self.pt_layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.setVisible(False)
        self.plot.deleteLater()
        self.plot = LCAResultsPlot(self.parent)
        self.pt_layout.insertWidget(idx, self.plot)
        super().update_plot(self.df, invert_plot=self.plot_inversion)
        if self.pt_layout.parentWidget():
            self.pt_layout.parentWidget().updateGeometry()

    def update_table(self):
        super().update_table(self.df)

class SmallComboBox(QtWidgets.QComboBox):
    """A small combo box that does not expand to fill the available space."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.setMinimumWidth(100)
        self.setMaximumWidth(200)
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)


class ContributionTab(NewAnalysisTab):
    """Parent class for any 'XXX Contributions' sub-tab."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.cutoff_menu = widgets.CutoffMenu(self, cutoff_value=0.05)
        self.combobox_menu = Combobox(
            func=QtWidgets.QComboBox(self),
            func_label=QtWidgets.QLabel("Reference Flow:"),
            method=SmallComboBox(self),
            method_label=QtWidgets.QLabel("Impact Category:"),
            agg=SmallComboBox(self),
            agg_label=QtWidgets.QLabel("Aggregate by:"),
            scenario=self.scenario_box,
            scenario_label=QtWidgets.QLabel("Scenario:"),
        )
        self.switch_label = QtWidgets.QLabel("Compare:")
        self.switches = widgets.SwitchComboBox(self)

        self.relativity = Relativity(
            QtWidgets.QRadioButton("Relative"),
            QtWidgets.QRadioButton("Absolute"),
        )
        self.relativity.relative.setChecked(True)
        self.relative = True
        self.relativity.relative.setToolTip(
            "Show relative values (compare fraction of each contribution)"
        )
        self.relativity.absolute.setToolTip(
            "Show absolute values (compare magnitudes of each contribution)"
        )
        self.relativity_group = QtWidgets.QButtonGroup(self)
        self.relativity_group.addButton(self.relativity.relative)
        self.relativity_group.addButton(self.relativity.absolute)

        self.total_menu = TotalMenu(
            QtWidgets.QRadioButton("Score"),
            QtWidgets.QRadioButton("Range"),
        )
        self.total_menu.score.setChecked(True)
        self.total_range = False
        self.total_menu.score.setToolTip(
            "Show the contributions relative to the <i>total</i> impact score.\n"
            "e.g. total negative results is -2 and total positive results is 10, then score is 8 (-2 + 10)"
        )
        self.total_menu.range.setToolTip(
            "Show the contribution relative to the total <i>range</i> of results.\n"
            "e.g. total negative results is -2 and total positive results is 10, then range is 12 (-2 * -1 + 10)"
        )
        self.total_group = QtWidgets.QButtonGroup(self)
        self.total_group.addButton(self.total_menu.score)
        self.total_group.addButton(self.total_menu.range)

        self.score_marker = settings.project_settings.settings.get("analysis_tab", {}).get(f"{self.__class__.__name__}score_marker_enabled", False)
        self.score_mrk_checkbox = QtWidgets.QCheckBox("Score Marker")
        self.score_mrk_checkbox.setToolTip(
            "Shows the score marker. When there are both positive and negative results,\n"
            "this shows a marker where the total score is."
        )
        self.score_mrk_checkbox.setChecked(self.score_marker)

        self.df = None
        self.plot = ContributionPlot(self)
        self.table = ContributionTable(self)
        self.contribution_fn = None
        self.has_method, self.has_func = False, False
        self.unit = None

        self.has_been_opened = False

        # set-up the help button
        self.explain_text = """
                <p>There are three ways of doing Contribtion Analysis in Activity Browser:</h4>
                <p>- <b>Elementary Flow (EF) Contributions</b></p>
                <p>- <b>Process Contributions</b></p>
                <p>- <b>First Tier (FT) Contributions</b></p>
                
                Detailed information on the different approaches provided in this <a href="https://github.com/LCA-ActivityBrowser/activity-browser/wiki/LCA-Results#contribution-analysis">wiki page</a> about the different approaches. 

                <p>You can manipulate the results in many ways with Activity Browser, read more on this <a href="https://github.com/LCA-ActivityBrowser/activity-browser/wiki/LCA-Results#manipulating-results">wiki page</a>
                about manipulating results. 
                """

        self.help_button = QtWidgets.QToolBar(self)
        self.help_button.addAction(
            icons.qicons.question, "Left click for help on Contribution Analysis Functions", self.explanation
        )

    def set_filename(self, optional_fields: dict = None):
        """Given a dictionary of fields, put together a usable filename for the plot and table."""
        optional = optional_fields or {}
        fields = (
            self.parent.cs_name,
            self.contribution_fn,
            optional.get("method"),
            optional.get("functional_unit"),
            self.unit,
        )

        filename = "_".join((str(x) for x in fields if x is not None))
        self.plot.plot_name, self.table.table_name = filename, filename

    def build_combobox(
        self, has_method: bool = True, has_func: bool = False
    ) -> QtWidgets.QHBoxLayout:
        """Construct a horizontal layout for picking and choosing what data to show and how."""
        menu = QtWidgets.QHBoxLayout()
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
        visible = self.has_scenarios
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
        if self.has_scenarios:
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
        # gather the combobox values
        method = self.parent.method_dict[self.combobox_menu.method.currentText()]
        functional_unit = self.combobox_menu.func.currentText()
        scenario = max(self.combobox_menu.scenario.currentIndex(), 0)  # set scenario 0 if not initiated yet
        aggregator = self.combobox_menu.agg.currentText()

        # set aggregator to None if unwanted
        if aggregator == "none":
            aggregator = None

        # initiate dict with the field we want to compare
        compare_fields = {"aggregator": aggregator}

        # Determine which comparison is active and update the comparison.
        if self.switches.currentIndex() == self.switches.indexes.func:
            compare_fields.update({"method": method, "scenario": scenario})
        elif self.switches.currentIndex() == self.switches.indexes.method:
            compare_fields.update(
                {"functional_unit": functional_unit, "scenario": scenario}
            )
        elif self.switches.currentIndex() == self.switches.indexes.scenario:
            compare_fields.update(
                {
                    "method": method,
                    "functional_unit": functional_unit,
                }
            )

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
        self.combobox_menu.scenario.currentIndexChanged.connect(self.update_tab)

    def update_tab(self):
        """Update the tab."""
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.set_combobox_changes()

        super().update_tab()
        QtWidgets.QApplication.restoreOverrideCursor()

    def update_dataframe(self, *args, **kwargs):
        """Update the underlying dataframe.

        Implement in subclass."""
        raise NotImplementedError

    def update_table(self):
        super().update_table(self.df, unit=self.unit)

    def update_plot(self):
        """Update the plot."""
        idx = self.pt_layout.indexOf(self.plot)
        self.plot.figure.clf()
        # name is already altered by set_filename before update_plot occurs.
        name = self.plot.plot_name
        self.plot.setVisible(False)
        self.plot.deleteLater()
        self.plot = ContributionPlot(self)
        self.pt_layout.insertWidget(idx, self.plot)
        super().update_plot(self.df, unit=self.unit)
        self.plot.plot_name = name
        if self.pt_layout.parentWidget():
            self.pt_layout.parentWidget().updateGeometry()


class ElementaryFlowContributionTab(ContributionTab):
    """Class for the 'Elementary flow Contributions' sub-tab.

    This tab allows for analysis of elementary flows.

    Example questions that can be answered by this tab:
        What is the CO2 production caused by reference flow XXX?
        Which impact is largest on the impact category YYY?
        What are the 5 largest elementary flows caused by reference flow ZZZ?

    Shows:
        Cutoff menu for determining cutoff values
        Compare options button to change between 'Reference Flows' and 'Impact Categories'
        'Impact Category'/'Reference Flow' chooser with aggregation method
        Plot/Table on/off and Relative/Absolute options for data
        Plot/Table
        Export options
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        header = get_header_layout_w_help("Elementary Flow Contributions", self.help_button)
        self.layout.addLayout(header)
        self.layout.addWidget(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())
        combobox = self.build_combobox(has_method=True, has_func=True)
        self.layout.addLayout(combobox)
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(self.build_export(True, True))

        self.contribution_fn = "EF contributions"
        self.switches.configure(self.has_func, self.has_method)
        self.connect_signals()
        self.toggle_comparisons(self.switches.indexes.func)

    def build_combobox(
        self, has_method: bool = True, has_func: bool = False
    ) -> QtWidgets.QHBoxLayout:
        self.combobox_menu.agg.addItems(self.parent.contributions.DEFAULT_EF_AGGREGATES)
        return super().build_combobox(has_method, has_func)

    def update_dataframe(self, *args, **kwargs):
        """Retrieve the top elementary flow contributions."""
        return self.parent.contributions.top_elementary_flow_contributions(
            **kwargs,
            limit=self.cutoff_menu.cutoff_value,
            limit_type=self.cutoff_menu.limit_type,
            normalize=self.relative,
            total_range=self.total_range,
        )


class ProcessContributionsTab(ContributionTab):
    """Class for the 'Process Contributions' sub-tab.

    This tab allows for analysis of process contributions.

    Example questions that can be answered by this tab:
        What is the contribution of electricity production to reference flow XXX?
        Which process contributes the most to impact category YYY?
        What are the top 5 contributing processes to reference flow ZZZ?

    Shows:
        Cutoff menu for determining cutoff values
        Compare options button to change between 'Reference Flows' and 'Impact Categories'
        'Impact Category'/'Reference Flow' chooser with aggregation method
        Plot/Table on/off and Relative/Absolute options for data
        Plot/Table
        Export options
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        header = get_header_layout_w_help("Process Contributions", self.help_button)
        self.layout.addLayout(header)
        self.layout.addWidget(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())
        combobox = self.build_combobox(has_method=True, has_func=True)
        self.layout.addLayout(combobox)
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(self.build_export(True, True))

        self.contribution_fn = "Process contributions"
        self.switches.configure(self.has_func, self.has_method)
        self.connect_signals()
        self.toggle_comparisons(self.switches.indexes.func)

    def build_combobox(
        self, has_method: bool = True, has_func: bool = False
    ) -> QtWidgets.QHBoxLayout:
        self.combobox_menu.agg.addItems(
            self.parent.contributions.DEFAULT_ACT_AGGREGATES
        )
        return super().build_combobox(has_method, has_func)

    def update_dataframe(self, *args, **kwargs):
        """Retrieve the top process contributions"""
        return self.parent.contributions.top_process_contributions(
            **kwargs,
            limit=self.cutoff_menu.cutoff_value,
            limit_type=self.cutoff_menu.limit_type,
            normalize=self.relative,
            total_range=self.total_range,
        )


class FirstTierContributionsTab(ContributionTab):
    """Class for the 'First Tier Contributions' sub-tab.

    This tab allows for analysis of first-tier (product) contributions.
    The direct impact (from biosphere exchanges from the FU)
    and cumulative impacts from all exchange inputs to the FU (first level) are calculated.

    e.g. the direct emissions from steel production and the cumulative impact for all electricity input
    into that activity. This works on the basis of input products and their total (cumulative) impact, scaled to
    how much of that product is needed in the FU.

    Example questions that can be answered by this tab:
        What is the contribution of electricity (product) to reference flow XXX?
        Which input product contributes the most to impact category YYY?
        What products contribute most to reference flow ZZZ?

    Shows:
        Compare options button to change between 'Reference Flows' and 'Impact Categories'
        'Impact Category'/'Reference Flow' chooser with aggregation method
        Plot/Table on/off and Relative/Absolute options for data
        Plot/Table
        Export options
    """

    def __init__(self, cs_name, parent=None):
        super().__init__(parent)

        self.cache = {"scores": {}, "ranges": {}}  # We cache the calculated data, as it can take some time to generate.
        # We cache the individual calculation results, as they are re-used in multiple views
        # e.g. FU1 x method1 x scenario1
        # may be seen in both 'Reference Flows' and 'Impact Categories', just with different axes.
        # we also cache scores/ranges, not for calculation speed, but to be able to easily convert for relative results
        self.caching = True  # set to False to disable caching for debug

        header = get_header_layout_w_help("First Tier Contributions", self.help_button)
        self.layout.addLayout(header)
        self.layout.addWidget(self.cutoff_menu)
        self.layout.addWidget(horizontal_line())
        combobox = self.build_combobox(has_method=True, has_func=True)
        self.layout.addLayout(combobox)
        self.layout.addWidget(horizontal_line())
        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(self.build_export(True, True))

        # get relevant data from calculation setup
        self.cs = cs_name
        func_units = bd.calculation_setups[self.cs]["inv"]
        self.func_keys = [list(fu.keys())[0] for fu in func_units]  # extract a list of keys from the functional units
        self.func_units = [
            {bd.get_activity(k): v for k, v in fu.items()}
            for fu in func_units
        ]
        self.methods = bd.calculation_setups[self.cs]["ia"]

        self.contribution_fn = "First Tier contributions"
        self.switches.configure(self.has_func, self.has_method)
        self.connect_signals()
        self.toggle_comparisons(self.switches.indexes.func)

    def update_tab(self):
        """Update the tab."""
        if self.has_been_opened:
            super().update_tab()

    def build_combobox(
        self, has_method: bool = True, has_func: bool = False
    ) -> QtWidgets.QHBoxLayout:
        self.combobox_menu.agg.addItems(
            self.parent.contributions.DEFAULT_ACT_AGGREGATES
        )
        return super().build_combobox(has_method, has_func)

    def get_data(self, compare) -> List[list]:
        """Get the data for analysis, either from self.cache or from calculation."""
        def try_cache():
            """Get data from cache if exists, otherwise return none."""
            if self.caching:
                return self.cache.get(cache_key, None)

        def calculate():
            """Shorthand for getting calculation results."""
            return self.calculate_contributions(demand, demand_key, demand_index,
                                                method=method, method_index=method_index,
                                                scenario_lca=self.has_scenarios, scenario_index=scenario_index,
                                                )

        # get the right data
        if self.has_scenarios:
            # get the scenario index, if it is -1 (none selected), then use index first index (0)
            scenario_index = max(self.combobox_menu.scenario.currentIndex(), 0)
        else:
            scenario_index = None
        method_index = self.combobox_menu.method.currentIndex()
        method = self.methods[method_index]
        demand_index = self.combobox_menu.func.currentIndex()
        demand = self.func_units[demand_index]
        demand_key = self.func_keys[demand_index]

        all_data = []
        if compare == "Reference Flows":
            # run the analysis for every reference flow
            for demand_index, demand in enumerate(self.func_units):
                demand_key = self.func_keys[demand_index]
                cache_key = (demand_index, method_index, scenario_index)
                # get data from cache if exists, otherwise calculate
                if data := try_cache():
                    all_data.append([demand_key, data])
                    continue

                data = calculate()
                if self.caching:
                    self.cache[cache_key] = data
                all_data.append([demand_key, data])
        elif compare == "Impact Categories":
            # run the analysis for every method
            for method_index, method in enumerate(self.methods):
                cache_key = (demand_index, method_index, scenario_index)

                # get data from cache if exists, otherwise calculate
                if data := try_cache():
                    all_data.append([method, data])
                    continue

                data = calculate()
                if self.caching:
                    self.cache[cache_key] = data
                all_data.append([method, data])
        elif compare == "Scenarios":
            # run the analysis for every scenario
            for scenario_index in range(self.combobox_menu.scenario.count()):
                scenario = self.combobox_menu.scenario.itemText(scenario_index)
                cache_key = (demand_index, method_index, scenario_index)

                # get data from cache if exists, otherwise calculate
                if data := try_cache():
                    all_data.append([scenario, data])
                    continue

                data = calculate()
                if self.caching:
                    self.cache[cache_key] = data
                all_data.append([scenario, data])

        return all_data

    def calculate_contributions(self, demand, demand_key, demand_index,
                                method, method_index: int = None,
                                scenario_lca: bool = False, scenario_index: int = None) -> dict:
        """Retrieve relevant activity data and calculate first tier contributions."""

        def get_default_demands() -> dict:
            """Get the inputs to calculate contributions from the activity"""
            # get exchange keys leading to this activity
            technosphere = bd.get_activity(demand_key).technosphere()

            keys = [exch.input.key for exch in technosphere if
                    exch.input.key != exch.output.key]
            # find scale from production amount and demand amount
            scale = demand[demand_key] / [p for p in bd.get_activity(demand_key).production()][0].amount

            amounts = [exch.amount * scale for exch in technosphere if
                       exch.input.key != exch.output.key]
            demands = {keys[i]: amounts[i] for i, _ in enumerate(keys)}
            return demands

        def get_scenario_demands() -> dict:
            """Get the inputs to calculate contributions from the scenario matrix"""
            # get exchange keys leading to this activity
            technosphere = bd.get_activity(demand_key).technosphere()
            demand_idx = _lca.product_dict[demand_key]

            keys = [exch.input.key for exch in technosphere if
                    exch.input.key != exch.output.key]
            # find scale from production amount and demand amount
            scale = demand[demand_key] / _lca.technosphere_matrix[_lca.activity_dict[demand_key], demand_idx] * -1

            amounts = []

            for exch in technosphere:
                exch_idx = _lca.activity_dict[exch.input.key]
                if exch.input.key != exch.output.key:
                    amounts.append(_lca.technosphere_matrix[exch_idx, demand_idx] * scale)

            # write al non-zero exchanges to demand dict
            demands = {keys[i]: amounts[i] for i, _ in enumerate(keys) if amounts[i] != 0}
            return demands

        # reuse LCA object from original calculation to skip 1 LCA
        if scenario_lca:
            # get score from the already calculated result
            score = self.parent.mlca.lca_scores[demand_index, method_index, scenario_index]

            # get lca object from mlca class
            self.parent.mlca.current = scenario_index
            self.parent.mlca.update_matrices()
            _lca = self.parent.mlca.lca
            _lca.redo_lci(demand)

        else:
            # get score from the already calculated result
            score = self.parent.mlca.lca_scores[demand_index, method_index]

            # get lca object to calculate new results
            _lca = self.parent.mlca.lca

        # set the correct method
        _lca.switch_method(method)
        _lca.lcia_calculation()

        if score == 0:
            # no need to calculate contributions to '0' score
            # technically it could be that positive and negative score of same amount negate to 0, but highly unlikely.
            return {"Score": 0, "Range": 0, demand_key: 0}

        data = {"Score": score}
        _range = []
        remainder = score  # contribution of demand_key

        if not scenario_lca:
            new_demands = get_default_demands()
        else:
            new_demands = get_scenario_demands()

        # iterate over all activities demand_key is connected to
        for key, amt in new_demands.items():

            # recalculate for this demand
            _lca.redo_lci({key: amt})
            _lca.redo_lcia()

            score = _lca.score
            if score != 0:
                # only store non-zero results
                data[key] = score
                _range.append(abs(score))
                remainder -= score  # subtract this from remainder

        data[demand_key] = remainder
        _range.append(abs(remainder))
        data["Range"] = sum(_range)
        return data

    def key_to_metadata(self, key: tuple) -> list:
        """Convert the key information to list with metadata.

        format:
        [reference product, activity name, location, unit, database]
        """
        return list(bwutils.AB_metadata.get_metadata([key], ["reference product", "name", "location", "unit"]).iloc[0]) + [key[0]]

    def metadata_to_index(self, data: list) -> str:
        """Convert list to formatted index.

        format:
        reference product | activity name | location | unit | database
        """
        return " | ".join(data)

    def data_to_df(self, all_data: List[list], compare: str) -> pd.DataFrame:
        """Convert the provided data into a dataframe."""
        unique_keys = set()
        # get all the unique keys:
        d = {"index": [], "reference product": [], "name": [],
             "location": [], "unit": [], "database": []}
        meta_cols = set(d.keys())

        for i, (item, data) in enumerate(all_data):
            # item is a key, method or scenario depending on the `compares`
            unique_keys.update(data.keys())
            # already add the total with right column formatting depending on `compares`
            if compare == "Reference Flows":
                col_name = self.metadata_to_index(self.key_to_metadata(item))
            elif compare == "Impact Categories":
                col_name = self.metadata_to_index(list(item))
            elif compare == "Scenarios":
                col_name = item

            self.cache["scores"][col_name] = data["Score"]
            self.cache["ranges"][col_name] = data["Range"]
            d[col_name] = []

            all_data[i] = item, data, col_name

        if compare == "Impact Categories":
            self.unit = get_unit(method=False, relative=self.relative)
        else:
            self.unit = get_unit(self.parent.method_dict[self.combobox_menu.method.currentText()], self.relative)

        # convert to dict format to feed into dataframe
        for key in unique_keys:
            if key in ["Score", "Range"]:
                continue
            # get metadata
            metadata = self.key_to_metadata(key)
            d["index"].append(self.metadata_to_index(metadata))
            d["reference product"].append(metadata[0])
            d["name"].append(metadata[1])
            d["location"].append(metadata[2])
            d["unit"].append(self.unit)
            d["database"].append(metadata[4])
            # check for each dataset if we have values, otherwise add np.nan
            for item, data, col_name in all_data:
                if val := data.get(key, False):
                    value = val
                else:
                    value = np.nan
                d[col_name].append(value)

        df = pd.DataFrame(d)
        data_cols = [col for col in df if col not in meta_cols]
        df = df.dropna(subset=data_cols, how="all")

        # now, apply aggregation
        group_on = self.combobox_menu.agg.currentText()
        if group_on != "none":
            df = df.groupby(by=group_on, as_index=False).sum()
            df["index"] = df[group_on]
            df = df[["index"] + data_cols]
            meta_cols = ["index"]

        all_contributions = deepcopy(df)

        # now, apply cut-off
        limit_type = self.cutoff_menu.limit_type
        limit = self.cutoff_menu.cutoff_value

        # iterate over the columns to get contributors, then replace cutoff flows with nan
        # nested for is slow, but this should rarely have to deal with >>50 rows (rows == technosphere exchanges)
        contributors = df[data_cols].shape[0]
        for col_num, col in enumerate(df[data_cols].T.values):
            # now, get total:
            if self.total_range:  # total is based on the range
                total = np.nansum(np.abs(col))
            else:  # total is based on the score
                total = np.nansum(col)

            col = np.nan_to_num(col)  # replace nan with 0
            cont = ca.sort_array(col, limit=limit, limit_type=limit_type, total=total)
            # write nans to values not present in cont
            for row_num in range(contributors):
                if row_num not in cont[:, 1]:
                    df.iloc[row_num, col_num + len(meta_cols)] = np.nan

        # drop any rows not contributing to anything
        df = df.dropna(subset=data_cols, how="all")

        # sort by mean square of each row
        func = lambda row: np.nanmean(np.square(row))
        if len(df) > 1:  # but only sort if there is something to sort
            df["_sort_me_"] = df[data_cols].apply(func, axis=1)
            df.sort_values(by="_sort_me_", ascending=False, inplace=True)
            del df["_sort_me_"]

        # add the scores and rest values
        score_and_rest = {col: [] for col in df}
        for col in df:
            if col == "index":
                score_and_rest[col].extend(["Score", "Rest (+)", "Rest (-)"])
            elif col in data_cols:
                # score
                score = self.cache["scores"][col]
                # positive and negative rest values
                pos_rest = (np.sum((all_contributions[col].values)[all_contributions[col].values > 0])
                            - np.sum((df[col].values)[df[col].values > 0]))
                neg_rest = (np.sum((all_contributions[col].values)[all_contributions[col].values < 0])
                            - np.sum((df[col].values)[df[col].values < 0]))

                score_and_rest[col].extend([score, pos_rest, neg_rest])
            else:
                score_and_rest[col].extend(["", "", ""])

        # add the two df together
        df = pd.concat([pd.DataFrame(score_and_rest), df], axis=0)

        # normalize
        if self.relative:
            if self.total_range:
                normalize = [self.cache["ranges"][col] for col in data_cols]
            else:
                normalize = [self.cache["scores"][col] for col in data_cols]
            df[data_cols] = df[data_cols] / normalize

        return df

    def update_dataframe(self, *args, **kwargs):
        """Retrieve the product contributions."""

        compare = self.switches.currentText()

        all_data = self.get_data(compare)
        df = self.data_to_df(all_data, compare)
        return df


class CorrelationsTab(NewAnalysisTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.tab_text = "Correlations"
        self.layout.addLayout(get_header_layout("Correlation Analysis"))

        if not self.parent.single_func_unit:
            self.plot = CorrelationPlot(self.parent)

        self.layout.addWidget(self.build_main_space())
        self.layout.addLayout(
            self.build_export(
                has_table=False, has_plot=not self.parent.single_func_unit
            )
        )

    def update_plot(self):
        """Update the plot."""
        idx = self.pt_layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.setVisible(False)
        self.plot.deleteLater()
        self.plot = CorrelationPlot(self.parent)
        self.pt_layout.insertWidget(idx, self.plot)
        df = self.parent.mlca.get_normalized_scores_df()
        super().update_plot(df)
        if self.pt_layout.parentWidget():
            self.pt_layout.parentWidget().updateGeometry()


class MonteCarloTab(NewAnalysisTab):
    def __init__(self, parent=None):
        super(MonteCarloTab, self).__init__(parent)
        self.parent: LCAResultsSubTab = parent
        header_ = QtWidgets.QToolBar()
        _header = header("Monte Carlo Simulation")
        _header.setToolTip("Left click on the question mark for help")
        header_.addWidget(_header)
        header_.addAction(
            icons.qicons.question,
            "Left click for help on Monte Carlo analysis",
            self.explanation,
        )
        self.layout.addWidget(header_)
        self.scenario_label = QtWidgets.QLabel("Scenario:")
        self.include_box = QtWidgets.QGroupBox("Include uncertainty for:", self)
        grid = QtWidgets.QGridLayout()
        self.include_tech = QtWidgets.QCheckBox("Technosphere", self)
        self.include_tech.setChecked(True)
        self.include_bio = QtWidgets.QCheckBox("Biosphere", self)
        self.include_bio.setChecked(True)
        self.include_cf = QtWidgets.QCheckBox("Characterization Factors", self)
        self.include_cf.setChecked(False)
        self.include_cf.setEnabled(False)
        self.include_parameters = QtWidgets.QCheckBox("Parameters", self)
        self.include_parameters.setChecked(False)
        self.include_parameters.setEnabled(False)
        grid.addWidget(self.include_tech, 0, 0)
        grid.addWidget(self.include_bio, 0, 1)
        grid.addWidget(self.include_cf, 1, 0)
        grid.addWidget(self.include_parameters, 1, 1)
        self.include_box.setLayout(grid)

        self.add_MC_ui_elements()

        self.table = LCAResultsTable()
        self.table.table_name = "MonteCarlo_" + self.parent.cs_name
        self.plot = MonteCarloPlot(self.parent)
        self.plot.hide()
        self.plot.plot_name = "MonteCarlo_" + self.parent.cs_name
        self.layout.addWidget(self.plot)
        self.export_widget = self.build_export(has_plot=True, has_table=True)
        self.layout.addWidget(self.export_widget)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.connect_signals()
        self.explain_text = """
            <p><b>Monte Carlo Analyses</b></p>
            <p><b>Monte Carlo</b> simulations generate stochastic data samples using existing data defined parameter 
            distributions for generating the expected distribution for the reference flows. </p>
            <p>More <b>simply</b>, within the LCA model the user may define certain uncertainty distributions for some 
            (or all) parameters. Monte Carlo analysis uses these defined uncertainty distributions with a stochastic 
            generator to sample from these distributions. This results in a "posterior" (or final) probability 
            distribution, expressing the expected variance, for the reference flows.</p>
             <p><a href="https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Monte-Carlo-Simulation">More 
             information can be found here</a></p>
        """

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

        if self.has_scenarios:
            self.scenario_box.currentIndexChanged.connect(
                self.parent.update_scenario_data
            )
            self.parent.update_scenario_box_index.connect(
                lambda index: self.set_combobox_index(self.scenario_box, index)
            )

    def add_MC_ui_elements(self):
        layout_mc = QtWidgets.QVBoxLayout()

        # H-LAYOUT start simulation
        self.button_run = QtWidgets.QPushButton("Run")
        self.label_iterations = QtWidgets.QLabel("Iterations:")
        self.iterations = QtWidgets.QLineEdit("30")
        self.iterations.setFixedWidth(40)
        self.iterations.setValidator(QtGui.QIntValidator(1, 1000))
        self.label_seed = QtWidgets.QLabel("Random seed:")
        self.label_seed.setToolTip(
            "Seed value (integer) for the random number generator. "
            "Use this for reproducible samples."
        )
        self.seed = QtWidgets.QLineEdit("")
        self.seed.setFixedWidth(30)

        self.hlayout_run = QtWidgets.QHBoxLayout()
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
        # self.radio_button_all_fu = QRadioButton("For all reference flows")
        # self.radio_button_all_methods = QRadioButton("Technosphere flows")
        #
        # self.radio_button_biosphere.setChecked(True)
        # self.radio_button_technosphere.setChecked(False)
        #
        # self.label_for_all_fu = QLabel('For all reference flows')
        # self.combobox_fu = QRadioButton()
        # self.hlayout_fu = QHBoxLayout()

        # FU selection
        # self.label_fu = QLabel('Choose reference flow')
        # self.combobox_fu = QComboBox()
        # self.hlayout_fu = QHBoxLayout()
        #
        # self.hlayout_fu.addWidget(self.label_fu)
        # self.hlayout_fu.addWidget(self.combobox_fu)
        # self.hlayout_fu.addStretch()
        # self.layout_mc.addLayout(self.hlayout_fu)

        # method selection
        self.method_selection_widget = QtWidgets.QWidget()
        self.label_methods = QtWidgets.QLabel("Choose impact category")
        self.combobox_methods = QtWidgets.QComboBox()
        self.hlayout_methods = QtWidgets.QHBoxLayout()

        self.hlayout_methods.addWidget(self.label_methods)
        self.hlayout_methods.addWidget(self.combobox_methods)
        self.hlayout_methods.addStretch()
        self.method_selection_widget.setLayout(self.hlayout_methods)

        layout_mc.addWidget(self.method_selection_widget)
        self.method_selection_widget.hide()

        self.layout.addLayout(layout_mc)

    def build_export(self, has_table: bool = True, has_plot: bool = True) -> QtWidgets.QWidget:
        """Construct the export layout but set it into a widget because we
        want to hide it."""
        export_layout = super().build_export(has_table, has_plot)
        export_widget = QtWidgets.QWidget()
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
            log.info(f"SEED: {self.seed.text()}")
            try:
                seed = int(self.seed.text())
            except ValueError as e:
                log.error(
                    "Seed value must be an integer number or left empty.", exc_info=e
                )
                QtWidgets.QMessageBox.warning(
                    self,
                    "Warning",
                    "Seed value must be an integer number or left empty.",
                )
                self.seed.setText("")
                return
        includes = {
            "technosphere": self.include_tech.isChecked(),
            "biosphere": self.include_bio.isChecked(),
            "cf": self.include_cf.isChecked(),
            "parameters": self.include_parameters.isChecked(),
        }

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self.parent.mc.calculate(iterations=iterations, seed=seed, **includes)
            signals.monte_carlo_finished.emit()
            self.update_mc()
        except (
            InvalidParamsError
        ) as e:  # This can occur if uncertainty data is missing or otherwise broken
            # print(e)
            log.error(e)
            QtWidgets.QMessageBox.warning(
                self, "Could not perform Monte Carlo simulation", str(e)
            )
        QtWidgets.QApplication.restoreOverrideCursor()

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
        self.scenario_label.setVisible(self.has_scenarios)

    def update_tab(self):
        self.update_combobox(
            self.combobox_methods, [str(m) for m in self.parent.mc.methods]
        )
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
        filename = "_".join(
            [str(x) for x in [self.parent.cs_name, "Monte Carlo results", str(method)]]
        )
        self.plot.plot_name, self.table.table_name = filename, filename

    def update_plot(self, method):
        idx = self.layout.indexOf(self.plot)
        self.plot.figure.clf()
        self.plot.setVisible(False)
        self.plot.deleteLater()
        # name is already altered by update_mc before update_plot
        name = self.plot.plot_name
        self.plot = MonteCarloPlot(self.parent)
        self.layout.insertWidget(idx, self.plot)
        super().update_plot(self.df, method=method)
        self.plot.plot_name = name
        self.plot.show()
        if self.layout.parentWidget():
            self.layout.parentWidget().updateGeometry()

    def update_table(self):
        super().update_table(self.df)


class GSATab(NewAnalysisTab):
    def __init__(self, parent=None):
        super(GSATab, self).__init__(parent)
        self.parent = parent

        self.GSA = bwutils.GlobalSensitivityAnalysis(self.parent.mc)

        header_ = QtWidgets.QToolBar()
        _header = header("Global Sensitivity Analysis")
        _header.setToolTip("Left click on the question mark for help")
        header_.addWidget(_header)
        header_.addAction(
            icons.qicons.question,
            "Left click for help on Global Sensitivity Analysis",
            self.explanation,
        )

        self.layout.addWidget(header_)
        self.scenario_box = None

        self.add_GSA_ui_elements()

        self.table = LCAResultsTable()
        self.table.table_name = "GSA_" + self.parent.cs_name
        self.layout.addWidget(self.table)
        self.table.hide()
        # self.plot = MonteCarloPlot(self.parent)
        # self.plot.hide()
        # self.plot.plot_name = 'GSA_' + self.parent.cs_name
        # self.layout.addWidget(self.plot)

        self.export_widget = self.build_export(has_plot=False, has_table=True)
        self.layout.addWidget(self.export_widget)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.connect_signals()

        self.explain_text = """
            <p><b>Global Sensitivity Analysis (GSA)</b> is a family of methods that, used in conjunction with distribution
            generating functions, can investigate the contributions of model variables on the final results.</p>
             <p>Within the AB running a GSA depends on the use of a Monte Carlo simulation for generating the
             variable distributions for the reference flow(s), upon which the GSA is performed. Running the GSA executes
             the stochastic simulations whilst fixing the values of selected variables of interest. Taking a lower and
             upper bound for the variables, therefore, indicates the influence of the fixed variable on the overall 
             level of model variability. </p>
             <p>For a more detailed explanation <a href="https://github.com/LCA-ActivityBrowser/activity-browser/wiki/Global-Sensitivity-Analysis">see the wiki</a></p>
             <p>The paper describing the methods is published by <a href="https://onlinelibrary.wiley.com/doi/10.1111/jiec.13194">Wiley online</a></p> 
        """

    def connect_signals(self):
        self.button_run.clicked.connect(self.calculate_gsa)
        signals.monte_carlo_finished.connect(self.monte_carlo_finished)

    def add_GSA_ui_elements(self):
        # H-LAYOUT SETTINGS ROW 1

        # run button
        self.button_run = QtWidgets.QPushButton("Run")
        self.button_run.setEnabled(False)

        # reference flow selection
        self.label_fu = QtWidgets.QLabel("Reference Flow:")
        self.combobox_fu = QtWidgets.QComboBox()

        # method selection
        self.label_methods = QtWidgets.QLabel("Impact Category:")
        self.combobox_methods = QtWidgets.QComboBox()

        # arrange layout
        self.hlayout_row1 = QtWidgets.QHBoxLayout()
        self.hlayout_row1.addWidget(self.button_run)
        self.hlayout_row1.addWidget(self.label_fu)
        self.hlayout_row1.addWidget(self.combobox_fu)
        self.hlayout_row1.addWidget(self.label_methods)
        self.hlayout_row1.addWidget(self.combobox_methods)

        # self.hlayout_row1.addWidget(self.fu_selection_widget)
        # self.hlayout_row1.addWidget(self.method_selection_widget)
        self.hlayout_row1.addStretch(1)

        # H-LAYOUT SETTINGS ROW 2
        self.hlayout_row2 = QtWidgets.QHBoxLayout()

        # cutoff technosphere
        self.label_cutoff_technosphere = QtWidgets.QLabel("Cut-off technosphere:")
        self.cutoff_technosphere = QtWidgets.QLineEdit("0.01")
        self.cutoff_technosphere.setFixedWidth(40)
        self.cutoff_technosphere.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 5))

        # cutoff biosphere
        self.label_cutoff_biosphere = QtWidgets.QLabel("Cut-off biosphere:")
        self.cutoff_biosphere = QtWidgets.QLineEdit("0.01")
        self.cutoff_biosphere.setFixedWidth(40)
        self.cutoff_biosphere.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 5))

        # export GSA input/output data automatically with run
        self.checkbox_export_data_automatically = QtWidgets.QCheckBox(
            "Save input/output data to Excel after run"
        )
        self.checkbox_export_data_automatically.setChecked(False)

        # # exclude Pedigree
        # self.checkbox_pedigree = QCheckBox('Include Pedigree uncertainties')
        # self.checkbox_pedigree.setChecked(True)

        # arrange layout
        self.hlayout_row2.addWidget(self.label_cutoff_technosphere)
        self.hlayout_row2.addWidget(self.cutoff_technosphere)
        self.hlayout_row2.addWidget(self.label_cutoff_biosphere)
        self.hlayout_row2.addWidget(self.cutoff_biosphere)
        self.hlayout_row2.addWidget(self.checkbox_export_data_automatically)
        # self.hlayout_row2.addWidget(self.checkbox_pedigree)
        self.hlayout_row2.addStretch(1)

        # OVERALL LAYOUT OF SETTINGS
        self.layout_settings = QtWidgets.QVBoxLayout()
        self.layout_settings.addLayout(self.hlayout_row1)
        self.layout_settings.addLayout(self.hlayout_row2)
        self.widget_settings = QtWidgets.QWidget()
        self.widget_settings.setLayout(self.layout_settings)

        # add to GSA layout
        self.label_monte_carlo_first = QtWidgets.QLabel(
            "You need to run a Monte Carlo Simulation first."
        )
        self.layout.addWidget(self.label_monte_carlo_first)
        self.layout.addWidget(self.widget_settings)

        # at start
        # todo: this is just for development, should be reversed later:
        self.widget_settings.hide()
        # self.label_monte_carlo_first.hide()

    def update_tab(self):
        self.update_combobox(
            self.combobox_methods, [str(m) for m in self.parent.mc.methods]
        )
        self.update_combobox(
            self.combobox_fu, list(self.parent.mlca.func_unit_translation_dict.keys())
        )

    def monte_carlo_finished(self):
        self.button_run.setEnabled(True)
        self.widget_settings.show()
        self.label_monte_carlo_first.hide()

    def calculate_gsa(self):
        act_number = self.combobox_fu.currentIndex()
        method_number = self.combobox_methods.currentIndex()
        cutoff_technosphere = float(self.cutoff_technosphere.text())
        cutoff_biosphere = float(self.cutoff_biosphere.text())
        # print('Calculating GSA for: ', act_number, method_number, cutoff_technosphere, cutoff_biosphere)

        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.GSA.perform_GSA(
                act_number=act_number,
                method_number=method_number,
                cutoff_technosphere=cutoff_technosphere,
                cutoff_biosphere=cutoff_biosphere,
            )
            # self.update_mc()
        except Exception as e:  # Catch any error...
            log.error(e)
            message = str(e)
            message_addition = ""
            if message == "singular matrix":
                message_addition = "\nIn order to avoid this happening, please increase the Monte Carlo iterations (e.g. to above 50)."
            elif message == "`dataset` input should have multiple elements.":
                message_addition = "\nIn order to avoid this happening, please increase the Monte Carlo iterations (e.g. to above 50)."
            elif message == "No objects to concatenate":
                message_addition = (
                    "\nThe reason for this is likely that there are no uncertain exchanges. Please check "
                    "the checkboxes in the Monte Carlo tab."
                )
            QtWidgets.QMessageBox.warning(
                self, "Could not perform GSA", str(message) + message_addition
            )
        QtWidgets.QApplication.restoreOverrideCursor()

        self.update_gsa()

    def update_gsa(self, cs_name=None):
        self.df = getattr(self.GSA, "df_final", None)
        if self.df is None:
            return
        self.update_table()
        self.table.show()
        self.export_widget.show()

        self.table.table_name = "gsa_output_" + self.GSA.get_save_name()

        if self.checkbox_export_data_automatically.isChecked():
            log.info("EXPORTING DATA")
            self.GSA.export_GSA_input()
            self.GSA.export_GSA_output()

    def update_plot(self, method):
        pass

    def update_table(self):
        super().update_table(self.df)

    def build_export(self, has_table: bool = True, has_plot: bool = True) -> QtWidgets.QWidget:
        """Construct the export layout but set it into a widget because we
        want to hide it."""
        export_layout = super().build_export(has_table, has_plot)
        export_widget = QtWidgets.QWidget()
        export_widget.setLayout(export_layout)
        # Hide widget until MC is calculated
        export_widget.hide()
        return export_widget

    # TODO review if can be removed
    # def set_filename(self, optional_fields: dict = None):
    #     """Given a dictionary of fields, put together a usable filename for the plot and table."""
    #     save_name = 'gsa_output_' + self.mc.cs_name + '_' + str(self.mc.iterations) + '_' + self.activity['name'] + \
    #                 '_' + str(self.method) + '.xlsx'
    #     save_name = save_name.replace(',', '').replace("'", '').replace("/", '')
    #     self.table.table_name = save_name
    #     optional = optional_fields or {}
    #     fields = (
    #         self.parent.cs_name, self.contribution_fn, optional.get("method"),
    #         optional.get("functional_unit"), self.unit
    #     )
    #     filename = '_'.join((str(x) for x in fields if x is not None))


class MonteCarloWorkerThread(QtCore.QThread):
    """A worker for Monte Carlo simulations.

    Unfortunately, pyparadiso does not allow parallel calculations on Windows (crashes).
    So this is for future reference in case this issue is solved..."""

    def __init__(self):
        pass

    def set_mc(self, mc, iterations=20):
        self.mc = mc
        self.iterations = iterations

    def run(self):
        log.info(f"Starting new Worker Thread. Iterations: {self.iterations}")
        self.mc.calculate(iterations=self.iterations)
        # res = bw.GraphTraversal().calculate(self.demand, self.method, self.cutoff, self.max_calc)
        log.info("in thread {}".format(QtCore.QThread.currentThread()))
        signals.monte_carlo_ready.emit(self.mc.cs_name)


worker_thread = MonteCarloWorkerThread()

# TODO review if can be removed

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
