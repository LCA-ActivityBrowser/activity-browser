# -*- coding: utf-8 -*-
import brightway2 as bw

from ..signals import signals


class ConvenienceData(object):
    """Stores data that may be re-used within one session, e.g.:
    - locations and units of a database."""
    def __init__(self):
        self.data = dict()

        self.connect_signals()

    def connect_signals(self):
        signals.edit_activity.connect(self.get_convenience_data)

    def get_convenience_data(self, db_name, update=False):
        """Get data from activities across one database and store it in sets."""
        if not db_name in self.data or update:
            locations = set()
            units = set()
            for act in bw.Database(db_name):
                locations.add(act.get("location"))
                units.add(act.get("unit"))

            self.data[db_name] = {
                "locations": locations,
                "units": units,
            }
        print("{} unique locations and {} unique units in {}".format(
            len(self.data[db_name]["locations"]),
            len(self.data[db_name]["units"]),
            db_name))


convenience_data = ConvenienceData()
