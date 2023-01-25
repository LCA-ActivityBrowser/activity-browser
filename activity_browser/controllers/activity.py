# -*- coding: utf-8 -*-
from typing import Iterator, Optional, Union
import uuid

import brightway2 as bw
from bw2data.backends.peewee.proxies import Activity, ExchangeProxyBase
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from activity_browser.bwutils import AB_metadata, commontasks as bc
from activity_browser.bwutils.strategies import relink_activity_exchanges
from activity_browser.settings import project_settings
from activity_browser.signals import signals
from activity_browser.ui.wizards import UncertaintyWizard
from ..ui.widgets import ActivityLinkingDialog, ActivityLinkingResultsDialog
from .parameter import ParameterController


class ActivityController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.new_activity.connect(self.new_activity)
        signals.delete_activity.connect(self.delete_activity)
        signals.delete_activities.connect(self.delete_activity)
        signals.duplicate_activity.connect(self.duplicate_activity)
        signals.duplicate_activities.connect(self.duplicate_activity)
        signals.duplicate_to_db_interface.connect(self.show_duplicate_to_db_interface)
        signals.duplicate_to_db_interface_multiple.connect(self.show_duplicate_to_db_interface)
        signals.activity_modified.connect(self.modify_activity)
        signals.duplicate_activity_to_db.connect(self.duplicate_activity_to_db)
        signals.relink_activity.connect(self.relink_activity_exchange)

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
            AB_metadata.update_metadata(new_act.key)
            signals.database_changed.emit(database_name)
            signals.databases_changed.emit()
            signals.unsafe_open_activity_tab.emit(new_act.key)

    @Slot(tuple, name="deleteActivity")
    @Slot(list, name="deleteActivities")
    def delete_activity(self, data: Union[tuple, Iterator[tuple]]) -> None:
        """Use the given data to delete one or more activities from brightway2."""
        activities = self._retrieve_activities(data)

        text = ("One or more activities have downstream processes. "
                "Deleting these activities will remove the exchange from the downstream processes, this can't be undone.\n\n"
                "Are you sure you want to continue?")

        if any(len(act.upstream()) > 0 for act in activities):
            choice = QtWidgets.QMessageBox.warning(self.window,
                                                   "Activity/Activities has/have downstream processes",
                                                   text,
                                                   QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                                   QtWidgets.QMessageBox.No)
            if choice == QtWidgets.QMessageBox.No:
                return

        # Iterate through the activities and:
        # - Close any open activity tabs,
        # - Delete any related parameters
        # - Delete the activity
        # - Clean the activity from the metadata.
        for act in activities:
            signals.close_activity_tab.emit(act.key)
            ParameterController.delete_activity_parameter(act.key)
            act.delete()
            AB_metadata.update_metadata(act.key)

        # After deletion, signal that the database has changed
        db = next(iter(activities)).get("database")
        bw.databases.set_modified(db)
        signals.database_changed.emit(db)
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
    @Slot(list, name="copyActivities")
    def duplicate_activity(self, data: Union[tuple, Iterator[tuple]]) -> None:
        """Duplicates the selected activity in the same db, with a new BW code."""
        # todo: add "copy of" (or similar) to name of activity for easy identification in new db
        # todo: some interface feedback so user knows the copy has succeeded
        activities = self._retrieve_activities(data)

        for act in activities:
            new_code = self.generate_copy_code(act.key)
            new_act = act.copy(new_code)
            # Update production exchanges
            for exc in new_act.production():
                if exc.input.key == act.key:
                    exc.input = new_act
                    exc.save()
            # Update 'products'
            for product in new_act.get('products', []):
                if product.get('input') == act.key:
                    product['input'] = new_act.key
            new_act.save()
            AB_metadata.update_metadata(new_act.key)
            signals.safe_open_activity_tab.emit(new_act.key)

        db = next(iter(activities)).get("database")
        bw.databases.set_modified(db)
        signals.database_changed.emit(db)
        signals.databases_changed.emit()

    @Slot(tuple, str, name="copyActivityToDbInterface")
    @Slot(list, str, name="copyActivitiesToDbInterface")
    def show_duplicate_to_db_interface(self, data: Union[tuple, Iterator[tuple]],
                                       db_name: Optional[str] = None) -> None:
        activities = self._retrieve_activities(data)
        origin_db = db_name or next(iter(activities)).get("database")

        available_target_dbs = list(project_settings.get_editable_databases())
        if origin_db in available_target_dbs:
            available_target_dbs.remove(origin_db)
        if not available_target_dbs:
            QtWidgets.QMessageBox.warning(
                self.window, "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only)."
            )
            return

        target_db, ok = QtWidgets.QInputDialog.getItem(
            self.window, "Copy activity to database", "Target database:",
            available_target_dbs, 0, False
        )
        if target_db and ok:
            new_keys = [self._copy_activity(target_db, act) for act in activities]
            if bc.count_database_records(target_db) < 50:
                bw.databases.clean()
            bw.databases.set_modified(target_db)
            signals.database_changed.emit(target_db)
            signals.databases_changed.emit()
            for key in new_keys:
                signals.safe_open_activity_tab.emit(key)

    @Slot(str, object, name="copyActivityToDb")
    def duplicate_activity_to_db(self, target_db: str, activity: Activity):
        new_key = self._copy_activity(target_db, activity)
        # only process database immediately if small
        if bc.count_database_records(target_db) < 50:
            bw.databases.clean()
        bw.databases.set_modified(target_db)
        signals.database_changed.emit(target_db)
        signals.databases_changed.emit()
        signals.safe_open_activity_tab.emit(new_key)

    @staticmethod
    def _copy_activity(target: str, act: Activity) -> tuple:
        new_code = ActivityController.generate_copy_code((target, act['code']))
        new_key = (target, new_code)
        act.copy(code=new_code, database=target)
        AB_metadata.update_metadata(new_key)
        return new_key

    @staticmethod
    @Slot(tuple, str, object, name="modifyActivity")
    def modify_activity(key: tuple, field: str, value: object) -> None:
        activity = bw.get_activity(key)
        activity[field] = value
        activity.save()
        bw.databases.set_modified(key[0])
        AB_metadata.update_metadata(key)
        signals.database_changed.emit(key[0])

    @staticmethod
    def _retrieve_activities(data: Union[tuple, Iterator[tuple]]) -> Iterator[Activity]:
        """Given either a key-tuple or a list of key-tuples, return a list
        of activities.
        """
        return [bw.get_activity(data)] if isinstance(data, tuple) else [
            bw.get_activity(k) for k in data
        ]

    @Slot(tuple, name="relinkActivityExchanges")
    def relink_activity_exchange(self, key: tuple) -> None:
        db = bw.Database(key[0])
        actvty = db.get(key[1])
        depends = db.find_dependents()
        options = [(depend, bw.databases.list) for depend in depends]
        dialog = ActivityLinkingDialog.relink_sqlite(actvty['name'], options, self.window)
        relinking_results = {}
        if dialog.exec_() == ActivityLinkingDialog.Accepted:
            for old, new in dialog.relink.items():
                other = bw.Database(new)
                failed, succeeded, examples = relink_activity_exchanges(actvty, old, other)
                relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)
            if failed > 0:
                relinking_dialog = ActivityLinkingResultsDialog.present_relinking_results(self.window, relinking_results, examples)
                relinking_dialog.exec_()
                activity = relinking_dialog.open_activity()
            signals.database_changed.emit(actvty['name'])
            signals.databases_changed.emit()


class ExchangeController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.exchanges_deleted.connect(self.delete_exchanges)
        signals.exchanges_add.connect(self.add_exchanges)
        signals.exchange_modified.connect(self.modify_exchange)
        signals.exchange_uncertainty_wizard.connect(self.edit_exchange_uncertainty)
        signals.exchange_uncertainty_modified.connect(self.modify_exchange_uncertainty)
        signals.exchange_pedigree_modified.connect(self.modify_exchange_pedigree)

    @Slot(list, tuple, name="addExchangesToKey")
    def add_exchanges(self, from_keys: Iterator[tuple], to_key: tuple) -> None:
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
        wizard = UncertaintyWizard(exc, self.window)
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
