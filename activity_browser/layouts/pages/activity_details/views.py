from logging import getLogger

from qtpy import QtWidgets, QtCore, QtGui

import bw2data as bd
import pandas as pd

from activity_browser import actions
from activity_browser.ui.widgets import ABTreeView
from activity_browser.ui.tables import delegates

from .items import ConsumersItem

log = getLogger(__name__)

EXCHANGE_MAP = {
    "natural resource": "biosphere", "emission": "biosphere", "inventory indicator": "biosphere",
    "economic": "biosphere", "social": "biosphere", "product": "technosphere",
    "processwithreferenceproduct": "technosphere", "waste": "technosphere",
}





class ConsumersView(ABTreeView):
    def mouseDoubleClickEvent(self, event) -> None:
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ConsumersItem)]
        keys = list({i["_consumer_key"] for i in items})
        if keys:
            actions.ActivityOpen.run(keys)

