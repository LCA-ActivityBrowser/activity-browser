from typing import Union, Callable, Optional

import pandas as pd
import brightway2 as bw
from PySide2 import QtCore

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata
from activity_browser.ui.icons import qicons
from activity_browser.actions.base import ABAction
from ...ui.widgets import LocationLinkingDialog
from ...controllers.activity import activity_controller


class ActivityDuplicateToLoc(ABAction):
    icon = qicons.copy
    title = 'Duplicate activity to new location'
    activity_key: tuple
    db_name: str

    def __init__(self, activity_key: Union[tuple, Callable], parent: QtCore.QObject):
        super().__init__(parent, activity_key=activity_key)

    def onTrigger(self, toggled):
        act = activity_controller.get_activities(self.activity_key)[0]
        self.db_name = act.key[0]

        # get list of dependent databases for activity and load to MetaDataStore
        databases = []
        for exchange in act.technosphere():
            databases.append(exchange.input[0])
        if self.db_name not in databases:  # add own database if it wasn't added already
            databases.append(self.db_name)

        # load all dependent databases to MetaDataStore
        dbs = {db: AB_metadata.get_database_metadata(db) for db in databases}
        # get list of all unique locations in the dependent databases (sorted alphabetically)
        locations = []
        for db in dbs.values():
            locations += db['location'].to_list()  # add all locations to one list
        locations = list(set(locations))  # reduce the list to only unique items
        locations.sort()

        # get the location to relink
        db = dbs[self.db_name]
        old_location = db.loc[db['key'] == act.key]['location'].iloc[0]

        # trigger dialog with autocomplete-writeable-dropdown-list
        options = (old_location, locations)
        dialog = LocationLinkingDialog.relink_location(act['name'], options, application.main_window)

        if dialog.exec_() != LocationLinkingDialog.Accepted: return

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

        successful_links = {}  # dict of dicts, key of new exch : {new values} <-- see 'values' below
        # in the future, 'alternatives' could be improved by making use of some location hierarchy. From that we could
        # get things like if the new location is NL but there is no NL, but RER exists, we use that. However, for that
        # we need some hierarchical structure to the location data, which may be available from ecoinvent, but we need
        # to look for that.

        # get exchanges that we want to relink
        for exch in act.technosphere():
            candidate = self.find_candidate(dbs, exch, old_location, new_location, use_alternatives, alternatives)
            if candidate is None:
                continue  # no suitable candidate was found, try the next exchange

            # at this point, we have found 1 suitable candidate, whether that is new_location or alternative location
            values = {
                'amount': exch.get('amount', False),
                'comment': exch.get('comment', False),
                'formula': exch.get('formula', False),
                'uncertainty': exch.get('uncertainty', False)
            }
            successful_links[candidate['key'].iloc[0]] = values

        # now, create a new activity by copying the old one
        new_code = activity_controller.generate_copy_code(act.key)
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
        activity_controller.modify_activity(new_act.key, 'location', new_location)

        # get exchanges that we want to delete
        del_exch = []  # delete these exchanges
        for exch in new_act.technosphere():
            candidate = self.find_candidate(dbs, exch, old_location, new_location, use_alternatives, alternatives)
            if candidate is None:
                continue  # no suitable candidate was found, try the next exchange
            del_exch.append(exch)
        # delete exchanges with old locations
        signals.exchanges_deleted.emit(del_exch)

        # add the new exchanges with all values carried over from last exch
        signals.exchanges_add_w_values.emit(list(successful_links.keys()), new_act.key, successful_links)

        # update the MetaDataStore and open new activity
        AB_metadata.update_metadata(new_act.key)
        signals.safe_open_activity_tab.emit(new_act.key)

        # send signals to relevant locations
        bw.databases.set_modified(self.db_name)
        signals.database_changed.emit(self.db_name)
        signals.databases_changed.emit()

    def find_candidate(self, dbs, exch, old_location, new_location, use_alternatives, alternatives) -> Optional[object]:
        """Find a candidate to replace the exchange with."""
        current_db = exch.input[0]
        if current_db == self.db_name:
            db = dbs[current_db]
        else:  # if the exchange is not from the current database, also check the current
            # (user may have added their own alternative dependents already)
            db = pd.concat([dbs[current_db], dbs[self.db_name]])

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
