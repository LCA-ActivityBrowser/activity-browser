from typing import Any, List

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons


class ExchangeDelete(ABAction):
    """
    ABAction to delete one or more exchanges from an activity.
    """

    icon = qicons.delete
    text = "Delete exchange(s)"

    @staticmethod
    @exception_dialogs
    def run(exchanges: List[Any]):
        for exchange in exchanges:
            exchange.delete()
