from qtpy import QtWidgets

from activity_browser import signals

from .dock_widget import ABDockWidget


class ABAbstractPane(QtWidgets.QWidget):
    title: str
    hideMode: ABDockWidget.HideMode

    def __init__(self, parent=None):
        super().__init__(parent)

        if self.hideMode == ABDockWidget.HideMode.Close:
            signals.project.changed.connect(self.deleteLater)


    def getDockWidget(self, main_window: QtWidgets.QMainWindow):
        dock_widget = ABDockWidget(self.title, parent=main_window, mode=self.hideMode)
        dock_widget.setWidget(self)
        return dock_widget
