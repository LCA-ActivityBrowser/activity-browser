# -*- coding: utf-8 -*-
import json
import math
import os
from typing import Optional

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
from bokeh.models import ColumnDataSource, HoverTool, CustomJS, Span
from bokeh.palettes import viridis
from bokeh.plotting import figure as bfig
from bw2data.filesystem import safe_filename
from jinja2 import Template
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from activity_browser.ui.web import webutils
from .. import utils
from ..bwutils.commontasks import wrap_text
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
        self.view.reload()

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
            fig_width = self.figure.width + 500
            export_png(self.figure, filename=filepath, width=fig_width)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, file_filter=self.SVG_FILTER)
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

        if show_legend:
            column_source = ColumnDataSource(df)
        else:
            column_source = ColumnDataSource({'values': list(df[0].values), 'index': list(df.index)})

        x_max = max(df.max())
        x_min = min(df.min())
        lca_results_plot = bfig(title=(', '.join([m for m in method])), y_range=list(df.index),
                                plot_height=BokehPlotUtils.calculate_bar_chart_height(bar_count=df.index.size,
                                                                                      legend_item_count=df.columns.size),
                                x_range=(x_min, x_max), tools=['hover'],
                                tooltips=("$name: @$name" if show_legend else "@values"),
                                sizing_mode="stretch_width", toolbar_location=None)

        if show_legend:
            lca_results_plot.hbar_stack(list(df.columns), height=self.BAR_HEIGHT, y='index', source=column_source,
                                        legend_label=list(df.columns),
                                        fill_color=viridis(len(df.columns)), line_width=0)
        else:
            lca_results_plot.hbar(y="index", height=self.BAR_HEIGHT, right="values", source=column_source)

        # p.x_range.start = 0
        lca_results_plot.xaxis.axis_label = bw.methods[method].get('unit')

        if show_legend:
            new_legend = lca_results_plot.legend[0]
            lca_results_plot.legend[0] = None
            lca_results_plot.legend[0].label_text_font_size = "8pt"
            new_legend.click_policy = 'hide'
            new_legend.location = (-200, 0)  # "bottom_left"
            lca_results_plot.add_layout(new_legend, 'below')

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


class ContributionPlot(BokehPlot):
    BAR_HEIGHT = 0.6

    def __init__(self):
        super().__init__()
        self.plot_name = 'Contributions'
        self.data: pd.DataFrame = None
        self.context_menu_actions: Optional[list] = None
        self.chart_bridge: Optional[ChartBridge] = None
        self.channel: Optional[QtWebChannel.QWebChannel] = None

    def plot(self, df: pd.DataFrame, unit: str = None, context_menu_actions: [] = None,
             is_relative: bool = True):
        """ Plot a horizontal stacked bar chart of the process contributions. """

        # Prepare dataframe for plotting
        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        # Avoid figures getting too large horizontally
        dfp.index = pd.Index([wrap_text(str(i), max_length=40) for i in dfp.index])
        dfp.columns = pd.Index([wrap_text(str(i), max_length=40) for i in dfp.columns])

        contri_transpose = dfp.T
        contri_transpose = contri_transpose.fillna(0)
        column_source = ColumnDataSource(contri_transpose)
        self.data = contri_transpose

        contribution_plot = bfig(y_range=list(contri_transpose.index), toolbar_location=None,
                                 plot_height=BokehPlotUtils.calculate_bar_chart_height(
                                     bar_count=contri_transpose.index.size,
                                     legend_item_count=contri_transpose.columns.size),
                                 sizing_mode="stretch_width")
        contribution_plot.hbar_stack(list(contri_transpose.columns), height=self.BAR_HEIGHT, y='index',
                                     source=column_source,
                                     legend_label=list(contri_transpose.columns),
                                     fill_color=viridis(len(contri_transpose.columns)), line_width=0)

        if is_relative:
            contribution_plot.x_range.start = 0

        if unit:
            contribution_plot.xaxis.axis_label = unit

        # Handle legend
        new_legend = contribution_plot.legend[0]
        new_legend.location = (-200, 0)  # "bottom_left"
        contribution_plot.legend[0] = None
        contribution_plot.legend[0].label_text_font_size = "8pt"
        new_legend.click_policy = 'hide'
        contribution_plot.add_layout(new_legend, 'below')

        # Handle styling
        contribution_plot.ygrid.grid_line_color = None
        contribution_plot.axis.minor_tick_line_color = None
        contribution_plot.outline_line_color = None

        self.figure = contribution_plot

        # Prepare for right-click interactions
        self.context_menu_actions = context_menu_actions
        add_context_menu_actions = context_menu_actions is not None

        hover_callback = None
        if add_context_menu_actions:
            self.chart_bridge = ChartBridge(self)
            self.channel = QtWebChannel.QWebChannel()
            self.channel.registerObject('chartBridge', self.chart_bridge)
            self.page.setWebChannel(self.channel)
            self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self.view.customContextMenuRequested.connect(self.on_context_menu)
            hover_callback = CustomJS(code="""
                                                    //console.log(cb_data)
                                                    window.lastHover = {}
                                                    window.lastHover.x = cb_data.geometry.x
                                                    window.lastHover.y = cb_data.geometry.y
                                                    """)
        else:
            self.view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        hover_tool_plot = HoverTool(callback=hover_callback, tooltips="$name: @$name")
        contribution_plot.add_tools(hover_tool_plot)

        # Create static HTML and render in webview (this can be exported - will contain hover interaction)
        template = BokehPlotUtils.build_html_bokeh_template(add_context_menu_communication=add_context_menu_actions,
                                                            disable_horizontal_scroll=True)
        html = file_html(contribution_plot, template=template, resources=None)
        self.page.setHtml(html)
        self.view.setPage(self.page)

    def on_context_menu(self, pos):
        """
        Finds the bar and sub-bar, if position of right-click is correct, prepares context menu with actions passed and shows it
        @param pos: Position of right-click within application window
        @return:
        """
        if not self.context_menu_actions or self.chart_bridge.context_menu_x is None or self.chart_bridge.context_menu_y is None:
            return

        bar_margin = 1 - self.BAR_HEIGHT
        bar_index = math.floor(self.chart_bridge.context_menu_y)
        bar_index_start = bar_index + (bar_margin / 2)
        bar_index_end = bar_index + 1 - (bar_margin / 2)
        if (
                self.chart_bridge.context_menu_x > 0 and self.chart_bridge.context_menu_y > 0 and bar_index < self.data.index.size
                and bar_index_start <= self.chart_bridge.context_menu_y <= bar_index_end):
            prev_val = 0
            for col_index, column in enumerate(list(self.data.columns), start=0):
                if self.data.iloc[bar_index][column] <= 0:
                    continue
                prev_val = self.data.iloc[bar_index][column] + prev_val
                if self.chart_bridge.context_menu_x < prev_val:
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.context_menu_x = 0
        self.context_menu_y = 0

    @Slot(str, name="set_context_menu_coordinates")
    def set_context_menu_coordinates(self, args: str):
        """ Called when user opens context menu by right-clicking on HBar.
        Args:
            args: string of a serialized json dictionary describing
            - x: X axis label (Process the part of Hbar represnts)
            - y: Y axis label (Process the part of Hbar represnts)
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
        p = bfig(tools=['hover'], background_fill_color="#fafafa", toolbar_location=None, sizing_mode="stretch_width",
                 tooltips=[("Probability", "@top"), ("Value", "@right")])
        colors = viridis(df.columns.size)
        i = 0
        for col in df.columns:
            hist, edges = np.histogram(df[col], density=True)
            p.quad(top=hist, bottom=0, left=edges[:-1], right=edges[1:], fill_color=colors[i], line_color="white",
                   alpha=0.5, legend_label=col)
            span = Span(location=df[col].mean(), dimension='height', line_color=colors[i], line_width=2)
            p.renderers.append(span)
            i = i + 1

        p.legend.location = "center"
        p.legend.background_fill_color = "#fefefe"
        p.legend.click_policy = 'hide'
        p.xaxis.axis_label = bw.methods[method]["unit"]
        p.yaxis.axis_label = 'Probability'
        p.add_layout(p.legend[0], 'below')

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
    BOKEH_JS_File_Name = "bokeh-2.3.2.min.js"

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
                                    new QWebChannel(qt.webChannelTransport, function (channel) {
                                        window.chartBridge = channel.objects.chartBridge;
                                    });
                                  document.addEventListener('contextmenu', function(e) {
                                     window.chartBridge.set_context_menu_coordinates(JSON.stringify({x:window.lastHover.x, y: window.lastHover.y}));
                                  }, true);
                                 </script>""" if add_context_menu_communication else "") + """
                    </body>
                </html> """)
        return template

    @staticmethod
    def calculate_bar_chart_height(bar_count: int = 1, legend_item_count: int = 1):
        return 100 + (90 * bar_count) + (30 * legend_item_count)
