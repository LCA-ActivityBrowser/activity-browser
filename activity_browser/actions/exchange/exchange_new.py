from typing import List

from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import commontasks
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ExchangeNew(ABAction):
    """
    ABAction to create a new exchange for an activity.
    """

    icon = qicons.add
    text = "Add exchanges"

    @staticmethod
    @exception_dialogs
    def run(from_keys: List[tuple], to_key: tuple, type: str):
        to_activity = bd.get_activity(to_key)
        for from_key in from_keys:
            exchange = to_activity.new_exchange(input=from_key, type=type, amount=1)
            exchange.save()
