from typing import Iterator

import brightway2 as bw
from bw2data.backends.peewee.proxies import ExchangeProxyBase
from PySide2.QtCore import QObject, Slot

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata, commontasks as bc


class ExchangeController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def add_exchanges(self, from_keys: Iterator[tuple], to_key: tuple, new_values: dict = None) -> None:
        """
        Add new exchanges.

        Optionally add new values also.

        Parameters
        ----------
        from_keys: The activities (keys) to create exchanges from
        to_key: The activity (key) to create an exchange to
        new_values: Values of the exchange, dict (from_keys as keys) with field names and values for the exchange

        Returns
        -------

        """
        activity = bw.get_activity(to_key)
        for key in from_keys:
            technosphere_db = bc.is_technosphere_db(key[0])
            exc = activity.new_exchange(input=key, amount=1)
            if technosphere_db is True:
                exc['type'] = 'technosphere'
            elif technosphere_db is False:
                exc['type'] = 'biosphere'
            else:
                exc['type'] = 'unknown'
            # add optional exchange values
            if new_values and (new_vals := new_values.get(key, {})):
                for field_name, value in new_vals.items():
                    if value:
                        exc[field_name] = value
            exc.save()
        bw.databases.set_modified(to_key[0])
        AB_metadata.update_metadata(to_key)
        signals.database_changed.emit(to_key[0])

    def delete_exchanges(self, exchanges: Iterator[ExchangeProxyBase]) -> None:
        db_changed = set()
        for exc in exchanges:
            db_changed.add(exc["output"][0])
            exc.delete()
        for db in db_changed:
            bw.databases.set_modified(db)
            signals.database_changed.emit(db)

    def edit_exchange(self, exchange: ExchangeProxyBase, data: dict):
        recalculate_exchanges = False

        for field, value in data.items():
            if field == "formula":
                edit_exchange_formula(exchange, value)
                recalculate_exchanges = True

            if field in {"loc", "scale", "shape", "minimum", "maximum"}:
                edit_exchange_uncertainty(exchange, field, value)

        exchange.save()
        bw.databases.set_modified(exchange["output"][0])
        signals.database_changed.emit(exchange["output"][0])

        if recalculate_exchanges:
            signals.exchange_formula_changed.emit(exchange["output"])

    @staticmethod
    @Slot(object, object, name="modifyExchangePedigree")
    def modify_exchange_pedigree(exc: ExchangeProxyBase, pedigree: dict) -> None:
        exc["pedigree"] = pedigree
        exc.save()
        bw.databases.set_modified(exc["output"][0])
        signals.database_changed.emit(exc["output"][0])


def edit_exchange_formula(exchange: ExchangeProxyBase, value):
    if "formula" in exchange and (value == "" or value is None):
        # Remove formula entirely.
        del exchange["formula"]
        if "original_amount" in exchange:
            # Restore the original amount, if possible
            exchange["amount"] = exchange["original_amount"]
            del exchange["original_amount"]
    if value:
        # At least set the formula, possibly also store the amount
        if "formula" not in exchange:
            exchange["original_amount"] = exchange["amount"]
        exchange["formula"] = value


def edit_exchange_uncertainty(exchange: ExchangeProxyBase, field: str, value):
    if isinstance(value, str):
        value = float("nan") if not value else float(value)

    exchange[field] = value


exchange_controller = ExchangeController(application)
