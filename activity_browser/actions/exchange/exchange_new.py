from typing import Union, Callable, List

from PySide2 import QtCore

from activity_browser.bwutils import commontasks
from activity_browser.brightway.bw2data import get_activity

from ..base import ABAction
from ...ui.icons import qicons


class ExchangeNew(ABAction):
    """
    ABAction to create a new exchange for an activity.
    """
    icon = qicons.add
    title = "Add exchanges"
    from_keys: List[tuple]
    to_key: tuple

    def __init__(self,
                 from_keys: Union[List[tuple], Callable],
                 to_key: Union[tuple, Callable],
                 parent: QtCore.QObject
                 ):
        super().__init__(parent, from_keys=from_keys, to_key=to_key)

    def onTrigger(self, toggled):
        to_activity = get_activity(self.to_key)
        for from_key in self.from_keys:
            exchange = to_activity.new_exchange(input=from_key, amount=1)

            technosphere_db = commontasks.is_technosphere_db(from_key[0])
            if technosphere_db is True:
                exchange['type'] = 'technosphere'
            elif technosphere_db is False:
                exchange['type'] = 'biosphere'
            else:
                exchange['type'] = 'unknown'

            exchange.save()
