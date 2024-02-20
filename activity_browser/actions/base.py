from PySide2 import QtWidgets, QtGui


class ABAction(QtWidgets.QAction):
    icon: QtGui.QIcon
    title: str
    tool_tip: str = None
    depends = []

    def __init__(self, parent):
        self.check_dependencies(parent)
        super().__init__(self.icon, self.title, parent)

        self.triggered.connect(self.onTrigger)
        self.toggled.connect(self.onToggle)

        if self.tool_tip:
            self.setToolTip(self.tool_tip)

    def check_dependencies(self, parent):
        for dependency in self.depends:
            if dependency not in dir(parent):
                raise AttributeError

    def onTrigger(self, checked):
        raise NotImplementedError

    def onToggle(self, checked):
        raise NotImplementedError
