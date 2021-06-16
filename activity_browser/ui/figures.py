# -*- coding: utf-8 -*-
import json
import math
import os

from PySide2.QtCore import QObject, Slot
from PySide2.QtWidgets import QMenu, QAction, QMessageBox
from bokeh.events import Tap
from bokeh.io import export_png
from jinja2 import Template
import brightway2 as bw
from bw2data.filesystem import safe_filename
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from pathlib import Path
from PySide2 import QtWidgets, QtCore, QtWebEngineWidgets, QtWebChannel
import seaborn as sns

from ..bwutils.commontasks import wrap_text
from ..settings import ab_settings

from bokeh.models import ColumnDataSource, HoverTool, TapTool, OpenURL, CustomJS
from bokeh.plotting import figure as bfig
from bokeh.embed import file_html
from bokeh.palettes import viridis


# todo: sizing of the figures needs to be improved and systematized...
# todo: Bokeh is a potential alternative as it allows interactive visualizations,
#  but this issue needs to be resolved first: https://github.com/bokeh/bokeh/issues/8169

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


class LCAResultsBarChart(Plot):
    """" Generate a bar chart comparing the absolute LCA scores of the products """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'LCA scores'

    def plot(self, df: pd.DataFrame, method: tuple, labels: list):
        self.reset_plot()
        height_inches, width_inches = self.get_canvas_size_in_inches()
        self.figure.set_size_inches(height_inches, width_inches)

        # https://github.com/LCA-ActivityBrowser/activity-browser/issues/489
        df.index = pd.Index(labels)  # Replace index of tuples
        show_legend = df.shape[1] != 1  # Do not show the legend for 1 column
        df.plot.barh(ax=self.ax, legend=show_legend)
        self.ax.invert_yaxis()

        # labels
        self.ax.set_yticks(np.arange(len(labels)))
        self.ax.set_xlabel(bw.methods[method].get('unit'))
        self.ax.set_title(', '.join([m for m in method]))
        # self.ax.set_yticklabels(labels, minor=False)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle='dashed')
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        # draw
        self.canvas.draw()


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


class ContributionPlot(Plot):
    MAX_LEGEND = 30

    def __init__(self):
        super().__init__()
        self.plot_name = 'Contributions'

    def plot(self, df: pd.DataFrame, unit: str = None):
        """ Plot a horizontal bar chart of the process contributions. """
        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        self.ax.clear()
        canvas_width_inches, canvas_height_inches = self.get_canvas_size_in_inches()
        optimal_height_inches = 4 + dfp.shape[1] * 0.55
        # print('Optimal Contribution plot height:', optimal_height_inches)
        self.figure.set_size_inches(canvas_width_inches, optimal_height_inches)

        # avoid figures getting too large horizontally
        dfp.index = pd.Index([wrap_text(str(i), max_length=40) for i in dfp.index])
        dfp.columns = pd.Index([wrap_text(i, max_length=40) for i in dfp.columns])
        # Strip invalid characters from the ends of row/column headers
        dfp.index = dfp.index.str.strip("_ \n\t")
        dfp.columns = dfp.columns.str.strip("_ \n\t")

        dfp.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax,
            legend=False if dfp.shape[0] >= self.MAX_LEGEND else True,
        )
        self.ax.tick_params(labelsize=8)
        if unit:
            self.ax.set_xlabel(unit)

        # show legend if not too many items
        if not dfp.shape[0] >= self.MAX_LEGEND:
            plt.rc('legend', **{'fontsize': 8})
            ncols = math.ceil(dfp.shape[0] * 0.6 / optimal_height_inches)
            # print('Ncols:', ncols, dfp.shape[0] * 0.55, optimal_height_inches)
            self.ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), ncol=ncols)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle='dashed')
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        # refresh canvas
        # size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[1] * 0.55)
        # self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])

        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])
        self.canvas.draw()


class BPlot(QtWidgets.QWidget):
    ALL_FILTER = "All Files (*.*)"
    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.plot_name = 'Figure'
        self.bridge = Bridge(self)
        self.channel = QtWebChannel.QWebChannel()
        self.channel.registerObject('bridge', self.bridge)

        self.view = QtWebEngineWidgets.QWebEngineView()
        self.view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)  # QtCore.Qt.NoContextMenu
        #self.debugview = QtWebEngineWidgets.QWebEngineView()
        self.view.customContextMenuRequested.connect(self.on_context_menu)
        self.view.setMinimumHeight(400)
        self.page = QtWebEngineWidgets.QWebEnginePage()
        self.page.setWebChannel(self.channel)

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.updateGeometry()

    def on_context_menu(self, pos):
        # TODO: send signal from js using QChannel to let this know the index(process name) then link the action to open the process
        context = QMenu(self)
        context.addAction(QAction("Open activity list", self)) # connect to event handler
        context.addAction(QAction("Other action", self))
        context.popup(self.mapToGlobal(pos));  # .exec(self.mapToGlobal(pos))

    def plot(self, *args, **kwargs):
        raise NotImplementedError

    def reset_plot(self) -> None:
        self.page.load(self.url)
        # TODO: refresh page
        # self.figure.clf()
        # self.ax = self.figure.add_subplot(111)

    def get_canvas_size_in_inches(self):
        # print("Canvas size:", self.canvas.get_width_height())
        return tuple(x / self.view.dpi for x in self.page.get_width_height())

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
            # export_png(plot, filename=filepath)
            # TODO: self.figure.savefig(filepath)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, file_filter=self.SVG_FILTER)
        if filepath:
            if not filepath.endswith('.svg'):
                filepath += '.svg'
            # TODO: self.figure.savefig(filepath)


class BContributionPlot(BPlot):
    MAX_LEGEND = 30

    def __init__(self):
        super().__init__()
        self.plot_name = 'Contributions'

    def plot(self, df: pd.DataFrame, unit: str = None):
        """ Plot a horizontal bar chart of the process contributions. """
        package_dir = Path(__file__).resolve().parents[2]
        bokeh_jspath = str(package_dir.joinpath("activity_browser", "static", "javascript", "bokeh-2.3.2.min.js"))
        js_code = open(bokeh_jspath, mode="r", encoding='UTF-8').read()

        # TODO:
            # Reduce js code - Let context menu be in Python
            # Show context menu on right click
            # 2 bugs assigned to me
            # Add a debounce to cut-off slider


        template = Template("""
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="utf-8">
                <title>{{ title if title else "Bokeh Plot" }}</title>
                 <script type="text/javascript">""" + js_code + """</script>
                 <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
                 <script type="text/javascript">
                    Bokeh.set_log_level("info");
                 </script>
                 <style>
                    option:hover {
                      background-color: #e6e6e6;
                    }
                    option {
                        padding: 5px;
                    }
                    select {
                        overflow: hidden;
                        background-color: #cccccc;
                    }
                    .hidden {
                      visibility: hidden;
                    }
                    #contextMenu:active {
                      box-shadow: 0 0 5px rgba(0, 0, 0, .25);
                    }
                    #contextMenu {
                      z-index:100;
                      box-sizing: border-box;
                      position: absolute;
                      box-shadow: 0 0 12px rgba(0, 0, 0, .25);
                      transition: box-shadow ease-in 50ms;
                    }
            </style>
            </head>
            <body>
                <div id='contextMenu' class='hidden'></div>
                {{ plot_div | safe }}
                {{ plot_script | safe }}
                <script type="text/javascript">
                    new QWebChannel(qt.webChannelTransport, function (channel) {
                        window.bridge = channel.objects.bridge;
                    });
                    
                    const options = ['Open Activity', 'Open details'] // TODO: This should come from configuration
                    var result_dict = {} //action, sub_bar, bar
                    const contextMenu = document.getElementById('contextMenu');
                    function openContextMenu(sx, sy) { //Pass options and sx,sy here
                        contextMenu.style.left = `${ sx }px`;
                        contextMenu.style.top = `${ sy }px`;
                        contextMenu.innerHTML = '';
                        var select = document.createElement("select");
                        select.id = "options"
                        select.size = 2 //options.length
                        for (const val of options)
                        {
                            var option = document.createElement("option");
                            option.value = val;
                            option.text = val.charAt(0).toUpperCase() + val.slice(1);
                            select.appendChild(option);
                        }
                        select.onchange = () => {
                            console.log('selection changed');
                            result_dict.action = select.value;
                            clearContextMenu();
                            window.bridge.chart_interaction(JSON.stringify(result_dict));
                        }
                       contextMenu.appendChild(select);
                       contextMenu.classList.remove('hidden');
                    }
                    document.onmousewheel = () => {
                      clearContextMenu()
                    };
                    document.onkeydown = (e) => {
                      if (e.key === 'Escape' || e.which === 27 || e.keyCode === 27) {
                        clearContextMenu()
                      }
                    };
                    function clearContextMenu(){
                        contextMenu.classList.add('hidden');
                        contextMenu.innerHTML = '';
                    }
                 </script>
            </body>
        </html> """)

        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        # avoid figures getting too large horizontally
        dfp.index = pd.Index([wrap_text(str(i), max_length=40) for i in dfp.index])
        dfp.columns = pd.Index([wrap_text(str(i), max_length=40) for i in dfp.columns])

        contri_transpose = dfp.T
        contri_transpose = contri_transpose.fillna(0)
        column_source = ColumnDataSource(contri_transpose)

        height = 0.7
        p = bfig(y_range=list(contri_transpose.index), plot_height=400, tools=['hover', 'pan', 'wheel_zoom'],
                 tooltips="$name: @$name")
        p.hbar_stack(list(contri_transpose.columns), height=height, y='index', source=column_source,
                     legend_label=list(contri_transpose.columns),
                     fill_color=viridis(len(contri_transpose.columns)), muted_alpha=2)

        new_legend = p.legend[0]
        new_legend.location = "center"
        p.legend[0] = None
        p.legend[0].label_text_font_size = "8pt"
        new_legend.click_policy = 'hide'
        p.add_layout(new_legend, 'below')

        p.ygrid.grid_line_color = None
        p.axis.minor_tick_line_color = None
        p.outline_line_color = None

        # TODO: Pass the key of the activity here so the js can send it back to bokeh
        callback = CustomJS(args=dict(source=column_source, height=height, legend_labels=list(contri_transpose.columns)),
                            code="""
        console.log('works');
        var bar_margin = 1 - height;
        var bar_index = Math.floor(cb_obj.y);
        var bar_index_start = bar_index + (bar_margin/2);
        var bar_index_end = bar_index + 1 - (bar_margin/2);
        var found = false;
        if(cb_obj.x > 0 && cb_obj.y > 0 && bar_index < source.data.index.length 
            && cb_obj.y >= bar_index_start && cb_obj.y <= bar_index_end)
        {
            console.log('On a bar');
            var prev_val = 0;
            for(var index in legend_labels)
            {
                var legend_label = legend_labels[index];
                if(source.data[legend_label][bar_index.toString()]<=0)
                    continue;
                prev_val = source.data[legend_label][bar_index.toString()] + prev_val;
                if(cb_obj.x < prev_val) {
                    console.log(legend_label);
                    result_dict.bar = source.data.index[bar_index];
                    result_dict.sub_bar = legend_label;
                    
                    openContextMenu(cb_obj.sx, cb_obj.sy);
                    found = true;
                    break;
                }
            }
            
        }
        if(!found) {
            clearContextMenu()
        }
        """)
        p.js_on_event('tap', callback)

        html = file_html(p, template=template, resources=None)
        self.page.setHtml(html)
        #self.page.setDevToolsPage(self.debugview.page())
        #self.debugview.show()
        self.view.setPage(self.page)


class Bridge(QObject):
    @Slot(str, name="chart_interaction")
    def chart_interaction(self, interaction_args: str):
        """ Is called when part of HBar is clicked in Javascript (via Bokeh callback).
        Args:
            interaction_args: string of a serialized json dictionary describing
            - X axis label (Process/EF the part of Hbar represnts)
            - Y axis label (Process/EF/Impact Category the Hbar represnts)
        """
        #interaction_data_dict = json.loads(interaction_args)
        print(interaction_args)
        #TODO: Open activity or react to event
        msgBox = QMessageBox()
        msgBox.setText(interaction_args)
        msgBox.setDefaultButton(QMessageBox.Ok)
        msgBox.exec_()


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


class MonteCarloPlot(Plot):
    """ Monte Carlo plot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_name = 'Monte Carlo'

    def plot(self, df: pd.DataFrame, method: tuple):
        self.ax.clear()

        for col in df.columns:
            color = self.ax._get_lines.get_next_color()
            df[col].hist(ax=self.ax, figure=self.figure, label=col, density=True, color=color,
                         alpha=0.5)  # , histtype="step")
            # self.ax.axvline(df[col].median(), color=color)
            self.ax.axvline(df[col].mean(), color=color)

        self.ax.set_xlabel(bw.methods[method]["unit"])
        self.ax.set_ylabel('Probability')
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.07), )  # ncol=2

        # lconfi, upconfi =mc['statistics']['interval'][0], mc['statistics']['interval'][1]

        self.canvas.draw()


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
