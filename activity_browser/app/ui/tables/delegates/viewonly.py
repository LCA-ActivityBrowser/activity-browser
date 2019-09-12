# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QStyledItemDelegate


class ViewOnlyDelegate(QStyledItemDelegate):
    """ Disable the editor functionality to allow specific columns of an
    editable table to be view-only.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        return None
