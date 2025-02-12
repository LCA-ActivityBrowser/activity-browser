from activity_browser.ui.widgets import ABAbstractItemModel

from .items import ExchangesItem, ConsumersItem


class ExchangesModel(ABAbstractItemModel):
    dataItemClass = ExchangesItem


class ConsumersModel(ABAbstractItemModel):
    dataItemClass = ConsumersItem
