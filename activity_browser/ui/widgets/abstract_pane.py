import re

from qtpy import QtWidgets

from .dock_widget import ABDockWidget
from .main_window import ABMainWindow


class ABAbstractPane(QtWidgets.QWidget):
    title: str = None
    name: str = None
    unique: bool = False  # whether the pane is unique in the application

    def __init__(self, parent: ABMainWindow):
        super().__init__(parent)
        self.name = self.name or re.sub(r'([a-z])([A-Z])', r'\1_\2', self.__class__.__name__).lower()
        self.title = self.title or self.name

        self.setObjectName(self.name)
        self.setWindowTitle(self.title)

        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)

        hide_mode = ABDockWidget.HideMode.Hide if self.unique else ABDockWidget.HideMode.Close
        self.dock_widget = ABDockWidget(self.title, parent=self.parent(), mode=hide_mode)
        self.dock_widget.setWidget(self)

    def parent(self) -> ABMainWindow:
        return super().parent()

    def hide(self):
        """
        Hide the pane's dock widget.
        """
        self.dock_widget.hide()

    def getDockWidget(self):
        return self.dock_widget

    def toggleViewAction(self):
        """
        Create a toggle view action for this pane.

        Returns:
            QtWidgets.QAction: The toggle view action for this pane.
        """
        return self.dock_widget.toggleViewAction()

    def sync(self):
        """
        Synchronize the pane with the current state of Brightway.
        """
        pass
