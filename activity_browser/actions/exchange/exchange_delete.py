from typing import List, Any

from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons


class ExchangeDelete(NewABAction):
    """
    ABAction to delete one or more exchanges from an activity.
    """
    icon = qicons.delete
    text = "Delete exchange(s)"

    @staticmethod
    def run(exchanges: List[Any]):
        for exchange in exchanges:
            exchange.delete()
