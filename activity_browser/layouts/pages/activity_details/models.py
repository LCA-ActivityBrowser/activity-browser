from activity_browser.ui.widgets import ABAbstractItemModel

from .items import ExchangeItem


class ExchangeModel(ABAbstractItemModel):
    dataItemClass = ExchangeItem
