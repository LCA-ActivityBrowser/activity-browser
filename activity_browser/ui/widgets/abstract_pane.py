from qtpy import QtWidgets

from .dock_widget import ABDockWidget


class ABAbstractPane(QtWidgets.QWidget):
    title: str
    hideMode: ABDockWidget.HideMode

    def getDockWidget(self, main_window: QtWidgets.QMainWindow):
        dock_widget = ABDockWidget(self.title, parent=main_window, mode=self.hideMode)
        dock_widget.setWidget(self)
        return dock_widget
