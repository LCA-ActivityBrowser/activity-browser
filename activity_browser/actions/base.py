from PySide2 import QtWidgets, QtGui, QtCore
from activity_browser import application


def dialog_on_error(func):
    def function(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as exception:
            QtWidgets.QMessageBox.warning(
                application.main_window,
                "An error occured",
                exception.args[0]
            )
            raise exception

    return function


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

        self.triggered.connect(lambda checked: self.onTrigger(checked))
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
        """Function to be called when the action is triggered, implement in subclass"""
        raise NotImplementedError

    def onToggle(self, checked):
        """Function to be called when the action is toggled, implement in subclass"""
        raise NotImplementedError

    def get_button(self) -> QtWidgets.QToolButton:
        """Convenience function to return a button that has this ABAction as default action."""
        button = QtWidgets.QToolButton(self.parent())
        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        button.setDefaultAction(self)
        return button


