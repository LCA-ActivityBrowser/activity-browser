# -*- coding: utf-8 -*-
import math

from qtpy.QtWidgets import QStyledItemDelegate

from .float import FloatDelegate
from .uncertainty import UncertaintyDelegate


class ViewOnlyDelegate(QStyledItemDelegate):
    """Disable the editor functionality to allow specific columns of an
    editable table to be view-only.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def displayText(self, value, locale):
        try:
            value = float(value)
            if math.isnan(value):
                return ""
            return "{:.5g}".format(value)
        except ValueError:
            return str(value)
        except TypeError:
            # Unexpected object types (eg. parameters)
            return repr(value)

    def createEditor(self, parent, option, index):
        return None


class ViewOnlyFloatDelegate(FloatDelegate):
    """Correctly display float values without allowing modification."""

    def createEditor(self, parent, option, index):
        return None


class ViewOnlyUncertaintyDelegate(UncertaintyDelegate):
    """Correctly display uncertainty type without allowing modification."""

    def createEditor(self, parent, option, index):
        return None
