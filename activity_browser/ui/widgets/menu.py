from qtpy import QtWidgets
from typing import Callable, Optional
from inspect import signature


class ABMenu(QtWidgets.QMenu):
    menuSetup: list[Callable[["ABMenu", QtWidgets.QWidget], None]]
    title: str = None

    def __init__(self, pos=None, parent=None, title: str = None):
        super().__init__(parent)

        for item in self.menuSetup:
            if len(signature(item).parameters) == 1:
                item(self)
            if len(signature(item).parameters) == 2:
                item(self, parent)

    def add(self, action, *args, enable=True, text=None, **kwargs):
        qaction = action.get_QAction(*args, parent=self, enabled=enable, text=text, **kwargs)
        self.addAction(qaction)

    def callback(self, text: str, func: Callable, args: list = None, kwargs: dict = None):
        args = args or []
        kwargs = kwargs or {}

        action = QtWidgets.QAction(text, self)
        action.triggered.connect(lambda: func(*args, **kwargs))
        self.addAction(action)
