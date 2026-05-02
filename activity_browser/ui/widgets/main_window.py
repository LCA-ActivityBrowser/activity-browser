from typing import TYPE_CHECKING
from loguru import logger

from qtpy import QtCore, QtWidgets

if TYPE_CHECKING:
    from .abstract_pane import ABAbstractPane


class ABMainWindow(QtWidgets.QMainWindow):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, parent=None):
        if self._initialized:
            return
        self._initialized = True

        super().__init__(parent)

        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setDockNestingEnabled(True)

    def clearPanes(self):
        for pane in self.panes():
            logger.debug(f"Clearing pane {pane.__class__.__name__}: {id(pane)}")
            pane.hide()
            pane.deleteLater()

    def addPane(self, pane: "ABAbstractPane", area=QtCore.Qt.DockWidgetArea.LeftDockWidgetArea):
        """
        Add a pane to the main window as a dock widget.
        """
        dock_widget = pane.getDockWidget()
        self.addDockWidget(area, dock_widget)
        dock_widget.show()
        pane.sync()

    def panes(self):
        """
        Return a list of all panes in the main window.
        """
        from .abstract_pane import ABAbstractPane
        return self.findChildren(ABAbstractPane)
