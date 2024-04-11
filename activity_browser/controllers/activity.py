# -*- coding: utf-8 -*-
from typing import Iterator, Optional, Union, List
import uuid

import brightway2 as bw
import pandas as pd
from bw2data.backends.peewee.proxies import Activity
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from activity_browser import project_settings, signals, application
from activity_browser.bwutils import AB_metadata, commontasks as bc
from .parameter import ParameterController


class ActivityController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.new_activity.connect(self.new_activity)
        signals.delete_activity.connect(self.delete_activities)
        signals.delete_activities.connect(self.delete_activities)
        signals.duplicate_activity.connect(self.duplicate_activities)
        signals.duplicate_activities.connect(self.duplicate_activities)
        signals.duplicate_to_db_interface.connect(self.show_duplicate_to_db_interface)
        signals.duplicate_to_db_interface_multiple.connect(self.show_duplicate_to_db_interface)
        signals.activity_modified.connect(self.modify_activity)
        signals.duplicate_activity_to_db.connect(self.duplicate_activity_to_db)

    def new_activity(self, database_name: str, activity_name: str) -> None:
        data = {
            "name": activity_name,
            "reference product": activity_name,
            "unit": "unit",
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

    def delete_activities(self, data: Union[tuple, Iterator[tuple]]) -> None:
        """Use the given data to delete one or more activities from brightway2."""
        activities = self.get_activities(data)

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

    def duplicate_activities(self, keys: List[tuple]) -> None:
        """Duplicates the selected activity in the same db, with a new BW code."""
        # todo: add "copy of" (or similar) to name of activity for easy identification in new db
        # todo: some interface feedback so user knows the copy has succeeded
        activities = self.get_activities(keys)

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
        activities = self.get_activities(data)
        origin_db = db_name or next(iter(activities)).get("database")

        available_target_dbs = list(project_settings.get_editable_databases())
        if origin_db in available_target_dbs:
            available_target_dbs.remove(origin_db)
        if not available_target_dbs:
            QtWidgets.QMessageBox.warning(
                application.main_window, "No target database",
                "No valid target databases available. Create a new database or set one to writable (not read-only)."
            )
            return

        target_db, ok = QtWidgets.QInputDialog.getItem(
            application.main_window, "Copy activity to database", "Target database:",
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
    def get_activities(keys: Union[tuple, List[tuple]]) -> List[Activity]:
        """Given either a key-tuple or a list of key-tuples, return a list
        of activities.
        """
        if isinstance(keys, tuple):
            return [bw.get_activity(keys)]
        else:
            return [bw.get_activity(k) for k in keys]


activity_controller = ActivityController(application)
