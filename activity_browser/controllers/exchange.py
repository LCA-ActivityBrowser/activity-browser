from bw2data.backends.peewee.proxies import Exchanges, Exchange
from PySide2.QtCore import QObject, Signal, SignalInstance

from activity_browser import application


class ABExchange(Exchange):
    @classmethod
    def from_exchange(cls, exchange: Exchange) -> "ABExchange":
        return cls(exchange._document)

    def save(self) -> None:
        super().save()
        exchange_controller.exchange_changed.emit(self)

    def delete(self) -> None:
        super().delete()
        exchange_controller.exchange_deleted.emit(self)

    def _get_input(self):
        from .activity import ABActivity
        return ABActivity.from_activity(super().input)

    def _set_input(self, value):
        exchange_controller.moving_exchange.emit(self)
        super()._set_input(value)
        exchange_controller.exchange_changed.emit(self)

    def _get_output(self):
        from .activity import ABActivity
        return ABActivity.from_activity(super().output)

    def _set_output(self, value):
        exchange_controller.moving_exchange.emit(self)
        super()._set_output(value)
        exchange_controller.exchange_changed.emit(self)


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
    moving_exchange: SignalInstance = Signal(ABExchange)


exchange_controller = ExchangeController(application)
