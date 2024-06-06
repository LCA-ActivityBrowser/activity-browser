from PySide2 import QtWidgets, QtGui, QtCore
from activity_browser import application


class ABAction:
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
    def get_QAction(cls, *args, **kwargs) -> QtWidgets.QAction:
        action = QtWidgets.QAction(cls.icon, cls.text, None)
        action.setToolTip(cls.tooltip)

        action.triggered.connect(lambda: cls.triggered(*args, **kwargs))

        return action

    @classmethod
    def get_QButton(cls, *args, **kwargs):
        """Convenience function to return a button that has this ABAction as default action."""
        button = QtWidgets.QToolButton(None)
        action = cls.get_QAction(*args, **kwargs)

        button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        button.setDefaultAction(action)
        return button


def exception_dialogs(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            QtWidgets.QMessageBox.critical(application.main_window,
                                           f"An error occurred: {type(e).__name__}",
                                           f"An error occurred, check the logs for more information \n\n {str(e)}",
                                           QtWidgets.QMessageBox.Ok
                                           )
            raise e
    return wrapper

