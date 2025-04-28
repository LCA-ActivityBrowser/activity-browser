from qtpy import QtWidgets

from activity_browser import signals

from .dock_widget import ABDockWidget


class ABAbstractPane(QtWidgets.QWidget):
    title: str
    name = "abstract_pane"
    hideMode: ABDockWidget.HideMode

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName(self.name)

        if self.hideMode == ABDockWidget.HideMode.Close:
            signals.project.changed.connect(self.deleteLater)

    def getDockWidget(self, main_window: QtWidgets.QMainWindow):
        dock_widget = ABDockWidget(self.title, parent=main_window, mode=self.hideMode)
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

    @classmethod
    def fromState(cls, state: dict, parent=None):
        """
        Restore the state of the pane.
        """
        return cls(parent=parent)
