from activity_browser.ui.widgets import ABAbstractItemModel

from .items import ConsumersItem



class ConsumersModel(ABAbstractItemModel):
    dataItemClass = ConsumersItem
