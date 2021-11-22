# -*- coding: utf-8 -*-
import json
import math
import os

import brightway2 as bw
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from PySide2 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel
from PySide2.QtCore import QObject, Slot
from PySide2.QtWidgets import QMenu, QAction
from bokeh.embed import file_html
from bokeh.io import export_png, export_svg
from bokeh.models import ColumnDataSource, HoverTool, CustomJS, Span, WheelZoomTool
from bokeh.palettes import turbo
from bokeh.plotting import figure as bokeh_figure
from bokeh.transform import dodge
from bw2data.filesystem import safe_filename
from jinja2 import Template
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from numpy import mgrid

from activity_browser.ui.web import webutils
from .. import utils
from ..bwutils.commontasks import wrap_text, wrap_text_by_separator
from ..settings import ab_settings


# todo: sizing of the figures needs to be improved and systematized...


class Plot(QtWidgets.QWidget):
    ALL_FILTER = "All Files (*.*)"
    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    def __init__(self, parent=None):
        super().__init__(parent)
        # create figure, canvas, and axis
        # self.figure = Figure(tight_layout=True)
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)  # create an axis
        self.plot_name = 'Figure'

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()

    def plot(self, *args, **kwargs):
        raise NotImplementedError

    def reset_plot(self) -> None:
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)

    def get_canvas_size_in_inches(self):
        # print("Canvas size:", self.canvas.get_width_height())
        return tuple(x / self.figure.dpi for x in self.canvas.get_width_height())

    def savefilepath(self, default_file_name: str, file_filter: str = ALL_FILTER):
        default = default_file_name or "LCA results"
        safe_name = safe_filename(default, add_hash=False)
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Choose location to save lca results',
            dir=os.path.join(ab_settings.data_dir, safe_name),
            filter=file_filter,
        )
        return filepath

    def to_png(self):
        """ Export to .png format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, file_filter=self.PNG_FILTER)
        if filepath:
            if not filepath.endswith('.png'):
                filepath += '.png'
            self.figure.savefig(filepath)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, file_filter=self.SVG_FILTER)
        if filepath:
            if not filepath.endswith('.svg'):
                filepath += '.svg'
            self.figure.savefig(filepath)


class LCAResultsPlot(Plot):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'LCA heatmap'

    def plot(self, df: pd.DataFrame):
        """ Plot a heatmap grid of the different impact categories and reference flows. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.reset_plot()

        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if "amount" in dfp.columns:
            dfp.drop(["amount"], axis=1, inplace=True)  # Drop the 'amount' col
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        # avoid figures getting too large horizontally
        dfp.index = [wrap_text(i, max_length=40) for i in dfp.index]
        dfp.columns = [wrap_text(i, max_length=20) for i in dfp.columns]

        sns.heatmap(
            dfp, ax=self.ax, cmap="Blues", annot=True, linewidths=0.05,
            annot_kws={"size": 11 if dfp.shape[1] <= 8 else 9,
                       "rotation": 0 if dfp.shape[1] <= 8 else 60}
        )
        self.ax.tick_params(labelsize=8)
        if dfp.shape[1] > 5:
            self.ax.set_xticklabels(self.ax.get_xticklabels(), rotation="vertical")
        self.ax.set_yticklabels(self.ax.get_yticklabels(), rotation="horizontal")

        # refresh canvas
        size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[0] * 0.55)
        self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])

        self.canvas.draw()


class BokehPlot(QtWidgets.QWidget):
    ALL_FILTER = "All Files (*.*)"
    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.figure = None
        self.plot_name = 'Figure'

        self.view = QtWebEngineWidgets.QWebEngineView()
        self.page = QtWebEngineWidgets.QWebEnginePage()
        self.view.setContentsMargins(0, 0, 0, 0)

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)

        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()

    def on_context_menu(self, *args, **kwargs):
        raise NotImplementedError

    def plot(self, *args, **kwargs):
        raise NotImplementedError

    def reset_plot(self) -> None:
        pass

    def save_file_path(self, default_file_name: str, file_filter: str = ALL_FILTER):
        default = default_file_name or "LCA results"
        safe_name = safe_filename(default, add_hash=False)
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption='Choose location to save lca results',
            dir=os.path.join(ab_settings.data_dir, safe_name),
            filter=file_filter,
        )
        return filepath

    def to_png(self):
        """ Export to .png format. """
        filepath = self.save_file_path(default_file_name=self.plot_name, file_filter=self.PNG_FILTER)
        if filepath:
            if not filepath.endswith('.png'):
                filepath += '.png'
            fig_width = self.figure.width + 500
            export_png(self.figure, filename=filepath, width=fig_width)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = self.save_file_path(default_file_name=self.plot_name, file_filter=self.SVG_FILTER)
        if filepath:
            if not filepath.endswith('.svg'):
                filepath += '.svg'
            fig_width = self.figure.width + 500
            self.figure.output_backend = "svg"
            export_svg(self.figure, filename=filepath, width=fig_width)
            self.figure.output_backend = "canvas"


class LCAResultsBarChart(BokehPlot):
    """" Generate a bar chart comparing the absolute LCA scores of the products """
    BAR_HEIGHT = 0.6

    def on_context_menu(self, *args, **kwargs):
        raise NotImplementedError

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'LCA scores'

    def plot(self, df: pd.DataFrame, method: tuple, labels: list):
        df.index = pd.Index(labels)  # Replace index of tuples
        show_legend = df.shape[1] != 1  # Do not show the legend for 1 column
        df = df[::-1]

        if show_legend:
            column_source = ColumnDataSource(df)
        else:
            column_source = ColumnDataSource({'values': list(df[0].values), 'index': list(df.index)})

        x_max = max(df.max())
        x_min = min(df.min())
        if x_min == x_max and x_min < 0:
            x_max = 0

        lca_results_plot = bokeh_figure(title=(', '.join([m for m in method])), y_range=list(df.index),
                                        plot_height=BokehPlotUtils.calculate_bar_chart_height(bar_count=df.index.size,
                                                                                              legend_item_count=df.columns.size),
                                        x_range=(x_min, x_max), tools=['hover'],
                                        tooltips=("$name: @$name" if show_legend else "@values"),
                                        sizing_mode="stretch_width", toolbar_location=None)
        lca_results_plot.title.text_font_style = "bold"
        lca_results_plot.title.text_font_size = "12pt"

        if show_legend:
            lca_results_plot.hbar_stack(list(df.columns), height=self.BAR_HEIGHT, y='index', source=column_source,
                                        legend_label=list(df.columns),
                                        fill_color=turbo(len(df.columns)), line_width=0)
        else:
            lca_results_plot.hbar(y="index", height=self.BAR_HEIGHT, right="values", source=column_source)

        # TODO:
        # Handle scenarios and https://github.com/LCA-ActivityBrowser/activity-browser/issues/622

        if x_min < 0:
            lca_results_plot.x_range.start = x_min

        if x_min > 0 and x_max > 0:
            lca_results_plot.x_range.start = 0
        lca_results_plot.xaxis.axis_label = bw.methods[method].get('unit')

        BokehPlotUtils.style_axis_labels(lca_results_plot.yaxis)

        # Relocate the legend to bottom left to save space
        if show_legend:
            BokehPlotUtils.style_and_place_legend(lca_results_plot, "bottom_left")

        lca_results_plot.ygrid.grid_line_color = None
        lca_results_plot.axis.minor_tick_line_color = None
        lca_results_plot.outline_line_color = None

        self.figure = lca_results_plot

        # Disable context menu as no actions at the moment
        self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        template = BokehPlotUtils.build_html_bokeh_template()
        html = file_html(lca_results_plot, template=template, resources=None)
        self.page.setHtml(html)
        self.view.setPage(self.page)


class LCAResultsOverview(BokehPlot):
    """" Generate a bar chart comparing the relative LCA scores of the products """

    def on_context_menu(self, *args, **kwargs):
        raise NotImplementedError

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'LCA Overview'

    def plot(self, df: pd.DataFrame):
        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if "amount" in dfp.columns:
            dfp.drop(["amount"], axis=1, inplace=True)  # Drop the 'amount' col
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        # avoid figures getting too large
        dfp.index = [wrap_text(i, max_length=40) for i in dfp.index]
        dfp.columns = [wrap_text_by_separator(i) for i in dfp.columns]

        dfp = dfp.T

        column_source = ColumnDataSource(dfp)
        lca_results_plot = bokeh_figure(x_range=list(dfp.index), y_range=(0, max(dfp.max())),
                                        sizing_mode="stretch_width", toolbar_location=None)

        colors = turbo(len(dfp.columns))
        for column_index in range(0, dfp.columns.size):
            lca_results_plot.vbar(
                x=dodge('index', mgrid[-0.3:0.3:dfp.columns.size * 1j][column_index] if dfp.columns.size > 1 else 0.0,
                        range=lca_results_plot.x_range),
                top=dfp.columns[column_index], width=0.1 if dfp.columns.size > 3 else 0.3, source=column_source,
                color=colors[column_index], legend_label=dfp.columns[column_index])

        lca_results_plot.x_range.range_padding = 0.08
        lca_results_plot.xgrid.grid_line_color = None
        BokehPlotUtils.style_axis_labels(lca_results_plot.xaxis)
        lca_results_plot.xaxis.major_label_orientation = 45.0

        # Relocate the legend to bottom left to save space
        BokehPlotUtils.style_and_place_legend(lca_results_plot, "bottom_left")

        self.figure = lca_results_plot

        # Disable context menu as no actions at the moment
        self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        template = BokehPlotUtils.build_html_bokeh_template()
        html = file_html(lca_results_plot, template=template, resources=None)
        self.page.setHtml(html)
        self.view.setPage(self.page)


class ContributionPlot(BokehPlot):
    BAR_HEIGHT = 0.4

    def __init__(self):
        super().__init__()
        self.plot_name = 'Contributions'
        self.plot_data: pd.DataFrame = None
        self.context_menu_actions: list = None
        self.chart_bridge: ChartBridge = None
        self.channel: QtWebChannel.QWebChannel = None
        self.hover_callback = None

    def plot(self, df: pd.DataFrame, unit: str = None, context_menu_actions: [] = None,
             is_relative: bool = True):
        """ Plot a horizontal stacked bar chart for the process and elementary flow contributions. """
        self.context_menu_actions = context_menu_actions

        # Copy, clean and transform the dataframe for plotting
        self.plot_data = df.copy()
        self.plot_data.index = self.plot_data['index']
        self.plot_data.drop(self.plot_data.select_dtypes(['object']), axis=1,
                            inplace=True)  # Remove all non-numeric columns (metadata)
        if 'Total' in self.plot_data.index:
            self.plot_data.drop("Total", inplace=True)
        self.plot_data = self.plot_data.fillna(0)
        self.plot_data = self.plot_data.T
        self.plot_data = self.plot_data[::-1]  # Reverse sort the data as bokeh reverses the plotting order

        # Avoid figures getting too large horizontally by text wrapping
        self.plot_data.index = pd.Index([wrap_text(str(i), max_length=40) for i in self.plot_data.index])
        self.plot_data.columns = pd.Index([wrap_text(str(i), max_length=40) for i in self.plot_data.columns])

        # Handle negative values
        has_negative_values = (self.plot_data.values < 0).any()
        has_positive_values = (self.plot_data.values > 0).any()
        positive_df = self.plot_data.copy()
        if has_negative_values:
            negative_df = self.plot_data[self.plot_data < 0]
            negative_df = negative_df.fillna(0)
            positive_df = self.plot_data[self.plot_data > 0]
            positive_df = positive_df.fillna(0)

        # Compute plot height
        plot_height = BokehPlotUtils.calculate_bar_chart_height(bar_count=self.plot_data.index.size,
                                                                legend_item_count=self.plot_data.columns.size)

        # Prepare the plot and add stacked bars
        contribution_plot = bokeh_figure(y_range=list(self.plot_data.index), toolbar_location=None,
                                         plot_height=plot_height,
                                         sizing_mode="stretch_width")
        if has_positive_values:
            contribution_plot.hbar_stack(list(positive_df.columns), height=self.BAR_HEIGHT, y='index',
                                         source=ColumnDataSource(positive_df),
                                         legend_label=list(positive_df.columns),
                                         fill_color=turbo(len(positive_df.columns)), line_width=0)
        if has_negative_values:
            contribution_plot.hbar_stack(list(negative_df.columns), height=self.BAR_HEIGHT, y='index',
                                         source=ColumnDataSource(negative_df),
                                         legend_label=list(negative_df.columns),
                                         fill_color=turbo(len(negative_df.columns)), line_width=0)

        if not has_negative_values:
            contribution_plot.x_range.start = 0

        if unit:
            contribution_plot.xaxis.axis_label = unit
            contribution_plot.xaxis.axis_label_text_font_size = "10pt"
            contribution_plot.xaxis.axis_label_text_font_style = "bold"

        # Relocate the legend to bottom left to save space
        BokehPlotUtils.style_and_place_legend(contribution_plot, (-200, 0))

        # Handle styling
        contribution_plot.ygrid.grid_line_color = None
        contribution_plot.axis.minor_tick_line_color = None
        contribution_plot.outline_line_color = None
        BokehPlotUtils.style_axis_labels(contribution_plot.yaxis)

        self.figure = contribution_plot

        # Handle context menu:
        self.init_context_menu()

        # Add tooltip on hover
        hover_tool_plot = HoverTool(callback=self.hover_callback, tooltips="$name: @$name")
        contribution_plot.add_tools(hover_tool_plot)

        # Create static HTML and render in web-view (this can be exported - will contain hover interaction)
        template = BokehPlotUtils.build_html_bokeh_template(
            add_context_menu_communication=self.context_menu_actions is not None,
            disable_horizontal_scroll=True)
        html = file_html(contribution_plot, template=template, resources=None)
        self.page.setHtml(html)
        self.view.setPage(self.page)

    def init_context_menu(self):
        # Prepare context menu actions Array[tuples(label, function callback)]
        if self.context_menu_actions is not None:
            self.chart_bridge = ChartBridge(self)
            self.channel = QtWebChannel.QWebChannel()
            self.channel.registerObject('chartBridge', self.chart_bridge)
            self.page.setWebChannel(self.channel)
            self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.view.customContextMenuRequested.connect(self.on_context_menu)
            self.hover_callback = CustomJS(code="""
                                                            //console.log(cb_data)
                                                            window.lastHover = {}
                                                            window.lastHover.x = cb_data.geometry.x
                                                            window.lastHover.y = cb_data.geometry.y
                                                            """)
        else:
            self.hover_callback = None
            self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

    def on_context_menu(self, pos):
        """
        Finds the bar and sub-bar, if position of right-click is correct, prepares context menu with actions passed
        and shows it with the co-ordinates passed to ChartBridge object
        @param pos: Position of right-click within application window
        """
        if not self.context_menu_actions or self.chart_bridge.context_menu_x is None or self.chart_bridge.context_menu_y is None:
            return

        bar_margin = 1 - self.BAR_HEIGHT
        bar_index = math.floor(self.chart_bridge.context_menu_y)
        bar_index_start = bar_index + (bar_margin / 2)
        bar_index_end = bar_index + 1 - (bar_margin / 2)
        if (self.chart_bridge.context_menu_y > 0 and bar_index < self.plot_data.index.size
                and bar_index_start <= self.chart_bridge.context_menu_y <= bar_index_end):  # self.chart_bridge.context_menu_x > 0 and

            data_table = self.plot_data.copy()
            is_sub_bar_negative = self.chart_bridge.context_menu_x < 0

            if is_sub_bar_negative:
                data_table = data_table[data_table < 0]
                data_table = data_table.abs()
            else:
                data_table = data_table[data_table > 0]

            data_table = data_table.fillna(0)

            prev_val = 0
            for col_index, column in enumerate(list(data_table.columns), start=0):
                if data_table.iloc[bar_index][column] == 0:
                    continue

                prev_val = data_table.iloc[bar_index][column] + prev_val
                if abs(self.chart_bridge.context_menu_x) < prev_val:
                    # bar_label = self.data.index[bar_index]
                    # sub_bar_label = column

                    context = QMenu(self)
                    for action_name, _action in self.context_menu_actions:
                        context_menu_item = QAction(action_name, self)
                        context_menu_item.triggered.connect(
                            lambda: _action(bar_index=bar_index, sub_bar_index=col_index))
                        context.addAction(context_menu_item)
                    context.popup(self.mapToGlobal(pos))
                    break


class ChartBridge(QObject):
    """
    Chart bridge is used to communicate the co-ordinates in the chart where the user performs a right-click
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.context_menu_x = 0
        self.context_menu_y = 0

    @Slot(str, name="set_context_menu_coordinates")
    def set_context_menu_coordinates(self, args: str):
        """
        The set_context_menu_coordinates is called from the JS with the co-ordinates and these co-ordinates are then used to
    open the context menu from python.
        Args:
            args: string of a serialized json dictionary describing
            - x: X axis co-ordinate (Index of the sub-bar(part-of bar) on which context menu was opened)
            - y: Y axis co-ordinate (Index of the bar on which context menu was opened)
        """
        data_dict = json.loads(args)
        self.context_menu_x = data_dict['x']
        self.context_menu_y = data_dict['y']


class CorrelationPlot(Plot):
    def __init__(self, parent=None):
        super().__init__(parent)
        sns.set(style="darkgrid")

    def plot(self, df: pd.DataFrame):
        """ Plot a heatmap of correlations between different reference flows. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.reset_plot()
        canvas_size = self.canvas.get_width_height()
        # print("Canvas size:", canvas_size)
        size = (4 + df.shape[1] * 0.3, 4 + df.shape[1] * 0.3)
        self.figure.set_size_inches(size[0], size[1])

        corr = df.corr()
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr, dtype=np.bool)
        mask[np.triu_indices_from(mask)] = True
        # Draw the heatmap with the mask and correct aspect ratio
        vmax = np.abs(corr.values[~mask]).max()
        # vmax = np.abs(corr).max()
        sns.heatmap(corr, mask=mask, cmap=plt.cm.PuOr, vmin=-vmax, vmax=vmax,
                    square=True, linecolor="lightgray", linewidths=1, ax=self.ax)

        df_lte8_cols = df.shape[1] <= 8
        for i in range(len(corr)):
            self.ax.text(
                i + 0.5, i + 0.5, corr.columns[i], ha="center", va="center",
                rotation=0 if df_lte8_cols else 45, size=11 if df_lte8_cols else 9
            )
            for j in range(i + 1, len(corr)):
                s = "{:.3f}".format(corr.values[i, j])
                self.ax.text(
                    j + 0.5, i + 0.5, s, ha="center", va="center",
                    rotation=0 if df_lte8_cols else 45, size=11 if df_lte8_cols else 9
                )
        self.ax.axis("off")

        # refresh canvas
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])
        self.canvas.draw()


class MonteCarloPlot(BokehPlot):
    """ Monte Carlo plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'Monte Carlo'

    def on_context_menu(self, *args, **kwargs):
        raise NotImplementedError

    def plot(self, df: pd.DataFrame, method: tuple):
        p = bokeh_figure(tools=['hover', 'wheel_zoom', 'pan'], background_fill_color="#fafafa", toolbar_location=None,
                         sizing_mode="stretch_width",
                         tooltips=[("Probability", "@top"), ("Value", "@right")])
        p.toolbar.active_scroll = p.select_one(WheelZoomTool)
        colors = turbo(df.columns.size)
        i = 0
        for col in df.columns:
            hist, edges = np.histogram(df[col], density=True)
            p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color=colors[i], line_width=0,
                   alpha=0.5, legend_label=col)
            span = Span(location=df[col].mean(), dimension='height', line_color=colors[i], line_width=2)
            p.renderers.append(span)
            i = i + 1

        # Relocate the legend to bottom left to save space
        BokehPlotUtils.style_and_place_legend(p, "center")
        p.xaxis.axis_label = bw.methods[method]["unit"]
        p.yaxis.axis_label = 'Probability'

        self.figure = p

        # Disable context menu as no actions at the moment
        self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        template = BokehPlotUtils.build_html_bokeh_template()
        html = file_html(p, template=template, resources=None)
        self.page.setHtml(html)
        self.view.setPage(self.page)


class SimpleDistributionPlot(Plot):
    def plot(self, data: np.ndarray, mean: float, label: str = "Value"):
        self.reset_plot()
        try:
            sns.histplot(data.T, kde=True, stat="density", ax=self.ax, edgecolor="none")
        except RuntimeError as e:
            print("Runtime error: {}\nPlotting without KDE.".format(e))
            sns.histplot(data.T, kde=False, stat="density", ax=self.ax, edgecolor="none")
        self.ax.set_xlabel(label)
        self.ax.set_ylabel("Probability density")
        # Add vertical line at given mean of x-axis
        self.ax.axvline(mean, label="Mean / amount", c="r", ymax=0.98)
        self.ax.legend(loc="upper right")
        _, height = self.canvas.get_width_height()
        self.setMinimumHeight(height / 2)
        self.canvas.draw()


class BokehPlotUtils:
    BOKEH_JS_File_Name = "bokeh-2.4.1.min.js"

    @staticmethod
    def build_html_bokeh_template(add_context_menu_communication: bool = False,
                                  disable_horizontal_scroll: bool = False):
        bokeh_jspath = webutils.get_static_js_path(BokehPlotUtils.BOKEH_JS_File_Name)
        bokeh_js_code = utils.read_file_text(bokeh_jspath)
        template = Template("""
                <!DOCTYPE html>
                <html lang="en">
                    <head>
                         <meta charset="utf-8">
                         <script type="text/javascript">""" + bokeh_js_code + """</script>
                         """ + (
            """<script src="qrc:///qtwebchannel/qwebchannel.js"></script>""" if add_context_menu_communication else "") + """
                    </head>
                    <body""" + (
                                """ style="overflow-x:hidden;" """ if disable_horizontal_scroll else "") + """>
                        {{ plot_div | safe }}
                        {{ plot_script | safe }}
                        """ + (
                                """<script type="text/javascript">
                                    // Connect to QWebChannel and accept the injected chartBridge object for communication
                                    // with Pyside 
                                    new QWebChannel(qt.webChannelTransport, function (channel) {
                                        window.chartBridge = channel.objects.chartBridge;
                                    });
                                    
                                  // Called when user right-clicks, passes the co-ordinates to python via the injected  
                                  // chartBridge object to open context menu from pyside
                                  document.addEventListener('contextmenu', function(e) {
                                     window.chartBridge.set_context_menu_coordinates(JSON.stringify({x:window.lastHover.x, y: window.lastHover.y}));
                                  }, true);
                                 </script>""" if add_context_menu_communication else "") + """
                    </body>
                </html> """)
        return template

    @staticmethod
    def calculate_bar_chart_height(bar_count: int = 1, legend_item_count: int = 1):
        return 120 + (70 * bar_count) + (20 * legend_item_count)

    @staticmethod
    def style_and_place_legend(plot, location):
        new_legend = plot.legend[0]
        new_legend.location = location
        plot.legend[0] = None
        plot.legend[0].label_text_font_size = "8pt"
        plot.legend[0].label_text_font_style = "bold"
        plot.legend[0].label_height = 10
        plot.legend[0].label_standoff = 2
        plot.legend[0].glyph_width = 15
        plot.legend[0].glyph_height = 15
        plot.legend[0].spacing = 1
        plot.legend[0].margin = 0
        plot.legend.border_line_color = None
        new_legend.click_policy = 'hide'
        plot.add_layout(new_legend, 'below')

    @staticmethod
    def style_axis_labels(axis):
        axis.major_label_text_font_size = "10pt"
        axis.major_label_text_font_style = "bold"
        axis.major_label_text_line_height = 0.8
        axis.major_label_text_align = "right"
