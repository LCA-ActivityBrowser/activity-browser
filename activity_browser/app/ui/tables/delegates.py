# -*- coding: utf-8 -*-
from PyQt5.QtGui import QDoubleValidator, QRegExpValidator
from PyQt5.QtWidgets import QItemDelegate, QLineEdit


class FloatDelegate(QItemDelegate):
    """ For validating entered float values
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setValidator(QDoubleValidator())
        return editor


class StringDelegate(QItemDelegate):
    """ For validating entered string values
    """
    def __init__(self, parent=None, regex=None):
        super().__init__(parent)
        self.regex = regex

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        if self.regex:
            editor.setValidator(QRegExpValidator(self.regex))
        return editor
