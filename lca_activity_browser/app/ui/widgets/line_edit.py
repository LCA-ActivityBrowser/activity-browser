# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from ...signals import signals
from PyQt4 import QtCore, QtGui


class SignalledLineEdit(QtGui.QLineEdit):
    """Adapted from http://stackoverflow.com/questions/12182133/pyqt4-combine-textchanged-and-editingfinished-for-qlineedit"""
    def __init__(self, key, field, contents='', parent=None):
        super(SignalledLineEdit, self).__init__(contents, parent)
        self.editingFinished.connect(self._editing_finished)
        self.textChanged.connect(self._text_changed)
        self._before = contents
        self._key = key
        self._field = field

    def _text_changed(self, text):
        """Reset 'before' value when changing via Python"""
        if not self.hasFocus():
            self._before = text

    def _editing_finished(self):
        after = self.text()
        if self._before != after:
            self._before = after
            signals.activity_modified.emit(self._key, self._field, after)


class SignalledPlainTextEdit(QtGui.QPlainTextEdit):
    """Adapted from https://john.nachtimwald.com/2009/08/19/better-qplaintextedit-with-line-numbers/"""
    def __init__(self, key, field, contents='', parent=None):
        super(SignalledPlainTextEdit, self).__init__(contents, parent)
        self.highlight()
        self.cursorPositionChanged.connect(self.highlight)
        self._before = contents
        self._key = key
        self._field = field

    def highlight(self):
        selection = QtGui.QTextEdit.ExtraSelection()
        selection.format.setBackground(self.palette().alternateBase())
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def focusOutEvent(self, event):
        after = self.toPlainText()
        if self._before != after:
            self._before = after
            signals.activity_modified.emit(self._key, self._field, after)
        super(SignalledPlainTextEdit, self).focusOutEvent(event)
