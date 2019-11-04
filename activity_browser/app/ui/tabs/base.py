# -*- coding: utf-8 -*-
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QMessageBox, QWidget


class BaseRightTab(QWidget):
    """ Extremely basic widget, to be created and used inside a QTabWidget

    Contains an `explanation` slot which presents the `explain_text` inside a popup
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.explain_text = "I explain what happens here"

    def _connect_signals(self):
        """ Used by child classes to wire up specific functionality to signals

        Should only be used during init
        """
        raise NotImplementedError

    def _construct_layout(self):
        """ Used by child classes to construct the initial layout of the widget

        Usually, the function should end with a self.setLayout() call.

        Should only be used during init
        """
        raise NotImplementedError

    @Slot()
    def explanation(self):
        """ Builds and shows a message box containing whatever text is set
        on self.explain_text
        """
        return QMessageBox.question(
            self, "Explanation", self.explain_text, QMessageBox.Ok,
            QMessageBox.Ok
        )
