# -*- coding: utf-8 -*-
import math
import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5 import QtWidgets
import appdirs
import brightway2 as bw
from time import time

from ..bwutils.commontasks import format_activity_label, wrap_text


class Plot(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Plot, self).__init__(parent)
        # create figure, canvas, and axis
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111)  # create an axis
        self.plot_name = 'Figure'

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))

    def get_canvas_size_in_inches(self):
        # print("Canvas size:", self.canvas.get_width_height())
        return tuple(x / self.figure.dpi for x in self.canvas.get_width_height())

    def savefilepath(self, default_file_name="LCA results", filter="All Files (*.*)"):

        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption='Choose location to save lca results',
            directory=appdirs.AppDirs('ActivityBrowser', 'ActivityBrowser').user_data_dir+"\\" + default_file_name,
            filter=filter,
        )
        return filepath

    def to_png(self):
        """ Export to .png format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, filter="PNG (*.png)")
        if filepath:
            if not filepath.endswith('.png'):
                filepath += '.png'
            self.figure.savefig(filepath)

    def to_svg(self):
        """ Export to .svg format. """
        filepath = self.savefilepath(default_file_name=self.plot_name, filter="SVG (*.svg)")
        if filepath:
            if not filepath.endswith('.svg'):
                filepath += '.svg'
            self.figure.savefig(filepath)



class LCAResultsBarChart(Plot):
    """" Generate a bar chart comparing the absolute LCA scores of the products """
    def __init__(self, parent=None, *args):
        super(LCAResultsBarChart, self).__init__(parent, *args)
        self.plot_name = 'LCA scores'

    def plot(self, mlca, method=None):

        self.ax.clear()

        if method == None:
            method = mlca.methods[0]

        functional_units = [format_activity_label(next(iter(fu.keys())), style='pnl') for fu in mlca.func_units]

        print('Method:', method)
        values = mlca.lca_scores[:, mlca.method_index[method]]
        y_pos = np.arange(len(functional_units))

        # color_iterate = iter(plt.rcParams['axes.prop_cycle'])
        for i in range(len(values)):
            self.ax.barh(y_pos[i], values[i], align='center', alpha=1)  # color=next(color_iterate)['color'],

        # labels
        self.ax.set_yticks(y_pos)
        self.ax.set_xlabel(bw.methods[method].get('unit'))
        self.ax.set_title(', '.join([m for m in method]))
        self.ax.set_yticklabels(functional_units, minor=False)

        # grid
        self.ax.grid(which="major", axis="x", color="grey", linestyle='dashed')
        self.ax.set_axisbelow(True)  # puts gridlines behind bars

        # self.canvas.figure
        self.canvas.draw()


class LCAResultsPlot(Plot):
    def __init__(self, parent=None, *args):
        super(LCAResultsPlot, self).__init__(parent, *args)
        self.plot_name = 'LCA heatmap'

    def plot(self, df):
        """ Plot a heatmap grid of the different methods and functional units. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)

        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)

        # avoid figures getting too large horizontally
        dfp.index = [wrap_text(i, max_length=40) for i in dfp.index]

        hm = sns.heatmap(dfp,
                    ax=self.ax,
                    cmap='Blues',
                    annot=True,
                    linewidths=.05,
                    annot_kws={"size": 11 if dfp.shape[1] <= 8 else 9,
                            'rotation': 0 if dfp.shape[1] <= 8 else 60}
                    )
        hm.tick_params(labelsize=8)

        # refresh canvas
        size_inches = (2 + dfp.shape[0] * 0.5, 4 + dfp.shape[0] * 0.55)
        self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])

        self.canvas.draw()


class ContributionPlot(Plot):
    def __init__(self):
        super(ContributionPlot, self).__init__()
        self.plot_name = 'Contributions'

    def plot(self, df):
        """ Plot a horizontal bar chart of the process contributions. """
        dfp = df.copy()
        dfp.index = dfp['index']
        dfp.drop(dfp.select_dtypes(['object']), axis=1, inplace=True)  # get rid of all non-numeric columns (metadata)
        if 'Total' in dfp.index:
            dfp.drop("Total", inplace=True)


        self.ax.clear()
        height = 1 + dfp.shape[1] * 0.5
        self.figure.set_figheight(height)

        # avoid figures getting too large horizontally
        dfp.index = [wrap_text(i, max_length=40) for i in dfp.index]
        dfp.columns = [wrap_text(i, max_length=40) for i in dfp.columns]
        # dfp.columns = [str(c).replace(' | ', '\n') for c in dfp.columns]
        # dfp.index = [str(c).replace(' | ', '\n') for c in dfp.index]

        plot = dfp.T.plot.barh(
            stacked=True,
            cmap=plt.cm.nipy_spectral_r,
            ax=self.ax
        )
        plot.tick_params(labelsize=8)
        plt.rc('legend', **{'fontsize': 8})  # putting below affects only LCAElementaryFlowContributionPlot
        plot.legend(loc='center left', bbox_to_anchor=(1, 0.5),
                    ncol=math.ceil((len(dfp.index) * 0.22) / height))
        plot.grid(b=False)

        # refresh canvas
        # size_inches = (2 + dfp.shape[1] * 0.5, 4 + dfp.shape[1] * 0.55)
        # self.figure.set_size_inches(self.get_canvas_size_in_inches()[0], size_inches[1])
        # size_pixels = self.figure.get_size_inches() * self.figure.dpi
        # self.setMinimumHeight(size_pixels[1])
        # self.canvas.draw()

        self.canvas.draw()
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])


class CorrelationPlot(Plot):
    def __init__(self, parent=None, *args):
        super(CorrelationPlot, self).__init__(parent, *args)
        sns.set(style="darkgrid")

    def plot(self, mlca, labels):
        """ Plot a heatmap of correlations between different functional units. """
        # need to clear the figure and add axis again
        # because of the colorbar which does not get removed by the ax.clear()
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        canvas_size = self.canvas.get_width_height()
        # print("Canvas size:", canvas_size)
        size = (4 + len(labels) * 0.3, 4 + len(labels) * 0.3)
        self.figure.set_size_inches(size[0], size[1])

        df = pd.DataFrame(data=mlca.lca_scores_normalized.T, columns=labels)
        corr = df.corr()
        # Generate a mask for the upper triangle
        mask = np.zeros_like(corr, dtype=np.bool)
        mask[np.triu_indices_from(mask)] = True
        # Draw the heatmap with the mask and correct aspect ratio
        vmax = np.abs(corr.values[~mask]).max()
        # vmax = np.abs(corr).max()
        sns.heatmap(corr, mask=mask, cmap=plt.cm.PuOr, vmin=-vmax, vmax=vmax,
                    square=True, linecolor="lightgray", linewidths=1, ax=self.ax)
        for i in range(len(corr)):
            self.ax.text(i + 0.5, i + 0.5, corr.columns[i],
                      ha="center", va="center",
                      rotation=0 if len(labels) <= 8 else 45,
                      size=11 if len(labels) <= 8 else 9)
            for j in range(i + 1, len(corr)):
                s = "{:.3f}".format(corr.values[i, j])
                self.ax.text(j + 0.5, i + 0.5, s,
                          ha="center", va="center",
                          rotation=0 if len(labels) <= 8 else 45,
                          size=11 if len(labels) <= 8 else 9)
        self.ax.axis("off")

        # refresh canvas
        self.canvas.draw()
        size_pixels = self.figure.get_size_inches() * self.figure.dpi
        self.setMinimumHeight(size_pixels[1])


class MonteCarloPlot(Plot):
    """ Monte Carlo plot."""
    def __init__(self, parent=None):
        super(MonteCarloPlot, self).__init__(parent)
        self.plot_name = 'MonteCarlo'

    def plot(self, df, method):
        # self.figure.clf()
        # self.ax = self.figure.add_subplot(111)
        self.ax.clear()

        for col in df.columns:
            df[col].hist(ax=self.ax, figure=self.figure, label=col, density=True, alpha=0.5)  # , histtype="step")

        self.ax.set_xlabel(bw.methods[method]["unit"])
        self.ax.set_ylabel('Probability')
        self.ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15),
                  fancybox=True, shadow=True, ncol=1)

        # print('Calculating MC LCA')
        # print('method', method)
        # # method = ('IPCC 2013', 'climate change', 'GTP 100a')
        # FU = {bw.Database('ecoinvent 3.4 cutoff').random(): 1.0}
        #
        # start = time()
        # mc = bw.MonteCarloLCA(demand=FU, method=method)
        # results = [next(mc) for x in range(10)]
        # print("MC LCA calculate in ({:.2g} seconds, )".format(time() - start))
        #
        # # pmc = bw.ParallelMonteCarlo(demand=FU, iterations=100, method=method)
        # # start = time()
        # # results = pmc.calculate()
        # print("MC LCA calculate in ({:.2g} seconds, )".format(time() - start))
        #
        # # n, bins, patches = plt.hist(results, normed=1, histtype="step")
        # self.ax.hist(results, density=1, histtype="step")
        #
        # self.ax.set_xlabel(bw.methods[method]["unit"])


        # self.ax.xlabel(bw.methods[method]["unit"])
        # self.ax.ylabel("Probability")
        # self.ax.title(FU)

        # plt.hist(results, ax=self.ax, normed=True, histtype="step")
        # self.ax.xlabel(method)
        # self.ax.ylabel("Probability")

        # # get matplotlib figure data
        # hist = np.array(mc['histogram'])
        # smoothed = np.array(mc['smoothed'])
        # values = hist[:, 0]
        # bins = hist[:, 1]
        # sm_x = smoothed[:, 0]
        # sm_y = smoothed[:, 1]
        # median = mc['statistics']['median']
        # mean = mc['statistics']['mean']
        # lconfi, upconfi =mc['statistics']['interval'][0], mc['statistics']['interval'][1]
        #
        # # plot
        # self.figure_mc.clf()
        # ax = self.figure_mc.add_subplot(111)
        # plt.rcParams.update({'font.size': 10})
        # ax.plot(values, bins)
        # ax.plot(sm_x, sm_y)
        # ax.vlines(lconfi, 0 , sm_y[0],
        #           label='lower 95%: {:.3g}'.format(lconfi), color='red', linewidth=2.0)
        # ax.vlines(upconfi, 0 , sm_y[-1],
        #           label='upper 95%: {:.3g}'.format(upconfi), color='red', linewidth=2.0)
        # ax.vlines(median, 0 , sm_y[self.helper.find_nearest(sm_x, median)],
        #           label='median: {:.3g}'.format(median), color='magenta', linewidth=2.0)
        # ax.vlines(mean, 0 , sm_y[self.helper.find_nearest(sm_x, mean)],
        #           label='mean: {:.3g}'.format(mean), color='blue', linewidth=2.0)
        # plt.xlabel('LCA scores ('+str(mc['iterations'])+' runs)'), plt.ylabel('probability')
        # plt.legend(loc='upper right', prop={'size': 10})
        self.canvas.draw()