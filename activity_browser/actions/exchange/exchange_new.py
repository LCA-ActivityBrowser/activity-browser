from typing import List

from activity_browser.bwutils import commontasks
from activity_browser.brightway import bd
from activity_browser.actions.base import NewABAction
from activity_browser.ui.icons import qicons


class ExchangeNew(NewABAction):
    """
    ABAction to create a new exchange for an activity.
    """
    icon = qicons.add
    text = "Add exchanges"

    @staticmethod
    def run(from_keys: List[tuple], to_key: tuple):
        to_activity = bd.get_activity(to_key)
        for from_key in from_keys:
            exchange = to_activity.new_exchange(input=from_key, amount=1)

            technosphere_db = commontasks.is_technosphere_db(from_key[0])
            if technosphere_db is True:
                exchange['type'] = 'technosphere'
            elif technosphere_db is False:
                exchange['type'] = 'biosphere'
            else:
                exchange['type'] = 'unknown'

            exchange.save()
