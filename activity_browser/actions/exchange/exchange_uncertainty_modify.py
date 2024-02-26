from typing import Union, Callable, List, Any

from PySide2 import QtCore

from activity_browser import application
from activity_browser.ui.wizards import UncertaintyWizard
from ..base import ABAction
from ...ui.icons import qicons


class ExchangeUncertaintyModify(ABAction):
    icon = qicons.edit
    title = "Modify uncertainty"
    exchanges: List[Any]

    def __init__(self, exchanges: Union[List[Any], Callable], parent: QtCore.QObject):
        super().__init__(parent, exchanges=exchanges)

    def onTrigger(self, toggled):
        wizard = UncertaintyWizard(self.exchanges[0], application.main_window)
        wizard.show()
