"""LCA Results page: tab widget shell and analysis sub-tabs.

Each calculation setup opens an :class:`LCAResultsPage` with sub-tabs for inventory,
LCIA scores, contributions, Sankey, Monte Carlo, and GSA. Shared tab chrome lives in
:mod:`style`; tables and plots in sibling modules; data builders in ``bwutils``.
"""

import os
from collections import namedtuple
from copy import deepcopy
from typing import List, Optional
from loguru import logger
from datetime import datetime

import numpy as np
import pandas as pd
import bw2data as bd
from qtpy import QtCore, QtGui, QtWidgets

from stats_arrays.errors import InvalidParamsError

from activity_browser import app
from activity_browser.bwutils import filesystem
from activity_browser.bwutils.commontasks import get_LCIA_method_name_dict
from activity_browser.bwutils.contribution_labels import contribution_axis_unit
from activity_browser.bwutils.export_names import (
    contribution_compare_export_slug,
    contribution_tab_slug,
    export_name_slug,
    flip_export_slug,
    lcia_compare_export_slug,
    lca_export_basename,
    relativity_export_slug,
)
from activity_browser.bwutils.lcia_overview import (
    LCIACompareMode,
    available_compare_modes,
    build_lcia_overview,
    compare_mode_supports_flip,
    lcia_compare_labels_for_modes,
    lcia_compare_mode_from_label,
)
from activity_browser.bwutils.sensitivity_analysis import GlobalSensitivityAnalysis
from activity_browser.mod.bw2analyzer import ABContributionAnalysis
from activity_browser.ui import widgets

from .combobox_utils import set_combobox_index, update_combobox
from .style import (
    configure_lca_tab_layout,
    lca_header_layout,
    lca_help_tool_button,
    lca_run_button,
    lca_tab_control_row,
    lca_tab_controls_section,
    SmallComboBox,
    vertical_line,
)
from .tables import ContributionTable, InventoryTable, LCAResultsTable
from .plots import (
    ContributionPlot,
    LCIAResultsOverviewPlot,
    MonteCarloPlot,
    GSAPlot,
)
from .sankey_navigator import SankeyNavigatorWidget

ca = ABContributionAnalysis()


# Special namedtuple for the LCAResults TabWidget.
Tabs = namedtuple(
    "tabs", ("inventory", "results", "ef", "process", "sankey", "tree", "mc", "gsa")
)
Relativity = namedtuple("relativity", ("relative", "absolute"))
TotalMenu = namedtuple("total_menu", ("score", "range"))
FULL_LABELS_TOOLTIP = (
    "Show full reference-flow, process, and contributor names on axes and titles "
    "(wrapped where space is limited). Legend entries are always wrapped."
)
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

    def __init__(self, cs_name, mlca, contributions, mc, parent=None):
        super().__init__(parent)
        self.setObjectName(f"{cs_name}-{datetime.now().strftime('%H:%M:%S')}")
        self.setWindowTitle(f"{cs_name} [{datetime.now().strftime('%H:%M')}]")

        self.cs_name, self.mlca, self.contributions, self.mc = cs_name, mlca, contributions, mc
        self.cs = bd.calculation_setups[self.cs_name]
        self.has_scenarios: bool = hasattr(mlca, "scenario_names")
        self.method_dict = get_LCIA_method_name_dict(self.mlca.methods)

        self.setMovable(True)
        # Match ABTabWidget: long sub-tab names must not set a wide minimum for the main window
        # or the central/dock splitter (QTabBar sizeHint is otherwise the full label widths).
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.tabBar().setUsesScrollButtons(True)
        if hasattr(QtCore.Qt, "TextElideMode"):
            self.setElideMode(QtCore.Qt.TextElideMode.ElideRight)
        else:
            self.setElideMode(QtCore.Qt.ElideRight)
        self.setVisible(False)
        self.visible = False

        self.tabs = Tabs(
            inventory=InventoryTab(self),
            results=LCAResultsTab(self),
            ef=ElementaryFlowContributionTab(self),
            process=ProcessContributionsTab(self),
            # ft=FirstTierContributionsTab(self.cs_name, parent=self),
            sankey=SankeyNavigatorWidget(self.cs_name, parent=self),
            tree=None,
            mc=MonteCarloTab(self),  # mc=None if self.mc is None else MonteCarloTab(self),
            gsa=GSATab(self),
        )
        self.tab_names = Tabs(
            inventory="Inventory",
            results="LCA scores",
            ef="EF Contributions",
            process="Process Contributions",
            # ft="FT Contributions",
            sankey="Sankey",
            tree=None,
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

    @QtCore.Slot(int, name="generateSankeyOnClick")
    def generate_content_on_click(self, index):
        if index == self.indexOf(self.tabs.sankey):
            if not self.tabs.sankey.has_sankey:
                logger.info("Generating Sankey Tab")
                self.tabs.sankey.new_sankey()
        # elif index == self.indexOf(self.tabs.ft):
        #     if not self.tabs.ft.has_been_opened:
        #         logger.info("Generating First Tier results")
        #         self.tabs.ft.has_been_opened = True
        #         self.tabs.ft.update_tab()

    def _scenario_export_filepath(self, default_name: str, file_filter: str):
        safe_name = bd.utils.safe_filename(default_name, add_hash=False)
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Choose location to save lca results",
            dir=str(os.path.join(filesystem.get_project_path(), safe_name)),
            filter=file_filter,
        )
        return str(filepath) if filepath else filepath

    @QtCore.Slot(name="lciaScenarioExport")
    def generate_lcia_scenario_csv(self):
        """Create a dataframe of the impact category results for all reference flows,
        impact categories and scenarios, then call the 'export to csv'
        """
        df = self.mlca.lca_scores_to_dataframe()
        default_name = lca_export_basename(self.cs_name, "LCIA results_all")
        filepath = self._scenario_export_filepath(
            default_name, "Comma Separated Values (*.csv);; All Files (*.*)"
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
        default_name = lca_export_basename(self.cs_name, "LCIA results_all")
        filepath = self._scenario_export_filepath(
            default_name, "Excel (*.xlsx);; All Files (*.*)"
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
        self.export_plot: Optional[ExportPlot] = None
        self.export_table: Optional[ExportTable] = None

        self.scenario_box = SmallComboBox()
        self.pt_layout = QtWidgets.QVBoxLayout()
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        configure_lca_tab_layout(self.layout)

    def add_tab_header(
        self, title: str, help_tooltip: Optional[str] = None
    ) -> None:
        """Title row; optional compact help button (same height as plain headers)."""
        help_widget = None
        if help_tooltip is not None:
            help_widget = lca_help_tool_button(self, help_tooltip, self.explanation)
        self.layout.addLayout(lca_header_layout(title, help_widget))

    def add_tab_control_rows(self, *rows: QtWidgets.QHBoxLayout) -> None:
        for row in rows:
            self.layout.addLayout(row)

    def build_tab_body(
        self,
        alignment: QtCore.Qt.Alignment = QtCore.Qt.AlignVCenter,
    ) -> QtWidgets.QWidget:
        """Standard expandable plot/table area used across LCA result tabs."""
        widget = QtWidgets.QWidget()
        widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        widget.setMinimumWidth(0)
        self.pt_layout.setContentsMargins(0, 0, 0, 0)
        self.pt_layout.setAlignment(alignment)
        widget.setLayout(self.pt_layout)
        return widget

    def populate_tab_body(
        self,
        *,
        plot_stretch: int = 1,
        table_stretch: int = 1,
        alignment: QtCore.Qt.Alignment = QtCore.Qt.AlignVCenter,
    ) -> QtWidgets.QWidget:
        if self.plot:
            self.pt_layout.addWidget(self.plot, plot_stretch)
        if self.table:
            self.pt_layout.addWidget(self.table, table_stretch)
        self.space_check()
        return self.build_tab_body(alignment=alignment)

    def add_tab_footer(
        self,
        has_plot: bool = True,
        has_table: bool = True,
        *,
        wrapped: bool = False,
    ) -> Optional[QtWidgets.QWidget]:
        export_layout = self.build_export(has_table=has_table, has_plot=has_plot)
        if wrapped:
            footer = QtWidgets.QWidget(self)
            footer.setLayout(export_layout)
            self.layout.addWidget(footer)
            return footer
        self.layout.addLayout(export_layout)
        return None

    def add_tab_body_with_placeholder(self) -> QtWidgets.QWidget:
        """Add expandable body plus placeholder so chrome stays at the top when empty."""
        self.body_placeholder = QtWidgets.QWidget()
        self.body_placeholder.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.main_content = self.populate_tab_body()
        self.main_content.hide()
        self.layout.addWidget(self.body_placeholder, 1)
        self.layout.addWidget(self.main_content, 1)
        return self.main_content

    def set_tab_body_visible(self, visible: bool) -> None:
        """Toggle between placeholder stretch and the results body."""
        if not hasattr(self, "body_placeholder"):
            return
        self.body_placeholder.setVisible(not visible)
        self.main_content.setVisible(visible)

    def _setup_plot_table_widgets(self, invertable: bool = False) -> None:
        """Create Plot/Table view controls (exclusive radio buttons) and optional Invert."""
        if getattr(self, "_plot_table_toolbar_initialized", False):
            return
        plot_radio = QtWidgets.QRadioButton("Plot")
        table_radio = QtWidgets.QRadioButton("Table")
        plot_radio.setToolTip("Show results as a chart")
        table_radio.setToolTip("Show results as a table")
        invert_widget = None
        if invertable:
            invert_widget = QtWidgets.QCheckBox("Invert")
            invert_widget.setChecked(False)
            invert_widget.stateChanged.connect(self.invert_plot)
        self.plot_table = PlotTableCheck(plot_radio, table_radio, invert_widget)
        self._plot_table_view_group = QtWidgets.QButtonGroup(self)
        self._plot_table_view_group.setExclusive(True)
        self._plot_table_view_group.addButton(self.plot_table.plot, 0)
        self._plot_table_view_group.addButton(self.plot_table.table, 1)
        self._plot_table_view_group.blockSignals(True)
        self.plot_table.plot.setChecked(True)
        self._plot_table_view_group.blockSignals(False)
        self._plot_table_view_group.buttonClicked.connect(self._on_plot_table_view_changed)
        self._plot_table_toolbar_initialized = True

    def _append_plot_options_widgets(self, row: QtWidgets.QHBoxLayout) -> None:
        """Append Relative/Absolute, Score/Range, and Horizontal to a row."""
        if self.relativity:
            row.addWidget(self.relativity.relative)
            row.addWidget(self.relativity.absolute)
            if not getattr(self, "_relativity_toggle_connected", False):
                self.relativity.relative.toggled.connect(self.relativity_check)
                self._relativity_toggle_connected = True
        if self.total_menu:
            row.addWidget(vertical_line())
            row.addWidget(self.total_menu.score)
            row.addWidget(self.total_menu.range)
            if not getattr(self, "_total_toggle_connected", False):
                self.total_menu.range.toggled.connect(self.total_check)
                self._total_toggle_connected = True
        if hasattr(self, "horizontal_checkbox"):
            row.addWidget(vertical_line())
            row.addWidget(self.horizontal_checkbox)
        if hasattr(self, "full_labels_checkbox"):
            row.addWidget(self.full_labels_checkbox)
            if not getattr(self, "_full_labels_toggle_connected", False):
                self.full_labels_checkbox.toggled.connect(self._full_labels_check)
                self._full_labels_toggle_connected = True
        row.addStretch()

    @QtCore.Slot(name="invertPlot")
    def invert_plot(self):
        if not self.plot_table or self.plot_table.invert is None:
            return
        self.plot_inversion = self.plot_table.invert.isChecked()
        self.space_check()
        self.update_plot()

    @QtCore.Slot(QtWidgets.QAbstractButton)
    def _on_plot_table_view_changed(self, _button: QtWidgets.QAbstractButton) -> None:
        if not self.plot_table:
            return
        self.space_check()
        if self.plot and self.plot_table.plot.isChecked():
            self.update_plot()
        if self.table and self.plot_table.table.isChecked():
            self.update_table()

    @QtCore.Slot(name="updatePlotTableVisibility")
    def space_check(self):
        """Show plot or table according to the selected view radio."""
        if not self.plot_table:
            return
        if self.plot:
            self.plot.setVisible(self.plot_table.plot.isChecked())
        if self.table:
            self.table.setVisible(self.plot_table.table.isChecked())

    @QtCore.Slot(bool, name="isRelativeToggled")
    def relativity_check(self, checked: bool):
        """Check if the relative or absolute option is selected."""
        self.relative = checked
        self._update_score_range_enabled()
        self.update_tab()

    def _update_score_range_enabled(self) -> None:
        """Score/Range normalization only applies in relative mode."""
        if not self.total_menu:
            return
        enabled = bool(self.relative)
        self.total_menu.score.setEnabled(enabled)
        self.total_menu.range.setEnabled(enabled)

    @QtCore.Slot(bool, name="isTotalToggled")
    def total_check(self, checked: bool):
        """Check if the relative or absolute option is selected."""
        self.total_range = checked
        self.update_tab()

    @QtCore.Slot(bool, name="horizontalBarsToggled")
    def _horizontal_bars_check(self, checked: bool) -> None:
        self.horizontal_bars = checked
        self.update_tab()

    @QtCore.Slot(bool, name="fullLabelsToggled")
    def _full_labels_check(self, checked: bool) -> None:
        self.full_labels = checked
        self.update_tab()

    def get_scenario_labels(self) -> List[str]:
        """Get scenario labels if scenarios are used."""
        from .combobox_utils import scenario_labels

        return scenario_labels(self.parent)

    def configure_scenario(self):
        """Determine if scenario Qt widgets are visible or not and retrieve
        scenario labels for the selection drop-down box.
        """
        if self.scenario_box:
            self.scenario_box.setVisible(self.has_scenarios)
            update_combobox(self.scenario_box, self.get_scenario_labels())

    set_combobox_index = staticmethod(set_combobox_index)
    update_combobox = staticmethod(update_combobox)

    @QtCore.Slot(int, name="scenarioIndexChanged")
    def _on_scenario_index_changed(self, index: int) -> None:
        """Refresh this tab when its scenario selector changes (tab-local state)."""
        self.update_tab()

    def _plot_view_selected(self) -> bool:
        """Whether the Plot view is selected (ignores real visibility in the window).

        Do not use QWidget.isVisible() here: tabs not yet shown still need their
        plot data refreshed, otherwise figures stay blank until the user switches views.
        """
        if not self.plot_table:
            return True
        return self.plot_table.plot.isChecked()

    def _table_view_selected(self) -> bool:
        if not self.plot_table:
            return True
        return self.plot_table.table.isChecked()

    def update_tab(self):
        """Update the plot and/or table for the views that are selected."""
        if self.plot and self._plot_view_selected():
            self.update_plot()
        # Keep the table model in sync even when the plot view is shown (export uses it).
        if self.table:
            self.update_table()

    def update_table(self, *args, **kwargs):
        """Update the table."""
        self.table.model.sync(*args, **kwargs)

    def update_plot(self, *args, **kwargs):
        """Update the plot."""
        self.plot.plot(*args, **kwargs)

    def _export_plot_png(self) -> None:
        if self.plot is not None:
            self.plot.to_png()

    def _export_plot_svg(self) -> None:
        if self.plot is not None:
            self.plot.to_svg()

    def _export_table_copy(self) -> None:
        if self.table is not None:
            self.table.to_clipboard()

    def _export_table_csv(self) -> None:
        if self.table is not None:
            self.table.to_csv()

    def _export_table_excel(self) -> None:
        if self.table is not None:
            self.table.to_excel()

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
            self.export_plot.png.clicked.connect(self._export_plot_png)
            self.export_plot.svg.clicked.connect(self._export_plot_svg)
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
            self.export_table.copy.clicked.connect(self._export_table_copy)
            self.export_table.csv.clicked.connect(self._export_table_csv)
            self.export_table.excel.clicked.connect(self._export_table_excel)
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

    _CF_FILTER_OPTIONS = (
        ("All flows", "No filtering with categorisation factors"),
        ("Without CFs", "Flows without categorisation factors"),
        ("With CFs", "Flows with categorisation factors"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_biosphere = None
        self.df_technosphere = None

        self.add_tab_header("Inventory")
        self.bio_tech_button_group = QtWidgets.QButtonGroup(self)
        self.bio_categorisation_factor_group = SmallComboBox(self)
        self.bio_categorisation_factor_group.setToolTip(
            "Filter biosphere flows by characterization-factor coverage:\n"
            "All flows — no filter\n"
            "Without CFs — flows without characterization factors\n"
            "With CFs — flows with characterization factors"
        )

        self.radio_button_biosphere = QtWidgets.QRadioButton("Biosphere flows")
        self.radio_button_biosphere.setChecked(True)
        self.radio_button_technosphere = QtWidgets.QRadioButton("Technosphere flows")
        self.bio_tech_button_group.addButton(self.radio_button_biosphere)
        self.bio_tech_button_group.addButton(self.radio_button_technosphere)

        self.remove_zeros_checkbox = QtWidgets.QCheckBox("Remove '0' values")
        self.remove_zero_state = False

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

        for short_label, full_label in self._CF_FILTER_OPTIONS:
            self.bio_categorisation_factor_group.addItem(short_label)
            index = self.bio_categorisation_factor_group.count() - 1
            self.bio_categorisation_factor_group.setItemData(
                index, full_label, QtCore.Qt.ToolTipRole
            )
        self.categorisation_filter_with_flows = None

        self.filter_flows_label = QtWidgets.QLabel("Filter flows:")

        controls_layout = lca_tab_control_row()
        controls_layout.addWidget(self.radio_button_biosphere)
        controls_layout.addWidget(self.radio_button_technosphere)
        controls_layout.addWidget(self.scenario_label)
        controls_layout.addWidget(self.scenario_box)
        controls_layout.addWidget(self.filter_flows_label)
        controls_layout.addWidget(self.bio_categorisation_factor_group)
        controls_layout.addWidget(self.remove_zeros_checkbox)
        controls_layout.addStretch(1)
        self.add_tab_control_rows(controls_layout)
        self._set_flow_filter_visible(self.radio_button_biosphere.isChecked())
        self.table = InventoryTable(self.parent)
        self.table.table_name = lca_export_basename(self.parent.cs_name, "Inventory")
        self.layout.addWidget(self.table, 1)

        self.add_tab_footer(has_plot=False, has_table=True)
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
                self._on_scenario_index_changed
            )

    @QtCore.Slot(QtWidgets.QRadioButton, name="addCategorisationFactorFilter")
    def add_categorisation_factor_filter(self, index: int):
        if index == 1:
            self.categorisation_filter_with_flows = False
            self.categorisation_factor_state = False
        elif index == 2:
            self.categorisation_filter_with_flows = True
            self.categorisation_factor_state = True
        else:
            self.categorisation_filter_with_flows = None
            self.categorisation_factor_state = None
        self.update_table()
        self.old_categorisation_factor_state = self.categorisation_factor_state

    def _set_flow_filter_visible(self, visible: bool) -> None:
        self.filter_flows_label.setVisible(visible)
        self.bio_categorisation_factor_group.setVisible(visible)

    @QtCore.Slot(QtWidgets.QRadioButton, name="toggleCategorisationFactorFilterButtons")
    def toggle_categorisation_factor_filter_buttons(self, bttn: QtWidgets.QRadioButton):
        if bttn.text() == "Biosphere flows":
            self._set_flow_filter_visible(True)
        else:
            self._set_flow_filter_visible(False)
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
        self._set_flow_filter_visible(toggled)
        if not toggled:
            self.categorisation_factor_state = None
        self._update_inventory_export_names()
        self.update_table()

    def _update_inventory_export_names(self) -> None:
        inventory = (
            "biosphere" if self.radio_button_biosphere.isChecked() else "technosphere"
        )
        fields = [self.parent.cs_name, "Inventory", inventory]
        if self.has_scenarios:
            scenario_index = max(self.scenario_box.currentIndex(), 0)
            scenario_names = self.get_scenario_labels()
            if scenario_names and 0 <= scenario_index < len(scenario_names):
                fields.append(scenario_names[scenario_index])
        if inventory == "biosphere":
            filter_index = self.bio_categorisation_factor_group.currentIndex()
            if filter_index > 0:
                fields.append(export_name_slug(self._CF_FILTER_OPTIONS[filter_index][0]))
        if self.remove_zero_state:
            fields.append("no_zeros")
        self.table.table_name = lca_export_basename(*fields)

    @QtCore.Slot(int, name="inventoryScenarioIndexChanged")
    def _on_scenario_index_changed(self, index: int) -> None:
        """Switch superstructure matrices when this tab's scenario changes."""
        mlca = self.parent.mlca
        if hasattr(mlca, "set_scenario") and getattr(mlca, "current", None) != index:
            mlca.set_scenario(index)
        super()._on_scenario_index_changed(index)

    def configure_scenario(self):
        """Allow scenarios options to be visible when used."""
        super().configure_scenario()
        self.scenario_label.setVisible(self.has_scenarios)
        self._set_flow_filter_visible(self.radio_button_biosphere.isChecked())

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
        self._update_inventory_export_names()

    def clear_tables(self) -> None:
        """Set the biosphere and technosphere to None."""
        self.df_biosphere, self.df_technosphere = None, None

    def _update_table(self, table: pd.DataFrame, drop: tuple = ("code", "id")):
        """Update the table."""
        self.table.model.sync((table.drop(list(drop), axis=1)).reset_index(drop=True))


class LCAResultsTab(NewAnalysisTab):
    """LCIA results landing tab: grouped bar chart (default) or table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.df = None
        self.overview_data = None
        self.relative = False
        self.flip_groups = False
        self.horizontal_bars = False
        self.full_labels = False

        self.horizontal_checkbox = QtWidgets.QCheckBox("Horizontal")
        self.horizontal_checkbox.setToolTip(
            "Draw bar charts horizontally (default is vertical)"
        )
        self.horizontal_checkbox.setChecked(self.horizontal_bars)

        self.full_labels_checkbox = QtWidgets.QCheckBox("Full labels")
        self.full_labels_checkbox.setToolTip(FULL_LABELS_TOOLTIP)
        self.full_labels_checkbox.setChecked(self.full_labels)

        self.relativity = Relativity(
            QtWidgets.QRadioButton("Relative"),
            QtWidgets.QRadioButton("Absolute"),
        )
        self.relativity.absolute.setChecked(True)
        self.relativity_group = QtWidgets.QButtonGroup(self)
        self.relativity_group.addButton(self.relativity.relative)
        self.relativity_group.addButton(self.relativity.absolute)

        self.compare_label = QtWidgets.QLabel("Compare:")
        self.compare_switch = widgets.LCAscoresSwitchComboBox(self)
        self.method_label = QtWidgets.QLabel("Impact Category:")
        self.method_box = SmallComboBox(self)
        self.scenario_label = QtWidgets.QLabel("Scenario:")
        self.flip_groups_checkbox = QtWidgets.QCheckBox("Flip groups")
        self.flip_groups_checkbox.setToolTip(
            "Swap what is shown on the x-axis (groups) versus in the legend (series)"
        )
        self._selectors_separator = vertical_line()

        self.view_plot = QtWidgets.QRadioButton("Plot")
        self.view_table = QtWidgets.QRadioButton("Table")
        self.view_plot.setChecked(True)
        self._view_group = QtWidgets.QButtonGroup(self)
        self._view_group.addButton(self.view_plot, 0)
        self._view_group.addButton(self.view_table, 1)

        basename = lca_export_basename(self.parent.cs_name, "LCA scores")
        self.overview_plot = LCIAResultsOverviewPlot(self)
        self.overview_plot.plot_name = basename
        self.table = LCAResultsTable(self.parent)
        self.table.table_name = basename
        self.plot = self.overview_plot

        self.add_tab_header("LCA scores")
        self.add_tab_control_rows(
            self._build_compare_row(),
            self._build_view_options_row(),
        )
        self.layout.addWidget(self.populate_tab_body(), 1)
        self.table.hide()
        self.add_tab_footer(has_plot=True, has_table=True)

        self._configure_compare_modes()
        self.connect_signals()
        self._update_selector_visibility()
        self._update_export_names()

    def _update_export_names(self) -> None:
        """Set plot/table export basenames from the current view options."""
        mode = self._compare_mode()
        fields = [
            self.parent.cs_name,
            "LCA scores",
            lcia_compare_export_slug(mode),
            relativity_export_slug(relative=self.relative),
        ]
        flip = flip_export_slug(flipped=self.flip_groups and compare_mode_supports_flip(mode))
        if flip:
            fields.append(flip)
        scenario_index = max(self.scenario_box.currentIndex(), 0)
        method_index = self.method_box.currentIndex()
        if mode in (
            LCIACompareMode.REFERENCE_FLOWS,
            LCIACompareMode.FLOWS_X_SCENARIOS,
        ):
            methods = self.parent.mlca.methods
            if 0 <= method_index < len(methods):
                fields.append(methods[method_index])
        if self.has_scenarios and mode in (
            LCIACompareMode.REFERENCE_FLOWS,
            LCIACompareMode.FLOWS_X_METHODS,
        ):
            scenario_names = self.get_scenario_labels()
            if scenario_names and 0 <= scenario_index < len(scenario_names):
                fields.append(scenario_names[scenario_index])
        name = lca_export_basename(*fields)
        self.overview_plot.plot_name = name
        self.table.table_name = name

    def _build_compare_row(self) -> QtWidgets.QHBoxLayout:
        compare_row = lca_tab_control_row()
        compare_row.addWidget(self.compare_label)
        compare_row.addWidget(self.compare_switch)
        compare_row.addWidget(self._selectors_separator)
        compare_row.addWidget(self.method_label)
        compare_row.addWidget(self.method_box)
        compare_row.addWidget(self.scenario_label)
        compare_row.addWidget(self.scenario_box)
        compare_row.addWidget(self.flip_groups_checkbox)
        compare_row.addStretch()
        return compare_row

    def _build_view_options_row(self) -> QtWidgets.QHBoxLayout:
        options_row = lca_tab_control_row()
        options_row.addWidget(self.view_plot)
        options_row.addWidget(self.view_table)
        options_row.addWidget(vertical_line())
        self._append_plot_options_widgets(options_row)
        return options_row

    def _compare_mode(self) -> LCIACompareMode:
        return lcia_compare_mode_from_label(self.compare_switch.currentText())

    def _configure_compare_modes(self) -> None:
        modes = available_compare_modes(self.parent.mlca, self.has_scenarios)
        self.compare_switch.configure(lcia_compare_labels_for_modes(modes))

    def _update_selector_visibility(self) -> None:
        mode = self._compare_mode()
        show_method = mode in (
            LCIACompareMode.REFERENCE_FLOWS,
            LCIACompareMode.FLOWS_X_SCENARIOS,
        )
        self.method_label.setHidden(not show_method)
        self.method_box.setHidden(not show_method)
        show_scenario = self.has_scenarios and mode in (
            LCIACompareMode.REFERENCE_FLOWS,
            LCIACompareMode.FLOWS_X_METHODS,
        )
        self.scenario_label.setHidden(not show_scenario)
        self.scenario_box.setHidden(not show_scenario)
        show_flip = compare_mode_supports_flip(mode)
        self.flip_groups_checkbox.setVisible(show_flip)
        self.flip_groups = (
            self.flip_groups_checkbox.isChecked() if show_flip else False
        )
        selector_widgets = (
            self.method_label,
            self.method_box,
            self.scenario_label,
            self.scenario_box,
            self.flip_groups_checkbox,
        )
        self._selectors_separator.setVisible(
            any(not widget.isHidden() for widget in selector_widgets)
        )

    def connect_signals(self):
        self.compare_switch.currentIndexChanged.connect(self._on_compare_changed)
        self.method_box.currentIndexChanged.connect(self.update_tab)
        if self.has_scenarios:
            self.scenario_box.currentIndexChanged.connect(
                self._on_scenario_index_changed
            )
        self._view_group.buttonClicked.connect(self._on_view_changed)
        self.relativity.relative.toggled.connect(self.relativity_check)
        self.flip_groups_checkbox.toggled.connect(self._flip_groups_check)
        self.horizontal_checkbox.toggled.connect(self._horizontal_bars_check)

    @QtCore.Slot(bool, name="flipGroupsToggled")
    def _flip_groups_check(self, checked: bool):
        self.flip_groups = checked
        self.update_tab()

    def _on_compare_changed(self):
        self._update_selector_visibility()
        self.update_tab()

    @QtCore.Slot(bool, name="lcaScoresRelativeToggled")
    def relativity_check(self, checked: bool):
        self.relative = checked
        self.update_tab()

    def _on_view_changed(self):
        self.overview_plot.setVisible(self.view_plot.isChecked())
        self.table.setVisible(self.view_table.isChecked())
        if self.view_plot.isChecked():
            self.update_plot()
        if self.view_table.isChecked():
            self.update_table()

    def configure_scenario(self):
        super().configure_scenario()
        self._update_selector_visibility()

    def build_export(
        self, has_table: bool = True, has_plot: bool = True
    ) -> QtWidgets.QHBoxLayout:
        layout = super().build_export(has_table, has_plot)
        if self.has_scenarios:
            stretch = layout.takeAt(layout.count() - 1)
            exp_layout = QtWidgets.QHBoxLayout()
            exp_layout.addWidget(QtWidgets.QLabel("Export all data"))
            csv_btn = QtWidgets.QPushButton(".csv")
            csv_btn.clicked.connect(self.parent.generate_lcia_scenario_csv)
            excel_btn = QtWidgets.QPushButton("Excel")
            excel_btn.clicked.connect(self.parent.generate_lcia_scenario_excel)
            exp_layout.addWidget(csv_btn)
            exp_layout.addWidget(excel_btn)
            layout.addWidget(vertical_line())
            layout.addLayout(exp_layout)
            layout.addSpacerItem(stretch)
        return layout

    def update_tab(self):
        self.update_combobox(
            self.method_box, [str(m) for m in self.parent.mlca.methods]
        )
        scenario_index = max(self.scenario_box.currentIndex(), 0)
        self.overview_data = build_lcia_overview(
            self.parent.mlca,
            self.parent.contributions,
            compare=self._compare_mode(),
            relative=self.relative,
            scenario_index=scenario_index,
            method_index=self.method_box.currentIndex(),
            flip_groups=self.flip_groups,
        )
        self.df = self.overview_data.table_df
        self._update_export_names()
        if self._plot_view_selected():
            self.update_plot()
        # Keep table in sync for export even when the plot view is shown.
        self.update_table()

    def _plot_view_selected(self) -> bool:
        return self.view_plot.isChecked()

    def _table_view_selected(self) -> bool:
        return self.view_table.isChecked()

    def update_plot(self):
        self.overview_plot.plot(
            self.overview_data,
            relative=self.relative,
            horizontal=self.horizontal_bars,
        )

    def update_table(self):
        if self.df is not None:
            super().update_table(self.df)


class ContributionTab(NewAnalysisTab):
    """Parent class for any 'XXX Contributions' sub-tab."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.cutoff_menu = widgets.CutoffMenu(self, cutoff_value=0.05)
        self.combobox_menu = Combobox(
            func=SmallComboBox(self),
            func_label=QtWidgets.QLabel("Reference Flow:"),
            method=SmallComboBox(self),
            method_label=QtWidgets.QLabel("Impact Category:"),
            agg=SmallComboBox(self),
            agg_label=QtWidgets.QLabel("Aggregate by:"),
            scenario=self.scenario_box,
            scenario_label=QtWidgets.QLabel("Scenario:"),
        )
        self.switch_label = QtWidgets.QLabel("Compare:")
        self.switches = widgets.ContributionsSwitchComboBox(self)

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
        self._update_score_range_enabled()

        self.horizontal_bars = False
        self.full_labels = False

        self.horizontal_checkbox = QtWidgets.QCheckBox("Horizontal")
        self.horizontal_checkbox.setToolTip(
            "Draw bar charts horizontally (default is vertical)"
        )
        self.horizontal_checkbox.setChecked(self.horizontal_bars)

        self.full_labels_checkbox = QtWidgets.QCheckBox("Full labels")
        self.full_labels_checkbox.setToolTip(FULL_LABELS_TOOLTIP)
        self.full_labels_checkbox.setChecked(self.full_labels)

        self.df = None
        self.plot = ContributionPlot(self)
        self.table = ContributionTable(self)
        self.contribution_fn = None
        self.has_method, self.has_func = False, False
        self.unit = None

        self.has_been_opened = False

        self.explain_text = """
                <p>There are three ways of doing Contribtion Analysis in Activity Browser:</h4>
                <p>- <b>Elementary Flow (EF) Contributions</b></p>
                <p>- <b>Process Contributions</b></p>
                <p>- <b>First Tier (FT) Contributions</b></p>
                
                Detailed information on the different approaches provided in this <a href="https://github.com/LCA-ActivityBrowser/activity-browser/wiki/LCA-Results#contribution-analysis">wiki page</a> about the different approaches. 

                <p>You can manipulate the results in many ways with Activity Browser, read more on this <a href="https://github.com/LCA-ActivityBrowser/activity-browser/wiki/LCA-Results#manipulating-results">wiki page</a>
                about manipulating results. 
                """

    def assemble_contribution_tab_layout(
        self,
        title: str,
        *,
        has_method: bool = True,
        has_func: bool = False,
    ) -> None:
        """Header, two control rows, main body, and export footer."""
        self.add_tab_header(
            title,
            "Left click for help on Contribution Analysis Functions",
        )
        self.add_tab_control_rows(
            self.build_compare_row(has_method=has_method, has_func=has_func),
            self.build_view_options_row(),
        )
        self.layout.addWidget(self.populate_tab_body(), 1)
        self.add_tab_footer(has_plot=True, has_table=True)

    def set_filename(self, optional_fields: dict = None):
        """Given a dictionary of fields, put together a usable filename for the plot and table."""
        optional = optional_fields or {}
        fields = [
            self.parent.cs_name,
            contribution_tab_slug(self.contribution_fn),
            contribution_compare_export_slug(
                self.switches.currentIndex(), self.switches.indexes
            ),
            relativity_export_slug(
                relative=self.relative, total_range=self.total_range
            ),
        ]
        aggregator = optional.get("aggregator")
        if aggregator:
            fields.append(f"agg_{export_name_slug(aggregator)}")
        if optional.get("method") is not None:
            fields.append(optional["method"])
        if optional.get("functional_unit"):
            fields.append(optional["functional_unit"])
        scenario_index = optional.get("scenario")
        if scenario_index is not None and self.has_scenarios:
            scenario_names = self.get_scenario_labels()
            if scenario_names and 0 <= scenario_index < len(scenario_names):
                fields.append(scenario_names[scenario_index])

        filename = lca_export_basename(*fields)
        self.plot.plot_name, self.table.table_name = filename, filename

    def build_compare_row(
        self, has_method: bool = True, has_func: bool = False
    ) -> QtWidgets.QHBoxLayout:
        """Row 1: Compare and optional impact-category / scenario selectors."""
        return self.build_combobox(has_method=has_method, has_func=has_func)

    def build_view_options_row(self, invertable: bool = False) -> QtWidgets.QHBoxLayout:
        """Row 2: Plot/Table, then cut-off and other plot options."""
        self._setup_plot_table_widgets(invertable)
        row = lca_tab_control_row()
        row.addWidget(self.plot_table.plot)
        row.addWidget(self.plot_table.table)
        row.addWidget(vertical_line())
        self.cutoff_menu.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Preferred
        )
        row.addWidget(self.cutoff_menu)
        if invertable and self.plot_table.invert is not None:
            row.addWidget(vertical_line())
            row.addWidget(self.plot_table.invert)
        row.addWidget(vertical_line())
        self._append_plot_options_widgets(row)
        return row

    def build_combobox(
        self, has_method: bool = True, has_func: bool = False
    ) -> QtWidgets.QHBoxLayout:
        """Construct a horizontal layout for picking and choosing what data to show and how."""
        menu = lca_tab_control_row()
        # Populate the drop-down boxes with their relevant values.
        self.combobox_menu.func.addItems(list(self.parent.mlca.fu_labels.values()))
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
        functional_unit = str(self.combobox_menu.func.currentIndex())
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
        self.unit = contribution_axis_unit(
            compare_fields.get("method"), relative=self.relative, total_range=self.total_range
        )
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
        self.horizontal_checkbox.toggled.connect(self._horizontal_bars_check)

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
        self.space_check()
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
        Compare row, then Plot/Table, cut-off, Relative/Absolute, Score/Range, Horizontal
        Compare options button to change between 'Reference Flows' and 'Impact Categories'
        'Impact Category'/'Reference Flow' chooser with aggregation method
        Export options
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.assemble_contribution_tab_layout(
            "Elementary Flow Contributions",
            has_method=True,
            has_func=True,
        )

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
        Compare row, then Plot/Table, cut-off, Relative/Absolute, Score/Range, Horizontal
        Compare options button to change between 'Reference Flows' and 'Impact Categories'
        'Impact Category'/'Reference Flow' chooser with aggregation method
        Export options
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.assemble_contribution_tab_layout(
            "Process Contributions",
            has_method=True,
            has_func=True,
        )

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
    """First-tier (direct supplier) contributions tab.

    Not registered in :class:`LCAResultsPage` by default (see commented ``ft=`` slot).
    Calculation logic remains here for potential re-enablement; consider moving heavy
    logic to ``bwutils`` if this tab is restored.
    """

    def __init__(self, cs_name, parent=None):
        super().__init__(parent)

        self.cache = {"scores": {}, "ranges": {}}  # We cache the calculated data, as it can take some time to generate.
        # We cache the individual calculation results, as they are re-used in multiple views
        # e.g. FU1 x method1 x scenario1
        # may be seen in both 'Reference Flows' and 'Impact Categories', just with different axes.
        # we also cache scores/ranges, not for calculation speed, but to be able to easily convert for relative results
        self.caching = True  # set to False to disable caching for debug

        self.assemble_contribution_tab_layout(
            "First Tier Contributions",
            has_method=True,
            has_func=True,
        )

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
        return list(app.metadata.get_metadata([key], ["reference product", "name", "location", "unit"]).iloc[0]) + [key[0]]

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
                from activity_browser.bwutils.commontasks import get_method_label

                col_name = get_method_label(item, separator=" | ")
            elif compare == "Scenarios":
                col_name = item

            self.cache["scores"][col_name] = data["Score"]
            self.cache["ranges"][col_name] = data["Range"]
            d[col_name] = []

            all_data[i] = item, data, col_name

        if compare == "Impact Categories":
            self.unit = contribution_axis_unit(
                None, relative=self.relative, total_range=self.total_range
            )
        else:
            self.unit = contribution_axis_unit(
                self.parent.method_dict[self.combobox_menu.method.currentText()],
                relative=self.relative,
                total_range=self.total_range,
            )

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
            df[data_cols] = 100.0 * df[data_cols] / normalize

        return df

    def update_dataframe(self, *args, **kwargs):
        """Retrieve the product contributions."""

        compare = self.switches.currentText()

        all_data = self.get_data(compare)
        df = self.data_to_df(all_data, compare)
        return df


class MonteCarloTab(NewAnalysisTab):
    def __init__(self, parent=None):
        super(MonteCarloTab, self).__init__(parent)
        self.parent: LCAResultsSubTab = parent

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
        self.add_tab_header(
            "Monte Carlo Simulation",
            "Left click for help on Monte Carlo analysis",
        )
        self.scenario_label = QtWidgets.QLabel("Scenario:")
        self.include_tech = QtWidgets.QCheckBox("Technosphere", self)
        self.include_tech.setChecked(True)
        self.include_bio = QtWidgets.QCheckBox("Biosphere", self)
        self.include_bio.setChecked(True)
        self.include_cf = QtWidgets.QCheckBox("Characterization Factors", self)
        self.include_cf.setChecked(True)
        self.include_parameters = QtWidgets.QCheckBox("Parameters", self)
        self.include_parameters.setChecked(True)
        self.include_parameters.setToolTip(
            "Consider uncertainty distributions of parameters. "
            "This overrides distributions set on exchanges if these are parameterized."
        )
        self.label_include_uncertainty = QtWidgets.QLabel("Include uncertainty for:", self)
        self.label_include_uncertainty.setToolTip(
            "Which model elements use defined uncertainty distributions in this simulation."
        )

        self.add_MC_ui_elements()

        self.table = LCAResultsTable()
        mc_basename = lca_export_basename(self.parent.cs_name, "Monte Carlo")
        self.table.table_name = mc_basename
        self.plot = MonteCarloPlot(self)
        self.plot.plot_name = mc_basename

        self.add_tab_body_with_placeholder()
        self.export_widget = self.add_tab_footer(
            has_plot=True, has_table=True, wrapped=True
        )
        self.export_widget.hide()
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

        if self.has_scenarios:
            self.scenario_box.currentIndexChanged.connect(
                self._on_scenario_index_changed
            )

    def add_MC_ui_elements(self):
        # H-LAYOUT start simulation
        self.button_run = lca_run_button(self)
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

        self.hlayout_run = lca_tab_control_row()
        self.hlayout_run.addWidget(self.button_run)
        self.hlayout_run.addWidget(self.scenario_label)
        self.hlayout_run.addWidget(self.scenario_box)
        self.hlayout_run.addWidget(self.label_iterations)
        self.hlayout_run.addWidget(self.iterations)
        self.hlayout_run.addWidget(self.label_seed)
        self.hlayout_run.addWidget(self.seed)
        self.hlayout_run.addWidget(vertical_line())
        self.hlayout_run.addWidget(self.label_include_uncertainty)
        self.hlayout_run.addWidget(self.include_tech)
        self.hlayout_run.addWidget(self.include_bio)
        self.hlayout_run.addWidget(self.include_cf)
        self.hlayout_run.addWidget(self.include_parameters)
        self.hlayout_run.addStretch(1)
        self.add_tab_control_rows(self.hlayout_run)

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

        # method selection + plot/table (row 2, aligned with other LCA result tabs)
        self.full_labels = False
        self.full_labels_checkbox = QtWidgets.QCheckBox("Full labels")
        self.full_labels_checkbox.setToolTip(FULL_LABELS_TOOLTIP)
        self.full_labels_checkbox.setChecked(self.full_labels)

        self.label_methods = QtWidgets.QLabel("Impact Category:")
        self.combobox_methods = SmallComboBox(self)
        self._setup_plot_table_widgets(invertable=False)
        self.hlayout_row2 = lca_tab_control_row()
        self.hlayout_row2.addWidget(self.plot_table.plot)
        self.hlayout_row2.addWidget(self.plot_table.table)
        self.hlayout_row2.addWidget(self.label_methods)
        self.hlayout_row2.addWidget(self.combobox_methods)
        self.hlayout_row2.addWidget(vertical_line())
        self._append_plot_options_widgets(self.hlayout_row2)
        self.view_options_widget = QtWidgets.QWidget()
        self.view_options_widget.setLayout(self.hlayout_row2)
        self.view_options_widget.hide()
        self.layout.addWidget(self.view_options_widget)

    @QtCore.Slot(name="calculateMcLca")
    def calculate_mc_lca(self):
        self.view_options_widget.hide()
        self.set_tab_body_visible(False)
        self.export_widget.hide()

        iterations = int(self.iterations.text())
        seed = None
        if self.seed.text():
            logger.info(f"SEED: {self.seed.text()}")
            try:
                seed = int(self.seed.text())
            except ValueError as e:
                logger.error(
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
            app.signals.monte_carlo_finished.emit()
            self.update_mc()
        except (
            InvalidParamsError
        ) as e:  # This can occur if uncertainty data is missing or otherwise broken
            # print(e)
            logger.error(e)
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

    @QtCore.Slot(int, name="mcScenarioIndexChanged")
    def _on_scenario_index_changed(self, index: int) -> None:
        """Scenario only affects export names after MC has been run."""
        if self.df is not None:
            self.update_mc()

    def update_tab(self):
        self.update_combobox(
            self.combobox_methods, [str(m) for m in self.parent.mc.methods]
        )
        # self.update_combobox(self.combobox_methods, [str(m) for m in self.parent.mct.mc.methods])

    @QtCore.Slot(bool, name="mcFullLabelsToggled")
    def _full_labels_check(self, checked: bool) -> None:
        self.full_labels = checked
        if self.df is not None:
            self.update_mc()

    def update_mc(self, cs_name=None):
        self.view_options_widget.show()
        self.set_tab_body_visible(True)
        self.export_widget.show()

        method_index = self.combobox_methods.currentIndex()
        method = self.parent.mc.methods[method_index]

        self.df = self.parent.mc.get_results_dataframe(method=method)

        self.update_table()
        if self._plot_view_selected():
            self.update_plot(method=method)
        self.space_check()
        fields = [self.parent.cs_name, "Monte Carlo", method]
        if self.has_scenarios:
            scenario_index = max(self.scenario_box.currentIndex(), 0)
            scenario_names = self.get_scenario_labels()
            if scenario_names and 0 <= scenario_index < len(scenario_names):
                fields.append(scenario_names[scenario_index])
        filename = lca_export_basename(*fields)
        self.plot.plot_name, self.table.table_name = filename, filename

    def update_plot(self, method):
        super().update_plot(self.df, method=method)
        self.space_check()

    def update_table(self):
        super().update_table(self.df)
        self.space_check()


class GSATab(NewAnalysisTab):
    """Global sensitivity analysis tab (requires a completed Monte Carlo run)."""

    def __init__(self, parent=None):
        super(GSATab, self).__init__(parent)
        self.parent = parent

        self.GSA = GlobalSensitivityAnalysis(self.parent.mc)

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
             <p>The plot shows the top inputs by delta (SALib) with confidence intervals (± delta_conf), coloured by type.</p>
        """
        self.add_tab_header(
            "Global Sensitivity Analysis",
            "Left click for help on Global Sensitivity Analysis",
        )
        self.scenario_box = None

        self.add_GSA_ui_elements()

        self.df = None
        self.table = LCAResultsTable()
        gsa_basename = lca_export_basename(self.parent.cs_name, "GSA")
        self.table.table_name = gsa_basename
        self.plot = GSAPlot(self)
        self.plot.plot_name = gsa_basename
        self.add_tab_body_with_placeholder()
        self.table.hide()
        self.plot.hide()

        self.export_widget = self.add_tab_footer(
            has_plot=True, has_table=False, wrapped=True
        )
        self.export_widget.hide()
        self.connect_signals()

    def connect_signals(self):
        self.button_run.clicked.connect(self.calculate_gsa)
        self.max_rows.editingFinished.connect(self._on_max_rows_changed)
        self.horizontal_checkbox.toggled.connect(self._horizontal_bars_check)
        self.full_labels_checkbox.toggled.connect(self._full_labels_check)
        app.signals.monte_carlo_finished.connect(self.monte_carlo_finished)

    def add_GSA_ui_elements(self):
        self.horizontal_bars = False
        self.full_labels = False

        self.horizontal_checkbox = QtWidgets.QCheckBox("Horizontal")
        self.horizontal_checkbox.setToolTip(
            "Draw bar charts horizontally (default is vertical)"
        )
        self.horizontal_checkbox.setChecked(self.horizontal_bars)

        self.full_labels_checkbox = QtWidgets.QCheckBox("Full labels")
        self.full_labels_checkbox.setToolTip(FULL_LABELS_TOOLTIP)
        self.full_labels_checkbox.setChecked(self.full_labels)

        # H-LAYOUT SETTINGS ROW 1

        # run button
        self.button_run = lca_run_button(self)
        self.button_run.setEnabled(False)

        # reference flow selection
        self.label_fu = QtWidgets.QLabel("Reference Flow:")
        self.combobox_fu = SmallComboBox(self)

        # method selection
        self.label_methods = QtWidgets.QLabel("Impact Category:")
        self.combobox_methods = SmallComboBox(self)

        self.label_cutoffs = QtWidgets.QLabel("Cutoffs:")
        self.label_technosphere = QtWidgets.QLabel("Technosphere")
        self.cutoff_technosphere = QtWidgets.QLineEdit("0.01")
        self.cutoff_technosphere.setFixedWidth(40)
        self.cutoff_technosphere.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 5))
        self.label_biosphere = QtWidgets.QLabel("Biosphere")
        self.cutoff_biosphere = QtWidgets.QLineEdit("0.01")
        self.cutoff_biosphere.setFixedWidth(40)
        self.cutoff_biosphere.setValidator(QtGui.QDoubleValidator(0.0, 1.0, 5))

        self.label_max_rows = QtWidgets.QLabel("Max rows shown:")
        self.label_max_rows.setToolTip(
            "Maximum number of inputs in the plot, ranked by delta (table shows all rows)."
        )
        self.max_rows = QtWidgets.QLineEdit("10")
        self.max_rows.setFixedWidth(40)
        self.max_rows.setValidator(QtGui.QIntValidator(1, 9999))

        self.hlayout_row1 = lca_tab_control_row()
        self.hlayout_row1.addWidget(self.button_run)
        self.hlayout_row1.addWidget(self.label_fu)
        self.hlayout_row1.addWidget(self.combobox_fu)
        self.hlayout_row1.addWidget(self.label_methods)
        self.hlayout_row1.addWidget(self.combobox_methods)
        self.hlayout_row1.addWidget(vertical_line())
        self.hlayout_row1.addWidget(self.label_cutoffs)
        self.hlayout_row1.addWidget(self.label_technosphere)
        self.hlayout_row1.addWidget(self.cutoff_technosphere)
        self.hlayout_row1.addWidget(self.label_biosphere)
        self.hlayout_row1.addWidget(self.cutoff_biosphere)
        self.hlayout_row1.addStretch(1)

        self.hlayout_row2 = lca_tab_control_row()
        self._setup_plot_table_widgets(invertable=False)
        self.hlayout_row2.addWidget(self.plot_table.plot)
        self.hlayout_row2.addWidget(self.plot_table.table)
        self.hlayout_row2.addWidget(vertical_line())
        self.hlayout_row2.addWidget(self.label_max_rows)
        self.hlayout_row2.addWidget(self.max_rows)
        self.hlayout_row2.addWidget(vertical_line())
        self.hlayout_row2.addWidget(self.horizontal_checkbox)
        self.hlayout_row2.addWidget(self.full_labels_checkbox)
        self.hlayout_row2.addStretch(1)
        self._set_max_rows_controls_enabled(True)

        # OVERALL LAYOUT OF SETTINGS
        self.layout_settings = lca_tab_controls_section(
            self.hlayout_row1, self.hlayout_row2
        )
        self.widget_settings = QtWidgets.QWidget()
        self.widget_settings.setLayout(self.layout_settings)

        # add to GSA layout
        self.label_monte_carlo_first = QtWidgets.QLabel(
            "You need to run a Monte Carlo Simulation first."
        )
        self.layout.addWidget(self.label_monte_carlo_first)
        self.layout.addWidget(self.widget_settings)

        self.widget_settings.hide()

    def update_tab(self):
        self.update_combobox(
            self.combobox_methods, [str(m) for m in self.parent.mc.methods]
        )
        self.update_combobox(
            self.combobox_fu, list(self.parent.mlca.fu_labels.values())
        )
        super().update_tab()

    def monte_carlo_finished(self):
        self.GSA.update_mc(self.parent.mc)
        self.button_run.setEnabled(True)
        self.widget_settings.show()
        self.label_monte_carlo_first.hide()

    def calculate_gsa(self):
        act_number = self.combobox_fu.currentIndex()
        method_number = self.combobox_methods.currentIndex()
        cutoff_technosphere = float(self.cutoff_technosphere.text())
        cutoff_biosphere = float(self.cutoff_biosphere.text())

        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            self.GSA.perform_GSA(
                act_number=act_number,
                method_number=method_number,
                cutoff_technosphere=cutoff_technosphere,
                cutoff_biosphere=cutoff_biosphere,
            )
        except Exception as e:
            import traceback
            traceback.print_tb(e.__traceback__)
            logger.error(e)
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

    def _set_max_rows_controls_enabled(self, plot_mode: bool) -> None:
        self.label_max_rows.setEnabled(plot_mode)
        self.max_rows.setEnabled(plot_mode)

    @QtCore.Slot(QtWidgets.QAbstractButton)
    def _on_plot_table_view_changed(self, button: QtWidgets.QAbstractButton) -> None:
        self._set_max_rows_controls_enabled(self._plot_view_selected())
        super()._on_plot_table_view_changed(button)

    def _gsa_max_rows(self) -> int:
        try:
            return max(1, int(self.max_rows.text()))
        except (TypeError, ValueError):
            return 10

    def _on_max_rows_changed(self):
        if self.df is not None and not self.df.empty:
            basename = self._gsa_export_basename()
            self.plot.plot_name = basename
            self.table.table_name = basename
        if self.df is not None and self._plot_view_selected():
            self.update_plot()

    def _gsa_export_basename(self) -> str:
        return lca_export_basename(self.GSA.get_save_name(), f"top{self._gsa_max_rows()}")

    @QtCore.Slot(bool, name="gsaHorizontalBarsToggled")
    def _horizontal_bars_check(self, checked: bool) -> None:
        self.horizontal_bars = checked
        if self.df is not None and not self.df.empty:
            basename = self._gsa_export_basename()
            self.plot.plot_name = basename
            self.table.table_name = basename
        if self.df is not None and self._plot_view_selected():
            self.update_plot()

    def update_gsa(self):
        self.df = getattr(self.GSA, "df_final", None)
        if self.df is None or self.df.empty:
            return

        basename = self._gsa_export_basename()
        self.table.table_name = basename
        self.plot.plot_name = basename
        self.set_tab_body_visible(True)
        self.export_widget.show()
        self.space_check()
        if self._plot_view_selected():
            self.update_plot()
        self.update_table()

    def export_gsa_data(self, *, as_csv: bool = False):
        if self.df is None or self.df.empty:
            QtWidgets.QMessageBox.warning(
                self, "No GSA results", "Run GSA first before exporting data."
            )
            return
        default_name = self._gsa_export_basename()
        if as_csv:
            default_name = f"{default_name}.csv"
            file_filter = self.table.CSV_FILTER
            caption = "Export GSA data (CSV)"
        else:
            file_filter = self.table.EXCEL_FILTER
            caption = "Export GSA data (Excel)"
        filepath = self.table.savefilepath(
            default_name,
            caption=caption,
            file_filter=file_filter,
        )
        if not filepath:
            return
        filepath = str(filepath)
        if as_csv:
            if not filepath.endswith(".csv"):
                filepath = f"{filepath}.csv"
        elif not filepath.endswith(".xlsx"):
            filepath = f"{filepath}.xlsx"
        try:
            if as_csv:
                self.GSA.export_GSA_all_csv(filepath)
            else:
                self.GSA.export_GSA_all(filepath)
        except Exception as e:
            logger.exception(e)
            QtWidgets.QMessageBox.warning(self, "Export failed", str(e))
            return

    def update_plot(self, *args, **kwargs):
        if self.df is None or self.df.empty:
            return
        super().update_plot(self.df, max_rows=self._gsa_max_rows())

    def update_table(self):
        if self.df is not None:
            super().update_table(self.df)

    def build_export(
        self, has_table: bool = True, has_plot: bool = True
    ) -> QtWidgets.QHBoxLayout:
        """Plot export, copy-results, and full GSA data export (inputs + outputs)."""
        export_layout = super().build_export(has_table=False, has_plot=has_plot)
        stretch = export_layout.takeAt(export_layout.count() - 1)

        if has_plot:
            export_layout.addWidget(vertical_line())

        copy_btn = QtWidgets.QPushButton("Copy")
        copy_btn.setToolTip("Copy the GSA results table shown in the UI to the clipboard.")
        copy_btn.clicked.connect(self._export_table_copy)
        export_layout.addWidget(copy_btn)

        export_layout.addWidget(vertical_line())
        gsa_data_layout = QtWidgets.QHBoxLayout()
        gsa_data_layout.addWidget(QtWidgets.QLabel("Export GSA data:"))
        export_gsa_csv_btn = QtWidgets.QPushButton(".csv")
        export_gsa_csv_btn.setToolTip(
            "Save GSA results and MC inputs as two CSV files (*_output.csv and *_input.csv)"
        )
        export_gsa_csv_btn.clicked.connect(lambda: self.export_gsa_data(as_csv=True))
        gsa_data_layout.addWidget(export_gsa_csv_btn)
        export_gsa_excel_btn = QtWidgets.QPushButton("Excel")
        export_gsa_excel_btn.setToolTip(
            "Save GSA results and MC inputs to one Excel file (GSA output and GSA input sheets)."
        )
        export_gsa_excel_btn.clicked.connect(self.export_gsa_data)
        gsa_data_layout.addWidget(export_gsa_excel_btn)
        export_layout.addLayout(gsa_data_layout)

        if stretch is not None:
            export_layout.addItem(stretch)
        return export_layout


class MonteCarloWorkerThread(QtCore.QThread):
    """Background worker for Monte Carlo (reserved for future use).

    Not used today: MC runs synchronously in the UI thread because pyparadiso
    does not safely support parallel solves on Windows. Kept as a reference if
    that limitation is lifted.
    """

    def __init__(self):
        super().__init__()
        self.mc = None
        self.iterations = 20

    def set_mc(self, mc, iterations=20):
        self.mc = mc
        self.iterations = iterations

    def run(self):
        logger.info(f"Starting new Worker Thread. Iterations: {self.iterations}")
        self.mc.calculate(iterations=self.iterations)
        logger.info("in thread {}".format(QtCore.QThread.currentThread()))
        # Legacy hook; live code uses app.signals.monte_carlo_finished instead.
        if hasattr(app.signals, "monte_carlo_ready"):
            app.signals.monte_carlo_ready.emit(self.mc.cs_name)


worker_thread = MonteCarloWorkerThread()
