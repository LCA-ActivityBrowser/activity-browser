from PySide2 import QtWidgets
import sys

from ..panels import ABTab
from ...ui.style import header
from ...ui.utils import StdRedirector


class DebugTab(ABTab):

    def __init__(self, parent = None):
        super(DebugTab, self).__init__(parent)

        self.log = QtWidgets.QTextEdit(self)
        sys.stdout = StdRedirector(self.log, sys.stdout, None)
        sys.stderr = StdRedirector(self.log, sys.stderr, "blue")

        self.debug_display = QtWidgets.QVBoxLayout()
        self.title = header('Program debugger output:')

        self.debug_display.addWidget(self.title)
        self.debug_display.addWidget(self.log)

        self.setLayout(self.debug_display)
        self.setVisible(False)
