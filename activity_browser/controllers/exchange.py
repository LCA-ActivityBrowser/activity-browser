from typing import Iterator

import brightway2 as bw
from bw2data.backends.peewee.proxies import ExchangeProxyBase
from PySide2.QtCore import QObject, Slot

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata, commontasks as bc
from activity_browser.ui.wizards import UncertaintyWizard


class ExchangeController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.exchanges_deleted.connect(self.delete_exchanges)
        signals.exchanges_add.connect(self.add_exchanges)
        signals.exchanges_add_w_values.connect(self.add_exchanges)
        signals.exchange_modified.connect(self.modify_exchange)
        signals.exchange_uncertainty_wizard.connect(self.edit_exchange_uncertainty)
        signals.exchange_uncertainty_modified.connect(self.modify_exchange_uncertainty)
        signals.exchange_pedigree_modified.connect(self.modify_exchange_pedigree)

    @Slot(list, tuple, name="addExchangesToKey")
    def add_exchanges(self, from_keys: Iterator[tuple], to_key: tuple, new_values: dict = {}) -> None:
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
            if new_vals := new_values.get(key, {}):
                for field_name, value in new_vals.items():
                    if value:
                        exc[field_name] = value
            exc.save()
        bw.databases.set_modified(to_key[0])
        AB_metadata.update_metadata(to_key)
        signals.database_changed.emit(to_key[0])

    @Slot(list, name="deleteExchanges")
    def delete_exchanges(self, exchanges: Iterator[ExchangeProxyBase]) -> None:
        db_changed = set()
        for exc in exchanges:
            db_changed.add(exc["output"][0])
            exc.delete()
        for db in db_changed:
            bw.databases.set_modified(db)
            signals.database_changed.emit(db)

    @staticmethod
    @Slot(object, str, object, name="editExchange")
    def modify_exchange(exchange: ExchangeProxyBase, field: str, value) -> None:
        # The formula field needs special handling.
        if field == "formula":
            if field in exchange and (value == "" or value is None):
                # Remove formula entirely.
                del exchange[field]
                if "original_amount" in exchange:
                    # Restore the original amount, if possible
                    exchange["amount"] = exchange["original_amount"]
                    del exchange["original_amount"]
            if value:
                # At least set the formula, possibly also store the amount
                if field not in exchange:
                    exchange["original_amount"] = exchange["amount"]
                exchange[field] = value
        else:
            exchange[field] = value
        exchange.save()
        bw.databases.set_modified(exchange["output"][0])
        if field == "formula":
            # If a formula was set, removed or changed, recalculate exchanges
            signals.exchange_formula_changed.emit(exchange["output"])
        signals.database_changed.emit(exchange["output"][0])

    @Slot(object, name="runUncertaintyWizard")
    def edit_exchange_uncertainty(self, exc: ExchangeProxyBase) -> None:
        """Explicitly call the wizard here for altering the uncertainty."""
        wizard = UncertaintyWizard(exc, application.main_window)
        wizard.show()

    @staticmethod
    @Slot(object, object, name="modifyExchangeUncertainty")
    def modify_exchange_uncertainty(exc: ExchangeProxyBase, unc_dict: dict) -> None:
        unc_fields = {"loc", "scale", "shape", "minimum", "maximum"}
        for k, v in unc_dict.items():
            if k in unc_fields and isinstance(v, str):
                # Convert empty values into nan, accepted by stats_arrays
                v = float("nan") if not v else float(v)
            exc[k] = v
        exc.save()
        bw.databases.set_modified(exc["output"][0])
        signals.database_changed.emit(exc["output"][0])

    @staticmethod
    @Slot(object, object, name="modifyExchangePedigree")
    def modify_exchange_pedigree(exc: ExchangeProxyBase, pedigree: dict) -> None:
        exc["pedigree"] = pedigree
        exc.save()
        bw.databases.set_modified(exc["output"][0])
        signals.database_changed.emit(exc["output"][0])


exchange_controller = ExchangeController(application)
