# -*- coding: utf-8 -*-
from typing import Iterator, Optional, Union
import uuid

import brightway2 as bw
from bw2data.backends.peewee.proxies import Activity, ExchangeProxyBase
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from ..bwutils import AB_metadata, commontasks as bc
from ..settings import project_settings
from ..signals import signals
from .parameter import ParameterController


class ActivityController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.new_activity.connect(self.new_activity)
        signals.delete_activity.connect(self.delete_activity)
        signals.duplicate_activity.connect(self.duplicate_activity)
        signals.show_duplicate_to_db_interface.connect(self.show_duplicate_to_db_interface)
        signals.activity_modified.connect(self.modify_activity)
        signals.duplicate_activity_to_db.connect(self.duplicate_activity_to_db)

    @Slot(str, name="createNewActivity")
    def new_activity(self, database_name: str) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Create new technosphere activity",
            "Please specify an activity name:" + " " * 10,
        )
        if ok and name:
            data = {
                "name": name, "reference product": name, "unit": "unit",
                "type": "process"
            }
            new_act = bw.Database(database_name).new_activity(
                code=uuid.uuid4().hex,
                **data
            )
            new_act.save()
            production_exchange = new_act.new_exchange(
                input=new_act, amount=1, type="production"
            )
            production_exchange.save()
            bw.databases.set_modified(database_name)
            signals.open_activity_tab.emit(new_act.key)
            signals.metadata_changed.emit(new_act.key)
            signals.database_changed.emit(database_name)
            signals.databases_changed.emit()

    @Slot(tuple, name="deleteActivity")
    def delete_activity(self, key: tuple) -> None:
        act = bw.get_activity(key)
        nu = len(act.upstream())
        if nu:
            text = "activities consume" if nu > 1 else "activity consumes"
            QtWidgets.QMessageBox.information(
                self.window,
                "Not possible.",
                """Can't delete {}. {} upstream {} its reference product.
                Upstream exchanges must be modified or deleted.""".format(act, nu, text)
            )
        else:
            ParameterController.delete_activity_parameter(act.key)
            act.delete()
            bw.databases.set_modified(act["database"])
            signals.metadata_changed.emit(act.key)
            signals.database_changed.emit(act["database"])
            signals.databases_changed.emit()
            signals.calculation_setup_changed.emit()

    @staticmethod
    def generate_copy_code(key: tuple) -> str:
        db, code = key
        metadata = AB_metadata.get_database_metadata(db)
        if '_copy' in code:
            code = code.split('_copy')[0]
        copies = metadata["key"].apply(
            lambda x: x[1] if code in x[1] and "_copy" in x[1] else None
        ).dropna().to_list() if not metadata.empty else []
        if not copies:
            return "{}_copy1".format(code)
        n = max((int(c.split('_copy')[1]) for c in copies))
        return "{}_copy{}".format(code, n + 1)

    @Slot(tuple, name="copyActivity")
    def duplicate_activity(self, key: tuple) -> None:
        """Duplicates the selected activity in the same db, with a new BW code."""
        # todo: add "copy of" (or similar) to name of activity for easy identification in new db
        # todo: some interface feedback so user knows the copy has succeeded
        act = bw.get_activity(key)
        new_code = self.generate_copy_code(key)
        new_act = act.copy(new_code)
        # Update production exchanges
        for exc in new_act.production():
            if exc.input.key == key:
                exc.input = new_act
                exc.save()
        # Update 'products'
        for product in new_act.get('products', []):
            if product.get('input') == key:
                product['input'] = new_act.key
        new_act.save()
        bw.databases.set_modified(act['database'])
        signals.metadata_changed.emit(new_act.key)
        signals.database_changed.emit(act['database'])
        signals.databases_changed.emit()
        signals.open_activity_tab.emit(new_act.key)

    @Slot(tuple, name="copyActivityToDbInterface")
    def show_duplicate_to_db_interface(self, key: tuple) -> None:
        origin_db = key[0]
        activity = bw.get_activity(key)

        available_target_dbs = list(project_settings.get_editable_databases())

        if origin_db in available_target_dbs:
            available_target_dbs.remove(origin_db)

        if not available_target_dbs:
            QtWidgets.QMessageBox.information(
                self.window,
                "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only)."
            )
        else:
            target_db, ok = QtWidgets.QInputDialog.getItem(
                self.window,
                "Copy activity to database",
                "Target database:",
                available_target_dbs,
                0,
                False
            )
            if ok:
                self.duplicate_activity_to_db(target_db, activity)

    @Slot(str, object, name="copyActivityToDb")
    def duplicate_activity_to_db(self, target_db: str, activity: Activity):
        new_code = self.generate_copy_code((target_db, activity['code']))
        new_act_key = (target_db, new_code)
        activity.copy(code=new_code, database=target_db)
        # only process database immediately if small
        if bc.count_database_records(target_db) < 50:
            bw.databases.clean()

        bw.databases.set_modified(target_db)
        signals.metadata_changed.emit(new_act_key)
        signals.database_changed.emit(target_db)
        signals.open_activity_tab.emit(new_act_key)
        signals.databases_changed.emit()

    @staticmethod
    @Slot(tuple, str, object, name="modifyActivity")
    def modify_activity(key: tuple, field: str, value: object) -> None:
        activity = bw.get_activity(key)
        activity[field] = value
        activity.save()
        bw.databases.set_modified(key[0])
        signals.metadata_changed.emit(key)
        signals.database_changed.emit(key[0])

    @staticmethod
    def _retrieve_activities(data: Union[tuple, Iterator[tuple]]) -> Iterator[Activity]:
        """Given either a key-tuple or a list of key-tuples, return a list
        of activities.
        """
        return [bw.get_activity(data)] if isinstance(data, tuple) else [
            bw.get_activity(k) for k in data
        ]


class ExchangeController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.exchanges_deleted.connect(self.delete_exchanges)
        signals.exchanges_add.connect(self.add_exchanges)
        signals.exchange_amount_modified.connect(self.modify_exchange_amount)
        signals.exchange_modified.connect(self.modify_exchange)
        signals.exchange_uncertainty_modified.connect(self.modify_exchange_uncertainty)
        signals.exchange_pedigree_modified.connect(self.modify_exchange_pedigree)

    @Slot(list, tuple, name="addExchangesToKey")
    def add_exchanges(self, from_keys: Iterator[tuple], to_key: tuple) -> None:
        activity = bw.get_activity(to_key)
        for key in from_keys:
            technosphere_db = bc.is_technosphere_db(key[0])
            exc = activity.new_exchange(input=key, amount=1)
            if key == to_key:
                exc['type'] = 'production'
            elif technosphere_db is True:
                exc['type'] = 'technosphere'
            elif technosphere_db is False:
                exc['type'] = 'biosphere'
            else:
                exc['type'] = 'unknown'
            exc.save()
        bw.databases.set_modified(to_key[0])
        signals.metadata_changed.emit(to_key)
        signals.database_changed.emit(to_key[0])

    @Slot(list, name="deleteExchanges")
    def delete_exchanges(self, exchanges: Iterator[ExchangeProxyBase]) -> None:
        db_changed = set()
        for exc in exchanges:
            db_changed.add(exc["output"][0])
            exc.delete()
        for db in db_changed:
            bw.databases.set_modified(db)
            # signals.metadata_changed.emit(to_key)
            signals.database_changed.emit(db)

    @Slot(object, )
    def modify_exchange_amount(self, exchange, value):
        exchange["amount"] = value
        exchange.save()
        bw.databases.set_modified(exchange["output"][0])
        signals.database_changed.emit(exchange["output"][0])

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
