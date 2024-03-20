from PySide2 import QtWidgets, QtGui, QtCore


class ABAction(QtWidgets.QAction):
    icon: QtGui.QIcon
    title: str
    tool_tip: str = None

    def __init__(self, parent, **kwargs):
        super().__init__(self.icon, self.title, parent)
        self.kwargs = kwargs

        self.triggered.connect(self.onTrigger)
        self.toggled.connect(self.onToggle)

        if self.tool_tip:
            self.setToolTip(self.tool_tip)

    def __getattr__(self, name: str):
        # immediate return if not found
        if name not in self.kwargs.keys():
            raise AttributeError

        # get the associated value
        value = self.kwargs[name]

        # if the kwarg is a getter, call and return, else just return
        if callable(value): return value()
        else: return value

    def onTrigger(self, checked):
        raise NotImplementedError

    def onToggle(self, checked):
        raise NotImplementedError

    def get_button(self) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self.parent())
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        button.setDefaultAction(self)
        return button
