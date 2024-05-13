from PySide2 import QtWidgets, QtGui, QtCore


class ABAction(QtWidgets.QAction):
    """
    Base class for ABActions. Superclasses QActions so feel free to supply icons, titles, tooltips etcetera.

    During init keyword-arguments are set as attributes to the class, so they can be retrieved by a trigger/toggle
    callback. Action arguments can either be passed as direct values, or as getter functions. When the argument is
    then accessed through ABAction.argumentname the value is either returned directly, or in the case of a function,
    retrieved and then returned.
    """
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
        """Fuction to be called when the action is triggered, implement in subclass"""
        raise NotImplementedError

    def onToggle(self, checked):
        """Fuction to be called when the action is toggled, implement in subclass"""
        raise NotImplementedError

    def get_button(self) -> QtWidgets.QToolButton:
        """Convenience function to return a button that has this ABAction as default action."""
        button = QtWidgets.QToolButton(self.parent())
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        button.setDefaultAction(self)
        return button


class NewABAction:
    icon: QtGui.QIcon = None
    text: str = None
    tooltip: str = None

    @staticmethod
    def run(*args, **kwargs):
        raise NotImplementedError

    @classmethod
    def triggered(cls, *args, **kwargs):

        args = [arg if not callable(arg) else arg() for arg in args]
        kwargs = {k: v if not callable(v) else v() for k, v in kwargs.items()}

        cls.run(*args, **kwargs)

    @classmethod
    def get_action(cls, *args, **kwargs) -> QtWidgets.QAction:
        action = QtWidgets.QAction(cls.icon, cls.text, None)
        action.setToolTip(cls.tooltip)

        action.triggered.connect(lambda: cls.triggered(*args, **kwargs))

        return action

    @classmethod
    def get_button(cls, *args, **kwargs):
        """Convenience function to return a button that has this ABAction as default action."""
        button = QtWidgets.QToolButton(None)
        action = cls.get_action(*args, **kwargs)

        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        button.setDefaultAction(action)
        return button
