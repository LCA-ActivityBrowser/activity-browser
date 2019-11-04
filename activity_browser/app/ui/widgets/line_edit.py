# -*- coding: utf-8 -*-
from PySide2 import QtGui, QtWidgets

from ...signals import signals


class SignalledLineEdit(QtWidgets.QLineEdit):
    """Adapted from http://stackoverflow.com/questions/12182133/PyQt5-combine-textchanged-and-editingfinished-for-qlineedit"""
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


class SignalledPlainTextEdit(QtWidgets.QPlainTextEdit):
    """Adapted from https://john.nachtimwald.com/2009/08/19/better-qplaintextedit-with-line-numbers/"""
    def __init__(self, key, field, contents='', parent=None):
        super(SignalledPlainTextEdit, self).__init__(contents, parent)
        self.highlight()
        self.cursorPositionChanged.connect(self.highlight)
        self._before = contents
        self._key = key
        self._field = field

    def highlight(self):
        selection = QtWidgets.QTextEdit.ExtraSelection()
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

    # def adjust_size(self):
    #     """ A way to reduce the height of the TextEdit. Could be implemented better.
    #     Based on: https://stackoverflow.com/questions/9506586/qtextedit-resize-to-fit
    #     """
    #     font = self.document().defaultFont()  # or another font if you change it
    #     fontMetrics = QtGui.QFontMetrics(font)  # a QFontMetrics based on our font
    #     textSize = fontMetrics.size(0, self._before)
    #     # textWidth = textSize.width() + 30  # constant may need to be tweaked
    #     textHeight = textSize.height() + 30  # constant may need to be tweaked
    #     self.setMaximumHeight(textHeight)
    #     # print('TextEdit Width/Height: {}/{}'.format(self.width(), self.height()))
    #     # print('Text Width/Height: {}/{}'.format(textWidth, textHeight))
    #     # print('DocSize:', self.document().size())


class SignalledComboEdit(QtWidgets.QComboBox):
    # based on SignalledPlainTextEdit.
    # Could be moved to new file. Or better: this file renamed to be more inclusive
    # needed to effectively implement the location dropdown list

    def __init__(self, key, field, contents='', parent=None):
        super().__init__()
        self._before = contents
        self._key = key
        self._field = field

    def focusOutEvent(self, event):
        after = self.currentText()
        if self._before != after:
            self._before = after
            signals.activity_modified.emit(self._key, self._field, after)
        super(SignalledComboEdit, self).focusOutEvent(event)

    # def showPopup(self):
    #     """Overrides the base class function."""
    #     self.populate_combobox.emit()
    #     super(SignalledComboEdit, self).showPopup()