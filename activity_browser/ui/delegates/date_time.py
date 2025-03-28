import datetime
import arrow

from qtpy import QtCore, QtGui, QtWidgets


class DateTimeDelegate(QtWidgets.QStyledItemDelegate):
    """For managing and validating entered float values."""

    def displayText(self, value, locale):
        tz = datetime.datetime.now(datetime.timezone.utc).astimezone()
        time_shift = -tz.utcoffset().total_seconds()
        value = arrow.get(value).shift(seconds=time_shift).humanize()
        return value
