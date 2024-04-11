from PySide2.QtCore import QObject, Signal, SignalInstance
from bw2data.backends.peewee.schema import ExchangeDataset

import activity_browser.bwutils.data as ABData
from activity_browser import application
from .base import VirtualDatapoint


class VirtualExchange(VirtualDatapoint):
    changed: SignalInstance = Signal(ABData.ABActivity)
    deleted: SignalInstance = Signal(ABData.ABActivity)

    @property
    def input(self):
        try:
            ds = ExchangeDataset.get_by_id(self.data_point.id)
            return ds.input_database, ds.input_code
        except:
            return None, None

    @property
    def output(self):
        try:
            ds = ExchangeDataset.get_by_id(self.data_point.id)
            return ds.ouput_database, ds.ouput_code
        except:
            return None, None


class ExchangeController(QObject):
    _dummy = VirtualExchange()

    def get_virtual(self, exchange: ABData.ABExchange, create=False) -> VirtualExchange:
        virtual_exchange = self.findChild(VirtualExchange, str(exchange.id))

        if virtual_exchange: return virtual_exchange
        elif create: return VirtualExchange(exchange.id, exchange, self)
        else: return self._dummy

    def changed(self, exchange: ABData.ABExchange):
        virtual_exchange = self.findChild(VirtualExchange, str(exchange.id))
        if not virtual_exchange: return
        virtual_exchange.changed.emit(exchange)

    def deleted(self, exchange: ABData.ABExchange):
        virtual_exchange = self.findChild(VirtualExchange, str(exchange.id))
        if not virtual_exchange: return
        virtual_exchange.deleted.emit(exchange)

    def get(self, exchange_id: int):
        return ABData.ABExchange(ExchangeDataset.get_by_id(exchange_id))


exchange_controller = ExchangeController(application)
