from bw2data.backends.peewee import Activity
from bw2data import get_activity
from PySide2.QtCore import QObject, Signal, SignalInstance

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata
from .exchange import ABExchange, ABExchanges, exchange_controller


class ABActivity(Activity):
    @classmethod
    def from_activity(cls, activity: Activity) -> "ABActivity":
        return cls(activity._document)

    def save(self) -> None:
        super().save()

        # legacy
        AB_metadata.update_metadata(self.key)
        signals.calculation_setup_changed.emit()

        activity_controller.activity_changed.emit(self)

    def delete(self) -> None:
        super().delete()

        # legacy
        AB_metadata.update_metadata(self.key)
        signals.calculation_setup_changed.emit()

        activity_controller.activity_deleted.emit(self)

    def copy(self, code=None, **kwargs) -> "ABActivity":
        activity = super().copy(code, **kwargs)

        # legacy
        AB_metadata.update_metadata(activity.key)

        activity_controller.new_activity.emit(activity)

        return ABActivity.from_activity(activity)

    # Exchange getters
    def exchanges(self) -> ABExchanges:
        return ABExchanges(self.key)

    def technosphere(self, include_substitution=True) -> ABExchanges:
        kinds = (("technosphere", "substitution") if include_substitution else ("technosphere",))
        return ABExchanges(self.key, kinds=kinds)

    def biosphere(self) -> ABExchanges:
        return ABExchanges(self.key, kinds=("biosphere",),)

    def production(self) -> ABExchanges:
        return ABExchanges(self.key, kinds=("production",),)

    def substitution(self) -> ABExchanges:
        return ABExchanges(self.key, kinds=("substitution",),)

    def upstream(self, kinds=("technosphere",)) -> ABExchanges:
        return ABExchanges(self.key, kinds=kinds, reverse=True)

    def rp_exchange(self) -> ABExchange:
        exchange = super().rp_exchange()
        return ABExchange.from_exchange(exchange)

    def new_exchange(self, **kwargs) -> ABExchange:
        """Create a new exchange linked to this activity"""
        exc = ABExchange()
        exc.output = self.key
        for key in kwargs:
            exc[key] = kwargs[key]
        exchange_controller.new_exchange.emit(exc)  # not too sure about this as the exchange hasn't been written yet
        return exc


class ActivityController(QObject):
    activity_changed: SignalInstance = Signal(ABActivity)
    activity_deleted: SignalInstance = Signal(ABActivity)
    new_activity: SignalInstance = Signal(ABActivity)

    _activity_changed_buffer = set()

    def __init__(self, parent=None):
        super().__init__(parent)
        exchange_controller.exchange_changed.connect(self._exchange_link)
        exchange_controller.exchange_deleted.connect(self._exchange_link)
        exchange_controller.new_exchange.connect(self._exchange_link)

    def _exchange_link(self, exchange: ABExchange) -> None:
        self._activity_changed_buffer.add(exchange.input)
        self._activity_changed_buffer.add(exchange.output)

        self.thread().eventDispatcher().awake.connect(self._process_buffer)

    def _process_buffer(self):
        """
        Function to process all the changed activities put in the buffer due to changed exchanges. Handy for bulk
        operations like activity deletions or copies.
        """
        # return when the buffer is (already) empty
        if not self._activity_changed_buffer: return

        for activity in self._activity_changed_buffer:
            self.activity_changed.emit(activity)

        self._activity_changed_buffer.clear()
        self.thread().eventDispatcher().awake.disconnect(self._process_buffer)

    def get(self, key: tuple) -> ABActivity:
        activity = get_activity(key)
        return ABActivity.from_activity(activity)


activity_controller = ActivityController(application)
