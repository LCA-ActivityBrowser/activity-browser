"""Legend hover tooltips on ABPlot."""

from __future__ import annotations


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
