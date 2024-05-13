from PySide2 import QtWidgets
from PySide2.QtCore import Slot
from PySide2.QtGui import QTextFormat

from activity_browser import actions


class SignalledLineEdit(QtWidgets.QLineEdit):
    """Adapted from http://stackoverflow.com/questions/12182133/PyQt5-combine-textchanged-and-editingfinished-for-qlineedit"""
    def __init__(self, key, field, contents='', parent=None):
        super(SignalledLineEdit, self).__init__(contents, parent)
        self.editingFinished.connect(self._editing_finished)
        self.textChanged.connect(self._text_changed)
        self._before = contents
        self._key = key
        self._field = field

    @Slot(str, name="customTextChanged")
    def _text_changed(self, text: str) -> None:
        """Reset 'before' value when changing via Python"""
        if not self.hasFocus():
            self._before = text

    @Slot(name="customEditFinish")
    def _editing_finished(self) -> None:
        after = self.text()
        if self._before != after:
            self._before = after
            actions.ActivityModify.run(self._key, self._field, after)


class SignalledPlainTextEdit(QtWidgets.QPlainTextEdit):
    """Adapted from https://john.nachtimwald.com/2009/08/19/better-qplaintextedit-with-line-numbers/"""
    def __init__(self, key: tuple, field: str, contents: str = "", parent=None):
        super().__init__(contents, parent)
        self.highlight()
        self.cursorPositionChanged.connect(self.highlight)
        self._before = contents
        self._key = key
        self._field = field

    @Slot(name="highlight")
    def highlight(self):
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.format.setBackground(self.palette().alternateBase())
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def focusOutEvent(self, event):
        after = self.toPlainText()
        if self._before != after:
            actions.ActivityModify.run(self._key, self._field, after)
        super().focusOutEvent(event)

    def refresh_text(self, text: str) -> None:
        self._before = text
        self.setPlainText(text)


class SignalledComboEdit(QtWidgets.QComboBox):
    """Based on SignalledPlainTextEdit.

    Could be moved to new file. Or better: this file renamed to be more inclusive
    needed to effectively implement the location dropdown list
    """

    def __init__(self, key, field, contents='', parent=None):
        super().__init__(parent)
        self._before = contents
        self._key = key
        self._field = field

    def focusOutEvent(self, event):
        after = self.currentText()
        if self._before != after:
            self._before = after
            actions.ActivityModify.run(self._key, self._field, after)
        super(SignalledComboEdit, self).focusOutEvent(event)
