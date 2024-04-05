from copy import deepcopy

from bw2data.backends.peewee.proxies import Exchanges, Exchange
from PySide2.QtCore import QObject, Signal, SignalInstance

from activity_browser import application


class ABExchange(Exchange):
    previous_state: dict = {}

    @classmethod
    def from_exchange(cls, exchange: Exchange) -> "ABExchange":
        ab_exchange = cls(exchange._document)
        ab_exchange.previous_state = deepcopy(exchange._document.data)
        return ab_exchange

    def save(self) -> None:
        super().save()
        exchange_controller.exchange_changed.emit(self)

    def delete(self) -> None:
        super().delete()
        exchange_controller.exchange_deleted.emit(self)

    def _get_input(self):
        from .activity import ABActivity
        return ABActivity.from_activity(super().input)

    def _get_output(self):
        from .activity import ABActivity
        return ABActivity.from_activity(super().output)


class ABExchanges(Exchanges):
    def __iter__(self):
        for obj in self._get_queryset():
            yield ABExchange(obj)

    def delete(self):
        for exchange in self:
            exchange.delete()


class ExchangeController(QObject):
    exchange_changed: SignalInstance = Signal(ABExchange)
    exchange_deleted: SignalInstance = Signal(ABExchange)
    new_exchange: SignalInstance = Signal(ABExchange)


exchange_controller = ExchangeController(application)
