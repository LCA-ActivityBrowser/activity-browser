from qtpy import QtWidgets
from typing import Callable


class ABMenu(QtWidgets.QMenu):
    menuSetup: list[Callable[["ABMenu"], None]]
    title: str = None

    def __init__(self, pos, parent=None):
        super().__init__(parent)

        for item in self.menuSetup:
            item(self)

    def add(self, action, *args, enable=True, **kwargs):
        qaction = action.get_QAction(*args, parent=self, **kwargs)
        qaction.setEnabled(enable)
        self.addAction(qaction)
