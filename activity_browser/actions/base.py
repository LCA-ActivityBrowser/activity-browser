from PySide2 import QtCore, QtGui, QtWidgets

from activity_browser import application
from activity_browser.i18n import _


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
        action = QtWidgets.QAction(cls.icon, _(cls.text) if cls.text else "", None)
        tooltip = cls.tooltip or getattr(cls, "tool_tip", None)
        action.setToolTip(_(tooltip) if tooltip else "")

        action.triggered.connect(lambda: cls.triggered(*args, **kwargs))

        return action

    @classmethod
    def get_QButton(cls, *args, **kwargs):
        """Convenience function to return a button that has this ABAction as default action."""
        button = QtWidgets.QPushButton(
            cls.icon,
            _(cls.text) if cls.text else "",
        )
        button.clicked.connect(lambda x: cls.triggered(*args, **kwargs))
        return button


def exception_dialogs(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                application.main_window,
                _(
                    "An error occurred: {error_type}",
                    error_type=type(e).__name__,
                ),
                _(
                    "An error occurred, check the logs for more information\n\n{error}",
                    error=str(e),
                ),
                QtWidgets.QMessageBox.Ok,
            )
            raise e

    return wrapper
