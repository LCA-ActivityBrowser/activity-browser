from bw2data.meta import *

from activity_browser.signals import qcalculation_setups, qdatabases, qmethods

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
        """
        Shorthand for connecting to the qdatabases QUpdater. Developers can import 'databases' from bw2data and connect
        directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qdatabases.metadata_changed

    def flush(self, signal: bool = True):
        """
        Emit that the databases have changed when it's data is flushed to disk a.k.a. saved.
        """
        # execute the patched function for standard functionality
        patched[Databases]["flush"](self, signal)
        # emit that the databases metadata have changed through the qUpdater
        qdatabases.emitLater("metadata_changed")


@patch_superclass
class CalculationSetups(CalculationSetups):
    @property
    def metadata_changed(self):
        """
        Shorthand for connecting to the qcalculation-setups QObject. Developers can import 'databases' from bw2data
        and connect directly, instead of importing the related QObject via activity_browser.signals
        """
        return qcalculation_setups.metadata_changed

    def flush(self, signal: bool = True):
        """
        Emit that the calculation setups have changed when it's data is flushed to disk a.k.a. saved.
        """
        # execute the patched function for standard functionality
        patched[CalculationSetups]["flush"](self, signal)
        # emit that the calculation setups metadata have changed through the qUpdater
        qcalculation_setups.emitLater("metadata_changed")


@patch_superclass
class Methods(Methods):
    @property
    def metadata_changed(self):
        """
        Shorthand for connecting to the qmethods QObject. Developers can import 'databases' from bw2data and connect
        directly, instead of importing the related QObject via activity_browser.signals
        """
        return qmethods.metadata_changed

    def flush(self, signal: bool = True):
        """
        Emit that the methods have changed when it's data is flushed to disk a.k.a. saved.
        """
        # execute the patched function for standard functionality
        patched[Methods]["flush"](self, signal)
        # emit that the methods metadata have changed through the qUpdater
        qmethods.emitLater("metadata_changed")


# reimport the patched singletons, but adding the type-hint so IDE's know what functionality has been added/patched
databases: Databases = databases
calculation_setups: CalculationSetups = calculation_setups
methods: Methods = methods
