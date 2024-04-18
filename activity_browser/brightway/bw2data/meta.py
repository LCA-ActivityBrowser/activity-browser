from bw2data.meta import *

from activity_browser.signals import qdatabases, qcalculation_setups, qmethods
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
        return qdatabases.metadata_changed

    def flush(self):
        patched().flush()
        qdatabases.emitLater("metadata_changed")


@patch_superclass
class CalculationSetups(CalculationSetups):
    @property
    def metadata_changed(self):
        return qcalculation_setups.metadata_changed

    def flush(self):
        patched().flush()
        qcalculation_setups.emitLater("metadata_changed")


@patch_superclass
class Methods(Methods):
    @property
    def metadata_changed(self):
        return qmethods.metadata_changed

    def flush(self):
        patched().flush()
        qmethods.emitLater("metadata_changed")


databases: Databases = databases
calculation_setups: CalculationSetups = calculation_setups
methods: Methods = methods
