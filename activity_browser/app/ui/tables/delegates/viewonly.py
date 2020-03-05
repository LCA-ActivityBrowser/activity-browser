# -*- coding: utf-8 -*-
import math

from PySide2.QtWidgets import QStyledItemDelegate


class ViewOnlyDelegate(QStyledItemDelegate):
    """ Disable the editor functionality to allow specific columns of an
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

    def createEditor(self, parent, option, index):
        return None
