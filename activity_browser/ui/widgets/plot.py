from qtpy import QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class ABPlot(QtWidgets.QWidget):
    ALL_FILTER = "All Files (*.*)"
    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    def __init__(self, parent=None):
        super().__init__(parent)
        # create figure, canvas, and axis
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(0)

        self.ax = self.figure.add_subplot(111)  # create an axis
        self.plot_name = "Figure"
        self._set_plot_chrome_white()

        # set the layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.updateGeometry()

    def plot(self, *args, **kwargs):
        raise NotImplementedError

    def _set_plot_chrome_white(self) -> None:
        """Match figure and Qt canvas to the plot area so default grey margins disappear."""
        self.figure.patch.set_facecolor("white")
        if self.ax is not None:
            self.ax.set_facecolor("white")
        bg = "background-color: white;"
        self.canvas.setStyleSheet(bg)
        self.setStyleSheet(bg)

    def reset_plot(self) -> None:
        self.figure.clf()
        self.ax = self.figure.add_subplot(111)
        self._set_plot_chrome_white()

    def get_canvas_size_in_inches(self):
        return tuple(x / self.figure.dpi for x in self.canvas.get_width_height())

    def to_png(self):
        """Export to .png format."""
        from activity_browser.bwutils.commontasks import savefilepath

        filepath = savefilepath(
            default_file_name=self.plot_name, file_filter=self.PNG_FILTER
        )
        if filepath:
            if not filepath.endswith(".png"):
                filepath += ".png"
            self.figure.savefig(filepath)

    def to_svg(self):
        """Export to .svg format."""      
        from activity_browser.bwutils.commontasks import savefilepath
        
        filepath = savefilepath(
            default_file_name=self.plot_name, file_filter=self.SVG_FILTER
        )
        if filepath:
            if not filepath.endswith(".svg"):
                filepath += ".svg"
            self.figure.savefig(filepath)

