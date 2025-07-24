import re

from qtpy import QtWidgets

from .dock_widget import ABDockWidget


class ABAbstractPane(QtWidgets.QWidget):
    title: str
    name: str = None
    unique: bool = False  # whether the pane is unique in the application

    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = self.name or re.sub(r'([a-z])([A-Z])', r'\1_\2', self.__class__.__name__).lower()
        self.setObjectName(self.name)
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)

    def getDockWidget(self, main_window: QtWidgets.QMainWindow):

        hidemode = ABDockWidget.HideMode.Hide if self.unique else ABDockWidget.HideMode.Close

        dock_widget = ABDockWidget(self.title, parent=main_window, mode=hidemode)
        dock_widget.setWidget(self)
        return dock_widget

    def sync(self):
        """
        Synchronize the pane with the current state of Brightway.
        """
        pass

    def saveState(self):
        """
        Save the state of the pane.
        """
        return {}

    def restoreState(self, state: dict):
        """
        Restore the state of the pane.
        """
        pass

    @classmethod
    def fromState(cls, state: dict, parent=None):
        """
        Restore the state of the pane.
        """
        pane = cls(parent=parent)
        pane.restoreState(state)
        return pane
