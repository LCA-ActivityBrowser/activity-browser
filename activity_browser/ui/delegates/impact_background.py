"""Delegate that tints table cells by signed impact magnitude.

Used by the Contribution Tree tab for percentage columns. Intensity uses a
log scale focused on the 1%–100% range so 1 / 10 / 50 / 100 read clearly
apart, still as a plain translucent color fill (no custom bar widgets).
"""

from __future__ import annotations

import math

from qtpy import QtCore, QtGui, QtWidgets


def impact_intensity_fraction(
    value: float,
    column_max: float,
    *,
    floor_ratio: float = 0.01,
) -> float:
    """Map ``|value|`` to ``[0, 1]`` on a log10 axis from ``floor`` to ``column_max``.

    Default ``floor_ratio=0.01`` puts the floor at 1% when ``column_max`` is 100,
    so 1 → 0, 10 → ~0.5, 50 → ~0.85, 100 → 1. Values below the floor share the
    minimum intensity.
    """
    if column_max <= 0 or value == 0:
        return 0.0
    lo = max(abs(column_max) * floor_ratio, 1e-12)
    hi = abs(column_max)
    if lo >= hi:
        return 1.0 if abs(value) >= hi else 0.0
    v = min(max(abs(value), lo), hi)
    return (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))


class ImpactBackgroundDelegate(QtWidgets.QStyledItemDelegate):
    """Paint a translucent full-cell background from a signed numeric value.

    Tint intensity uses :func:`impact_intensity_fraction` (log-scaled).
    Positive and negative hues are configurable (e.g. red for cumulative %,
    blue for direct %).

    Parameters
    ----------
    column_max:
        Maximum absolute value in the column — used to scale tint intensity.
    positive_rgb:
        RGB triple for positive (burden) values.
    negative_rgb:
        RGB triple for negative (credit) values.
    parent:
        Optional Qt parent.
    """

    VALUE_ROLE = QtCore.Qt.UserRole + 10

    def __init__(
        self,
        column_max: float = 100.0,
        positive_rgb: tuple[int, int, int] = (210, 85, 85),
        negative_rgb: tuple[int, int, int] = (85, 170, 95),
        parent=None,
    ):
        super().__init__(parent)
        self.column_max = column_max
        self.positive_rgb = positive_rgb
        self.negative_rgb = negative_rgb

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        self.initStyleOption(option, index)
        painter.save()

        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, option.widget)

        value = index.data(self.VALUE_ROLE)
        tint = self._impact_tint(value)
        if tint is not None:
            painter.fillRect(option.rect, tint)

        text = index.data(QtCore.Qt.DisplayRole)
        if text is not None:
            text_rect = option.rect.adjusted(4, 0, -4, 0)
            palette = option.palette
            if option.state & QtWidgets.QStyle.State_Selected:
                colour = palette.highlightedText().color()
            else:
                colour = palette.text().color()
            painter.setPen(colour)
            painter.drawText(
                text_rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                str(text),
            )

        painter.restore()

    def _impact_tint(self, value) -> QtGui.QColor | None:
        if value is None or not isinstance(value, (int, float)) or value == 0:
            return None
        if self.column_max <= 0:
            return None

        fraction = impact_intensity_fraction(value, self.column_max)
        # Strong span: near-transparent at floor → nearly solid at max
        alpha = int(25 + 200 * fraction)
        r, g, b = self.positive_rgb if value > 0 else self.negative_rgb
        return QtGui.QColor(r, g, b, min(alpha, 230))
