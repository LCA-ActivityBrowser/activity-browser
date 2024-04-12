from typing import List

from bw2data.backends import SQLiteBackend
from bw2data.backends.peewee.proxies import Activity, Exchange, Exchanges
from bw2data.method import Method
from PySide2.QtCore import SignalInstance

import activity_browser.controllers as ctrl
from activity_browser import signals
from .metadata import AB_metadata


class ABExchange(Exchange):
    moved_IO = []

    @classmethod
    def from_exchange(cls, exchange: Exchange) -> "ABExchange":
        ab_exchange = cls(exchange._document)
        return ab_exchange

    @property
    def changed(self) -> SignalInstance:
        return ctrl.exchange_controller.get_virtual(self, create=True).changed

    @property
    def deleted(self) -> SignalInstance:
        return ctrl.exchange_controller.get_virtual(self, create=True).deleted

    @property
    def id(self) -> int:
        return self._document.get_id()

    def save(self) -> None:
        super().save()
        ctrl.exchange_controller.changed(self)

        acts = set()

        acts.add(self.input)
        acts.add(self.output)
        acts.update(self.moved_IO)

        dbs = set()

        for activity in acts:
            dbs.add(activity["database"])
            ctrl.activity_controller.changed(activity)

        for db_name in dbs:
            db = ctrl.database_controller.get(db_name)
            ctrl.database_controller.changed(db)

        self.moved_IO.clear()

    def delete(self) -> None:
        super().delete()
        ctrl.exchange_controller.changed(self)
        ctrl.exchange_controller.deleted(self)

        ctrl.activity_controller.changed(self.input)
        ctrl.activity_controller.changed(self.output)

        in_db = ctrl.database_controller.get(self.input["database"])
        ctrl.database_controller.changed(in_db)

        out_db = ctrl.database_controller.get(self.output["database"])
        ctrl.database_controller.changed(out_db)

    def _get_input(self):
        return ABActivity.from_activity(super().input)

    def _set_input(self, value):
        if hash(value) is not hash(self.input):
            self.moved_IO.append(self.input)
        super()._set_input(value)

    def _get_output(self):
        return ABActivity.from_activity(super().output)

    def _set_output(self, value):
        if hash(value) is not hash(self.output):
            self.moved_IO.append(self.output)
        super()._set_output(value)


class ABExchanges(Exchanges):
    def __iter__(self):
        for obj in self._get_queryset():
            yield ABExchange(obj)

    def delete(self):
        for exchange in self:
            exchange.delete()


class ABActivity(Activity):

    @classmethod
    def from_activity(cls, activity: Activity) -> "ABActivity":
        return cls(activity._document)

    @property
    def changed(self) -> SignalInstance:
        return ctrl.activity_controller.get_virtual(self, create=True).changed

    @property
    def deleted(self) -> SignalInstance:
        return ctrl.activity_controller.get_virtual(self, create=True).deleted

    def save(self) -> None:
        super().save()

        # legacy
        AB_metadata.update_metadata(self.key)
        signals.calculation_setup_changed.emit()

        ctrl.activity_controller.changed(self)

        db = ctrl.database_controller.get(self["database"])
        ctrl.database_controller.changed(db)

    def delete(self) -> None:
        # exchange deletions are signalled through ABExchanges in the superclass
        super().delete()

        # legacy
        AB_metadata.update_metadata(self.key)
        signals.calculation_setup_changed.emit()

        ctrl.activity_controller.changed(self)
        ctrl.activity_controller.deleted(self)

    def copy(self, code=None, **kwargs) -> "ABActivity":
        activity = super().copy(code, **kwargs)
        ab_activity = self.from_activity(activity)

        # legacy
        AB_metadata.update_metadata(ab_activity.key)

        # copy creates a new activity, so update accordingly
        db = ctrl.database_controller.get(self["database"])
        ctrl.database_controller.changed(db)

        return ab_activity

    # Exchange getters
    def exchanges(self) -> ABExchanges:
        return ABExchanges(self.key)

    def technosphere(self, include_substitution=True) -> ABExchanges:
        kinds = (("technosphere", "substitution") if include_substitution else ("technosphere",))
        return ABExchanges(self.key, kinds=kinds)

    def biosphere(self) -> ABExchanges:
        return ABExchanges(self.key, kinds=("biosphere",), )

    def production(self) -> ABExchanges:
        return ABExchanges(self.key, kinds=("production",), )

    def substitution(self) -> ABExchanges:
        return ABExchanges(self.key, kinds=("substitution",), )

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
        return exc


class ABDatabase(SQLiteBackend):

    @classmethod
    def from_database(cls, database: SQLiteBackend) -> "ABDatabase":
        return cls(database.name)

    @property
    def changed(self) -> SignalInstance:
        return ctrl.database_controller.get_virtual(self, create=True).changed

    @property
    def deleted(self) -> SignalInstance:
        return ctrl.database_controller.get_virtual(self, create=True).deleted

    def __iter__(self) -> "ABActivity":
        for doc in self._get_queryset():
            yield ABActivity(doc)

    # mirroring database properties
    def process(self) -> None:
        super().process()
        ctrl.database_controller.sync()

    def register(self, **kwargs):
        super().register(**kwargs)
        ctrl.database_controller.sync()

    # methods for database manipulation
    def copy(self, name) -> "ABDatabase":
        database = super().copy(name)
        return self.from_database(database)

    def delete(self, keep_params=False, warn=True) -> None:
        # get all affected activities and exchanges that have virtual counterparts (i.e. have signals attached to them)
        acts = [ctrl.activity_controller.get(act.key)
                for act in ctrl.activity_controller.children()
                if act.key[0] == self.name]

        excs = [ctrl.exchange_controller.get(exc.id)
                for exc in ctrl.exchange_controller.children()
                if exc.input[0] == self.name or exc.output[0] == self.name]

        super().delete(keep_params, warn)

        # emit the deleted db, affected activities, and affected exchanges
        ctrl.database_controller.changed(self)
        ctrl.database_controller.deleted(self)

        for activity in acts: ctrl.activity_controller.changed(activity)
        for activity in acts: ctrl.activity_controller.deleted(activity)

        for exchange in excs: ctrl.exchange_controller.changed(exchange)
        for exchange in excs: ctrl.exchange_controller.deleted(exchange)

    # methods returning activity proxies
    def random(self, filters=True, true_random=False) -> ABActivity:
        activity = super().random(filters, true_random)
        return ABActivity.from_activity(activity)

    def get(self, code) -> ABActivity:
        activity = super().get(code)
        return ABActivity.from_activity(activity)

    def new_activity(self, code, **kwargs) -> ABActivity:
        activity = ABActivity()
        activity['database'] = self.name
        activity['code'] = str(code)
        activity['location'] = "GLO"
        activity.update(kwargs)

        # legacy
        AB_metadata.update_metadata(activity.key)

        return activity

    def search(self, string, **kwargs) -> List[ABActivity]:
        result = super().search(string, **kwargs)
        return [ABActivity.from_activity(activity) for activity in result]

    # methods directly changing data
    def write(self, data, process=True):
        super().write(data, process)
        ctrl.database_controller.changed(self)

        # no need to signal activities or exchanges. They are brand-new so won't have any slots connected to them right
        # now anyway. Any old activities or exchanges will have been deleted by this method.


class ABCalculationSetup(dict):

    def __init__(self, name: str, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    @property
    def changed(self) -> SignalInstance:
        return ctrl.cs_controller.get_virtual(self, create=True).changed

    @property
    def deleted(self) -> SignalInstance:
        return ctrl.cs_controller.get_virtual(self, create=True).deleted


class ABMethod(Method):

    def __hash__(self):
        return hash(self.name)

    @property
    def changed(self) -> SignalInstance:
        return ctrl.ic_controller.get_virtual(self, create=True).changed

    @property
    def deleted(self) -> SignalInstance:
        return ctrl.ic_controller.get_virtual(self, create=True).deleted

    def write(self, data, process=True):
        super().write(data, process)

        ctrl.ic_controller.changed(self)
        ctrl.ic_controller.sync()

    def copy(self, name=None) -> "ABMethod":
        new_method = super().copy(name)

        ctrl.ic_controller.sync()

        return new_method

    def deregister(self):
        super().deregister()

        ctrl.ic_controller.changed(self)
        ctrl.ic_controller.deleted(self)
        ctrl.ic_controller.sync()

    # extending Brightway Functionality

    def load_dict(self) -> dict:
        return {cf[0]: cf[1] for cf in self.load()}

    def write_dict(self, data: dict, process=True):
        self.write(list(data.items()), process)
