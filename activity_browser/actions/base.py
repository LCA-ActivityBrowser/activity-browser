from logging import getLogger
from qtpy import QtCore, QtGui, QtWidgets

from activity_browser import application

log = getLogger(__name__)


class ABAction:
    icon = QtGui.QIcon()
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
    def get_QAction(cls, *args, parent=None, text=None, enabled=True, **kwargs) -> QtWidgets.QAction:
        text = text or cls.text
        action = QtWidgets.QAction(cls.icon, text, parent, enabled=enabled)
        action.setToolTip(cls.tooltip)

        action.triggered.connect(lambda: cls.triggered(*args, **kwargs))

        return action

    @classmethod
    def get_QButton(cls, *args, **kwargs):
        """Convenience function to return a button that has this ABAction as default action."""
        button = QtWidgets.QPushButton(
            cls.icon,
            cls.text
        )
        button.clicked.connect(lambda x: cls.triggered(*args, **kwargs))
        return button


def exception_dialogs(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            if not hasattr(e, "dialog_flag"):
                setattr(e, "dialog_flag", True)
                QtWidgets.QMessageBox.critical(
                    application.main_window,
                    f"An error occurred: {type(e).__name__}",
                    f"An error occurred, check the logs for more information \n\n {str(e)}",
                    QtWidgets.QMessageBox.Ok,
                )
            raise e

    return wrapper
