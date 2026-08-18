"""Legend hover tooltips on ABPlot."""

from __future__ import annotations

from activity_browser import app  # noqa: F401  — ABApplication before pytest-qt's QApplication


def test_legend_tooltip_on_colored_handle():
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.backend_bases import MouseEvent
    from qtpy import QtWidgets

    from activity_browser.ui.widgets.plot import ABPlot

    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])

    full_label = "product A | process A | GLO | db"
    plot = ABPlot()
    plot.reset_plot()
    plot.ax.bar([0], [1], label="short…")
    plot.add_legend()
    plot._tooltip_legend = [full_label]
    plot.figure.canvas.draw()

    legend = plot.ax.get_legend()
    assert legend is not None
    handle = legend.legend_handles[0]
    renderer = plot.figure.canvas.get_renderer()
    bbox = handle.get_window_extent(renderer)
    event = MouseEvent(
        "motion_notify_event",
        plot.figure.canvas,
        (bbox.x0 + bbox.x1) / 2,
        (bbox.y0 + bbox.y1) / 2,
    )

    assert plot._legend_tooltip(event) == full_label


def test_legend_tooltip_on_legend_text():
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib.backend_bases import MouseEvent
    from qtpy import QtWidgets

    from activity_browser.ui.widgets.plot import ABPlot

    if QtWidgets.QApplication.instance() is None:
        QtWidgets.QApplication([])

    full_label = "product A | process A | GLO | db"
    plot = ABPlot()
    plot.reset_plot()
    plot.ax.bar([0], [1], label="short…")
    plot.add_legend()
    plot._tooltip_legend = [full_label]
    plot.figure.canvas.draw()

    legend = plot.ax.get_legend()
    assert legend is not None
    text = legend.get_texts()[0]
    renderer = plot.figure.canvas.get_renderer()
    bbox = text.get_window_extent(renderer)
    event = MouseEvent(
        "motion_notify_event",
        plot.figure.canvas,
        (bbox.x0 + bbox.x1) / 2,
        (bbox.y0 + bbox.y1) / 2,
    )

    assert plot._legend_tooltip(event) == full_label


def test_collapsed_canvas_resize_does_not_warn(qtbot, main_window):
    """Qt often resizes plots through 0×0; constrained_layout must not run then."""
    import warnings

    from qtpy.QtCore import QSize
    from qtpy.QtGui import QResizeEvent

    from activity_browser.ui.widgets.plot import ABPlot

    plot = ABPlot()
    plot.reset_plot()
    plot.ax.bar([0, 1], [1.0, 2.0], label="series")
    plot.add_legend(loc="upper left", bbox_to_anchor=(1.02, 1))
    qtbot.addWidget(plot)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        plot.canvas.resizeEvent(QResizeEvent(QSize(1, 1), QSize(400, 300)))
        qtbot.wait(20)

    assert not any(
        "constrained_layout not applied" in str(w.message) for w in caught
    )
