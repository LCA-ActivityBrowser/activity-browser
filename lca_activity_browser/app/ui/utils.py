# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtGui


class StdRedirector(object):
    # From http://stackoverflow.com/questions/17132994/pyside-and-python-logging/17145093#17145093
    def __init__(self, widget, out=None, color=None):
        """(edit, out=None, color=None) -> can write stdout, stderr to a
        QTextEdit.
        edit = QTextEdit
        out = alternate stream ( can be the original sys.stdout )
        color = alternate color (i.e. color stderr a different color)
        """
        self.edit_widget = widget
        self.out = out
        self.color = color

    def write(self, text):
        if self.color:
            original = self.edit_widget.textColor()
            self.edit_widget.setTextColor(self.color)

        self.edit_widget.moveCursor(QtGui.QTextCursor.End)
        self.edit_widget.insertPlainText(text )

        if self.color:
            self.edit_widget.setTextColor(original)

        if self.out:
            self.out.write(text)
