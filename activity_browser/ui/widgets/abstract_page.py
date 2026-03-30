from qtpy import QtWidgets
from qtpy.QtCore import Signal, SignalInstance
import re


class ABAbstractPage(QtWidgets.QWidget):
    basePage = False
    name: str = None
    title: str = None

    visibilityChanged: SignalInstance = Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = self.name or re.sub(r'([a-z])([A-Z])', r'\1_\2', self.__class__.__name__).lower()
        self.title = self.title or self.name

        self.setObjectName(self.name)
        self.setWindowTitle(self.title)

        self.toggle_view_action = QtWidgets.QAction(self.title, self)
        self.toggle_view_action.setCheckable(True)
        self.toggle_view_action.setChecked(True)
        self.toggle_view_action.triggered.connect(lambda b: self.visibilityChanged.emit(b))

    def toggleViewAction(self):
        """
        Create a toggle view action for this page.

        Returns:
            QtWidgets.QAction: The toggle view action for this page.
        """
        return self.toggle_view_action
