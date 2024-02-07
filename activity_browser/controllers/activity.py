# -*- coding: utf-8 -*-
from typing import Iterator, Optional, Union
import uuid

import brightway2 as bw
import pandas as pd
from bw2data.backends.peewee.proxies import Activity
from PySide2.QtCore import QObject, Slot, Qt
from PySide2 import QtWidgets

from activity_browser import project_settings, signals
from activity_browser.bwutils import AB_metadata, commontasks as bc
from activity_browser.bwutils.strategies import relink_activity_exchanges
from .parameter import ParameterController
from ..ui.widgets import ActivityLinkingDialog, ActivityLinkingResultsDialog, LocationLinkingDialog

class ActivityController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.new_activity.connect(self.new_activity)
        signals.delete_activity.connect(self.delete_activity)
        signals.delete_activities.connect(self.delete_activity)
        signals.duplicate_activity.connect(self.duplicate_activity)
        signals.duplicate_activity_new_loc.connect(self.duplicate_activity_new_loc)
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

    @Slot(tuple, name="copyActivityNewLoc")
    def duplicate_activity_new_loc(self, old_key: tuple) -> None:
        """Duplicates the selected activity in the same db, links to new location, with a new BW code.

        This function will try and link all exchanges in the same location as the production process
        to a chosen location, if none is available for the given exchange, it will try to link to
        RoW and then GLO, if those don't exist, the exchange is not altered.

        This def does the following:
        - Read all databases in exchanges of activity into MetaDataStore
        - Give user dialog to re-link location and potentially use alternatives
        - Finds suitable activities with new location (and potentially alternative)
        - Re-link exchanges to new (and potentially alternative) location

        Parameters
        ----------
        old_key: the key of the activity to re-link to a different location

        Returns
        -------
        """
        def find_candidate(dbs, exch, old_location, new_location, use_alternatives, alternatives) -> Optional[object]:
            """Find a candidate to replace the exchange with."""
            current_db = exch.input[0]
            if current_db == db_name:
                db = dbs[current_db]
            else:  # if the exchange is not from the current database, also check the current
                # (user may have added their own alternative dependents already)
                db = pd.concat([dbs[current_db], dbs[db_name]])

            if db.loc[db['key'] == exch.input]['location'].iloc[0] != old_location:
                return  # this exchange has a location we're not trying to re-link

            # get relevant data to match on
            row = db.loc[db['key'] == exch.input]
            name = row['name'].iloc[0]
            prod = row['reference product'].iloc[0]
            unit = row['unit'].iloc[0]

            # get candidates to match (must have same name, product and unit)
            candidates = db.loc[(db['name'] == name)
                                & (db['reference product'] == prod)
                                & (db['unit'] == unit)]
            if len(candidates) <= 1:
                return  # this activity does not exist in this database with another location (1 is self)

            # check candidates for new_location
            candidate = candidates.loc[candidates['location'] == new_location]
            if len(candidate) == 0 and not use_alternatives:
                return  # there is no candidate
            elif len(candidate) > 1:
                return  # there is more than one candidate, we can't know what to use
            elif len(candidate) == 0:
                # there are no candidates, but we can try alternatives
                for alt in alternatives:
                    candidate = candidates.loc[candidates['location'] == alt]
                    if len(candidate) == 1:
                        break  # found an alternative in with this alternative location, stop looking
                if len(candidate) != 1:
                    return  # there are either no or multiple matches with alternative locations
            return candidate

        act = self._retrieve_activities(old_key)[0]  # we only take one activity but this function always returns list
        db_name = act.key[0]

        # get list of dependent databases for activity and load to MetaDataStore
        databases = []
        for exch in act.technosphere():
            databases.append(exch.input[0])
        if db_name not in databases:  # add own database if it wasn't added already
            databases.append(db_name)

        # load all dependent databases to MetaDataStore
        dbs = {db: AB_metadata.get_database_metadata(db) for db in databases}
        # get list of all unique locations in the dependent databases (sorted alphabetically)
        locations = []
        for db in dbs.values():
            locations += db['location'].to_list()  # add all locations to one list
        locations = list(set(locations))  # reduce the list to only unique items
        locations.sort()

        # get the location to relink
        db = dbs[db_name]
        old_location = db.loc[db['key'] == act.key]['location'].iloc[0]

        # trigger dialog with autocomplete-writeable-dropdown-list
        options = (old_location, locations)
        dialog = LocationLinkingDialog.relink_location(act['name'], options, self.window)
        if dialog.exec_() != LocationLinkingDialog.Accepted:
            # if the dialog accept button is not clicked, do nothing
            return

        # read the data from the dialog
        for old, new in dialog.relink.items():
            alternatives = []
            new_location = new
            if dialog.use_rer.isChecked():  # RER
                alternatives.append(dialog.use_rer.text())
            if dialog.use_ews.isChecked():  # Europe without Switzerland
                alternatives.append(dialog.use_ews.text())
            if dialog.use_row.isChecked():  # RoW
                alternatives.append(dialog.use_row.text())
            # the order we add alternatives is important, they are checked in this order!
            if len(alternatives) > 0:
                use_alternatives = True
            else:
                use_alternatives = False

        succesful_links = {}  # dict of dicts, key of new exch : {new values} <-- see 'values' below
        # in the future, 'alternatives' could be improved by making use of some location hierarchy. From that we could
        # get things like if the new location is NL but there is no NL, but RER exists, we use that. However, for that
        # we need some hierarchical structure to the location data, which may be available from ecoinvent, but we need
        # to look for that.

        # get exchanges that we want to relink
        for exch in act.technosphere():
            candidate = find_candidate(dbs, exch, old_location, new_location, use_alternatives, alternatives)
            if candidate is None:
                continue  # no suitable candidate was found, try the next exchange

            # at this point, we have found 1 suitable candidate, whether that is new_location or alternative location
            values = {
                'amount': exch.get('amount', False),
                'comment': exch.get('comment', False),
                'formula': exch.get('formula', False),
                'uncertainty': exch.get('uncertainty', False)
            }
            succesful_links[candidate['key'].iloc[0]] = values

        # now, create a new activity by copying the old one
        new_code = self.generate_copy_code(act.key)
        new_act = act.copy(new_code)
        # update production exchanges
        for exc in new_act.production():
            if exc.input.key == act.key:
                exc.input = new_act
                exc.save()
        # update 'products'
        for product in new_act.get('products', []):
            if product.get('input') == act.key:
                product.input = new_act.key
        new_act.save()
        # save the new location to the activity
        self.modify_activity(new_act.key, 'location', new_location)

        # get exchanges that we want to delete
        del_exch = []  # delete these exchanges
        for exch in new_act.technosphere():
            candidate = find_candidate(dbs, exch, old_location, new_location, use_alternatives, alternatives)
            if candidate is None:
                continue  # no suitable candidate was found, try the next exchange
            del_exch.append(exch)
        # delete exchanges with old locations
        signals.exchanges_deleted.emit(del_exch)

        # add the new exchanges with all values carried over from last exch
        signals.exchanges_add_w_values.emit(list(succesful_links.keys()), new_act.key, succesful_links)

        # update the MetaDataStore and open new activity
        AB_metadata.update_metadata(new_act.key)
        signals.safe_open_activity_tab.emit(new_act.key)

        # send signals to relevant locations
        bw.databases.set_modified(db_name)
        signals.database_changed.emit(db_name)
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
            QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
            for old, new in dialog.relink.items():
                other = bw.Database(new)
                failed, succeeded, examples = relink_activity_exchanges(actvty, old, other)
                relinking_results[f"{old} --> {other.name}"] = (failed, succeeded)
            QtWidgets.QApplication.restoreOverrideCursor()
            if failed > 0:
                relinking_dialog = ActivityLinkingResultsDialog.present_relinking_results(self.window, relinking_results, examples)
                relinking_dialog.exec_()
                activity = relinking_dialog.open_activity()
            signals.database_changed.emit(actvty['name'])
            signals.databases_changed.emit()


