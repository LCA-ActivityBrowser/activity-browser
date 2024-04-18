from bw2data.meta import *

from activity_browser.signals import databases_updater, calculation_setups_updater
from ..patching import patch_superclass, patched


@patch_superclass
class Databases(Databases):
    """
    Apparently the databases metaclass is kinda broken. As in, it doesn't update when the underlying databases change in
    e.g. number of activities. Also, setting a database as modified is done before the database is actually modified,
    meaning that callbacks relying on the modified database will fail. This should be fixed within Brightway...
    """

    @property
    def metadata_changed(self):
        return databases_updater.metadata_changed

    def flush(self):
        patched().flush()
        databases_updater.emitLater("metadata_changed")


@patch_superclass
class CalculationSetups(CalculationSetups):
    """
    Apparently the databases metaclass is kinda broken. As in, it doesn't update when the underlying databases change in
    e.g. number of activities. Also, setting a database as modified is done before the database is actually modified,
    meaning that callbacks relying on the modified database will fail. This should be fixed within Brightway...
    """

    @property
    def metadata_changed(self):
        return calculation_setups_updater.metadata_changed

    def flush(self):
        patched().flush()
        calculation_setups_updater.emitLater("metadata_changed")


databases: Databases = databases
calculation_setups: CalculationSetups = calculation_setups
