import pandas as pd
from qtpy import QtWidgets

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils import AB_metadata, commontasks
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class ActivityDuplicateToLoc(ABAction):
    """
    ABAction to duplicate an activity and possibly their exchanges to a new location.
    """

    icon = qicons.copy
    text = "Duplicate node to new location"

    @classmethod
    @exception_dialogs
    def run(cls, activity_key: tuple):
        activity = bd.get_activity(activity_key)
        db_name = activity["database"]

        # get list of dependent databases for activity and load to MetaDataStore
        databases = []
        for exchange in activity.technosphere():
            databases.append(exchange.input[0])
        if db_name not in databases:  # add own database if it wasn't added already
            databases.append(db_name)

        # load all dependent databases to MetaDataStore
        dbs = {db: AB_metadata.get_database_metadata(db) for db in databases}
        # get list of all unique locations in the dependent databases (sorted alphabetically)
        locations = []
        for db in dbs.values():
            locations += db["location"].to_list()  # add all locations to one list
        locations = list(set(locations))  # reduce the list to only unique items
        locations.sort()

        # get the location to relink
        db = dbs[db_name]
        old_location = db.loc[db["key"] == activity.key]["location"].iloc[0]

        # trigger dialog with autocomplete-writeable-dropdown-list
        options = (old_location, locations)
        dialog = LocationLinkingDialog.relink_location(
            activity["name"], options, application.main_window
        )

        if dialog.exec_() != LocationLinkingDialog.Accepted:
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

        # successful_links = {}  # dict of dicts, key of new exch : {new values} <-- see 'values' below
        # in the future, 'alternatives' could be improved by making use of some location hierarchy. From that we could
        # get things like if the new location is NL but there is no NL, but RER exists, we use that. However, for that
        # we need some hierarchical structure to the location data, which may be available from ecoinvent, but we need
        # to look for that.

        # get exchanges that we want to relink
        # for exch in activity.technosphere():
        #     candidate = self.find_candidate(dbs, exch, old_location, new_location, use_alternatives, alternatives)
        #     if candidate is None:
        #         continue  # no suitable candidate was found, try the next exchange
        #
        #     # at this point, we have found 1 suitable candidate, whether that is new_location or alternative location
        #     values = {
        #         'amount': exch.get('amount', False),
        #         'comment': exch.get('comment', False),
        #         'formula': exch.get('formula', False),
        #         'uncertainty': exch.get('uncertainty', False)
        #     }
        #     successful_links[candidate['key'].iloc[0]] = values

        # now, create a new activity by copying the old one
        new_code = commontasks.generate_copy_code(activity.key)
        new_act = activity.copy(new_code)

        # update production exchanges
        # TODO: check if this is even necessary (I think BW takes care of this)
        for exc in new_act.production():
            if exc.input.key == activity.key:
                exc.input = new_act
                exc.save()

        # update 'products'
        for product in new_act.get("products", []):
            if product.get("input") == activity.key:
                product.input = new_act.key

        # save the new location to the activity
        new_act["location"] = new_location

        new_act.save()

        # get exchanges that we want to delete
        # del_exch = []  # delete these exchanges
        for exch in new_act.technosphere():
            candidate = cls.find_candidate(
                db_name,
                dbs,
                exch,
                old_location,
                new_location,
                use_alternatives,
                alternatives,
            )
            if candidate is None:
                continue  # no suitable candidate was found, try the next exchange
            exch.input = candidate["key"][0]
            exch.save()
            # del_exch.append(exch)
        # delete exchanges with old locations
        # exchange_controller.delete_exchanges(del_exch)

        # add the new exchanges with all values carried over from last exchange
        # exchange_controller.add_exchanges(list(successful_links.keys()), new_act.key, successful_links)

        # update the MetaDataStore and open new activity
        AB_metadata.update_metadata(new_act.key)
        signals.safe_open_activity_tab.emit(new_act.key)

    @staticmethod
    def find_candidate(
        db_name, dbs, exch, old_location, new_location, use_alternatives, alternatives
    ):
        """Find a candidate to replace the exchange with."""
        current_db = exch.input[0]
        if current_db == db_name:
            db = dbs[current_db]
        else:  # if the exchange is not from the current database, also check the current
            # (user may have added their own alternative dependents already)
            db = pd.concat([dbs[current_db], dbs[db_name]])

        if db.loc[db["key"] == exch.input]["location"].iloc[0] != old_location:
            return  # this exchange has a location we're not trying to re-link

        # get relevant data to match on
        row = db.loc[db["key"] == exch.input]
        name = row["name"].iloc[0]
        prod = row["reference product"].iloc[0]
        unit = row["unit"].iloc[0]

        # get candidates to match (must have same name, product and unit)
        candidates = db.loc[
            (db["name"] == name)
            & (db["reference product"] == prod)
            & (db["unit"] == unit)
        ]
        if len(candidates) <= 1:
            return  # this activity does not exist in this database with another location (1 is self)

        # check candidates for new_location
        candidate = candidates.loc[candidates["location"] == new_location]
        if len(candidate) == 0 and not use_alternatives:
            return  # there is no candidate
        elif len(candidate) > 1:
            return  # there is more than one candidate, we can't know what to use
        elif len(candidate) == 0:
            # there are no candidates, but we can try alternatives
            for alt in alternatives:
                candidate = candidates.loc[candidates["location"] == alt]
                if len(candidate) == 1:
                    break  # found an alternative in with this alternative location, stop looking
            if len(candidate) != 1:
                return  # there are either no or multiple matches with alternative locations
        return candidate


class LocationLinkingDialog(QtWidgets.QDialog):
    """Display all of the possible location links in a single dialog for the user.

    Allow users to select alternate location links and an option to link to generic alternatives (GLO, RoW).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activity Location linking")

        self.loc_label = QtWidgets.QLabel()
        self.label_choices = []
        self.grid_box = QtWidgets.QGroupBox("Location link:")
        self.grid = QtWidgets.QGridLayout()
        self.grid_box.setLayout(self.grid)

        self.use_alternatives_label = QtWidgets.QLabel(
            "Use generic alternatives as fallback:"
        )
        self.use_alternatives_label.setToolTip(
            "If the chosen location is not found, try matching the selected "
            "locations below too"
        )
        self.use_row = QtWidgets.QCheckBox("RoW")
        self.use_row.setChecked(True)
        self.use_rer = QtWidgets.QCheckBox("RER")
        self.use_ews = QtWidgets.QCheckBox("Europe without Switzerland")

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.loc_label)
        layout.addWidget(self.grid_box)
        layout.addWidget(self.use_alternatives_label)
        layout.addWidget(self.use_row)
        layout.addWidget(self.use_rer)
        layout.addWidget(self.use_ews)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    @property
    def relink(self) -> dict:
        """Returns a dictionary of str -> str key/values, showing which keys
        should be linked to which values.

        Only returns key/value pairs if they differ.
        """
        return {
            label.text(): combo.currentText()
            for label, combo in self.label_choices
            if label.text() != combo.currentText()
        }

    @classmethod
    def construct_dialog(
        cls,
        label: str,
        options: list,
        parent: QtWidgets.QWidget = None,
    ) -> "LocationLinkingDialog":
        loc, locs = options

        obj = cls(parent)
        obj.loc_label.setText(label)

        label = QtWidgets.QLabel(loc)
        combo = QtWidgets.QComboBox()
        combo.addItems(locs)
        combo.setCurrentText(loc)
        obj.label_choices.append((label, combo))
        # Start at 1 because row 0 is taken up by the loc_label
        obj.grid.addWidget(label, 0, 0, 1, 2)
        obj.grid.addWidget(combo, 0, 2, 1, 2)

        obj.updateGeometry()
        return obj

    @classmethod
    def relink_location(
        cls, act_name: str, options: list, parent=None
    ) -> "LocationLinkingDialog":
        label = "Relinking exchanges from activity '{}' to a new location.".format(
            act_name
        )
        return cls.construct_dialog(label, options, parent)


