from qtpy import QtWidgets, QtGui, QtCore

from activity_browser import application, bwutils
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

from bw_functional import Function


class FunctionSubstitute(ABAction):
    """
    ABAction to open one or more supplied activities in an activity tab by employing signals.

    TODO: move away from using signals like this. Probably add a method to the MainWindow to add a panel instead.
    """

    icon = qicons.edit
    text = "Substitute Function"

    @staticmethod
    @exception_dialogs
    def run(function: tuple | int | Function, substitute: tuple | int | Function):
        function = bwutils.refresh_node(function)
        substitute = bwutils.refresh_node(substitute)

        if not isinstance(function, Function):
            return

        if function.get("substitutor") == substitute.key:
            return

        function.substitute(substitute.key)
        function.save()
