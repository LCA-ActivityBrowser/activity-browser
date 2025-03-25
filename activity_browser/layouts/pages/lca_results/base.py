from collections import namedtuple

from qtpy import QtWidgets

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import actions, bwutils, settings
from activity_browser.ui import widgets, icons

ExportPlot = namedtuple("export_plot", ("label", "png", "svg"))
ExportTable = namedtuple("export_table", ("label", "copy", "csv", "excel"))


class BaseLCATab(QtWidgets.QWidget):
    """Parent class around which all sub-tabs are built."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.has_scenarios = self.parent().has_scenarios

        self.scenario_box = QtWidgets.QComboBox()
        self.pt_layout = QtWidgets.QVBoxLayout()
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

    def build_main_space(self, invertable: bool = False) -> QtWidgets.QScrollArea:
        """Assemble main space where plots, tables and relevant options are shown."""
        space = QScrollArea()
        widget = QWidget()
        self.pt_layout.setAlignment(QtCore.Qt.AlignTop)
        widget.setLayout(self.pt_layout)
        space.setWidget(widget)
        space.setWidgetResizable(True)

        # Option switches
        self.plot_table = PlotTableCheck(QCheckBox("Plot"), QCheckBox("Table"), None)
        if invertable:
            self.plot_table = PlotTableCheck(
                QCheckBox("Plot"), QCheckBox("Table"), QCheckBox("Invert")
            )
            self.plot_table.invert.setChecked(False)
            self.plot_table.invert.stateChanged.connect(self.invert_plot)
        self.plot_table.plot.setChecked(True)
        self.plot_table.table.setChecked(True)
        self.plot_table.table.stateChanged.connect(self.space_check)
        self.plot_table.plot.stateChanged.connect(self.space_check)

        # Assemble option row
        row = QHBoxLayout()
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

    def invert_plot(self):
        self.plot_inversion = self.plot_table.invert.isChecked()
        self.space_check()
        self.update_plot()

    def space_check(self):
        """Show graph and/or table, whichever is selected.

        Can also hide both, if you want to do that.
        """
        self.table.setVisible(self.plot_table.table.isChecked())
        self.plot.setVisible(self.plot_table.plot.isChecked())

    def relativity_check(self, checked: bool):
        """Check if the relative or absolute option is selected."""
        self.relative = checked
        self.update_tab()

    def total_check(self, checked: bool):
        """Check if the relative or absolute option is selected."""
        self.total_range = checked
        self.update_tab()

    def score_mrk_check(self, checked: bool):
        self.score_marker = checked

        settings.project_settings.settings["analysis_tab"] = settings.project_settings.settings.get("analysis_tab", {})
        settings.project_settings.settings["analysis_tab"][f"{self.__class__.__name__}score_marker_enabled"] = checked
        settings.project_settings.write_settings()

        self.update_tab()

    def get_scenario_labels(self) -> list[str]:
        """Get scenario labels if scenarios are used."""
        return self.parent().mlca.scenario_names if self.has_scenarios else []

    def configure_scenario(self):
        """Determine if scenario Qt widgets are visible or not and retrieve
        scenario labels for the selection drop-down box.
        """
        if self.scenario_box:
            self.scenario_box.setVisible(self.has_scenarios)
            self.update_combobox(self.scenario_box, self.get_scenario_labels())

    @staticmethod
    def set_combobox_index(box: QtWidgets.QComboBox, index: int) -> None:
        """Update the index on the given QComboBox without sending a signal."""
        box.blockSignals(True)
        box.setCurrentIndex(index)
        box.blockSignals(False)

    @staticmethod
    def update_combobox(box: QtWidgets.QComboBox, labels: list[str]) -> None:
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

    def build_export(self, has_table: bool = True, has_plot: bool = True) -> QtWidgets.QHBoxLayout:
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
            export_menu.addWidget(widgets.ABVLine(self))

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