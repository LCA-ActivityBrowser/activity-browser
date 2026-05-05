import math

from qtpy import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class ABFigureCanvas(FigureCanvasQTAgg):
    """Matplotlib's Qt canvas uses fig pixel size for :meth:`sizeHint`, so layouts and
    :class:`QScrollArea` grow the main window to match a wide figure. We only need the
    widget to fill the width given by the parent; :meth:`resizeEvent` on the base
    class already keeps the figure size in sync with the widget.
    """

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802 (Qt API)
        return QtCore.QSize(0, 0)

    def minimumSizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(0, 0)


class ABPlot(QtWidgets.QWidget):
    ALL_FILTER = "All Files (*.*)"
    PNG_FILTER = "PNG (*.png)"
    SVG_FILTER = "SVG (*.svg)"

    def __init__(self, parent=None):
        super().__init__(parent)
        # create figure, canvas, and axis
        self.figure = Figure(constrained_layout=True)
        self.canvas = ABFigureCanvas(self.figure)
        self.canvas.setMinimumHeight(0)
        self.canvas.setMinimumWidth(0)
        self.canvas.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.setMinimumWidth(0)

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
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        self.updateGeometry()

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802 (Qt API)
        sh = super().sizeHint()
        return QtCore.QSize(0, sh.height())

    def minimumSizeHint(self) -> QtCore.QSize:  # noqa: N802
        mh = super().minimumSizeHint()
        return QtCore.QSize(0, mh.height())

    def _device_pixel_ratio(self) -> float:
        if hasattr(self.canvas, "devicePixelRatioF"):
            return float(self.canvas.devicePixelRatioF())
        return float(self.canvas.devicePixelRatio())

    def _qt_physical_pixel_size(self) -> tuple[float, float]:
        """Device pixels allocated to the plot (matches matplotlib's Qt :meth:`resizeEvent`)."""
        dpr = self._device_pixel_ratio()
        cw = self.canvas.width()
        ch = self.canvas.height()
        if cw < 2:
            cw = self.width()
        if ch < 2:
            ch = self.height()
        cw = max(cw, 1)
        ch = max(ch, 1)
        return cw * dpr, ch * dpr

    def get_canvas_size_in_inches(self) -> tuple[float, float]:
        """Figure size must follow **Qt layout**, not :meth:`~matplotlib.backends.backend_agg.FigureCanvasAgg.get_width_height` (figure buffer), or scroll areas widen the window."""
        w_px, h_px = self._qt_physical_pixel_size()
        dpi = self.figure.dpi
        return (w_px / dpi, h_px / dpi)

    def sync_figure_to_widget(self) -> None:
        """Resize the figure to the drawable area the layout assigned (no ``forward`` resize of Qt)."""
        w_px, h_px = self._qt_physical_pixel_size()
        dpr = self._device_pixel_ratio()
        # After plot(), the canvas may not yet reflect setMinimumHeight(); don't squash tall figures.
        min_h = self.minimumHeight()
        if min_h > 0:
            h_px = max(h_px, float(min_h) * dpr)
        w_px = max(w_px, 1.0)
        h_px = max(h_px, 1.0)
        dpi = self.figure.dpi
        self.figure.set_size_inches(w_px / dpi, h_px / dpi, forward=False)
        self.canvas.draw_idle()

    def _schedule_figure_sync(self) -> None:
        """After ``plot()`` the widget often has not been laid out yet; sync on next event-loop tick."""
        QtCore.QTimer.singleShot(0, self.sync_figure_to_widget)

    def set_minimum_height_for_figure_inches(self, height_inches: float) -> None:
        """Minimum Qt height (logical px) so tall figures scroll inside :class:`QScrollArea`."""
        phy_px = height_inches * self.figure.dpi
        logical = max(int(math.ceil(phy_px / self._device_pixel_ratio())), 1)
        self.setMinimumHeight(logical)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._schedule_figure_sync()

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

