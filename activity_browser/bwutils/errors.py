# -*- coding: utf-8 -*-

"""
A series of defined Errors and Warnings for the Activity Browser

Both Warnings and Exceptions are customized to enable custom handling (in bulk) of non-critical
errors.


"""
from bw2data.errors import *
from bw2io.errors import *


class ABError(Exception):
    """To be used as a generic Activity-Browser Error that will not lead to the AB crashing out"""

    pass


class ABWarning(Warning):
    """To be used as a generic Activity-Browser Warning"""

    pass


class ImportCanceledError(ABError):
    """Import of data was cancelled by the user."""

    pass


class LinkingFailed(ABError):
    """Unlinked exchanges remain after relinking."""

    pass


class IncompatibleDatabaseNamingError(ABError):
    """Database and keys do not match."""

    pass


class ActivityProductionValueError(ABError):
    """Production value for an activity == 0"""

    pass


class InvalidSDFEntryValue(ABError):
    """NA values found for data type that cannot hold \"NA\"."""

    pass


class ExchangeErrorValues(ABError):
    """In Brightway2 if there is an error in an exchange calculation the 'amount' field is not available for the
    Exchange"""

    pass


class ScenarioExchangeError(ABError):
    """In the AB we require the exchanges from the scenario file to be mappable to the databases. If this is not the
    case we MUST throw an error."""

    pass


class ReferenceFlowValueError(ABWarning):
    """While a user can technically perform a calculation with the reference flows all set to 0, such a calculation
    makes no logical sense and will lead to downstream errors (due to 0 results)."""

    pass


class DuplicatedScenarioExchangeWarning(ABWarning):
    """Will warn the user that a loaded scenario table contains duplicate exchanges. Only the last added exchange value
    will be used."""

    pass


class CriticalCalculationError(ABError):
    """Should be raised if some action during the running of the calculation causes a critical Exception that will fail
    the calculation. This is intended to be used with a Popup warning system that catches the original exception.
    """

    pass


class CriticalScenarioExtensionError(ABError):
    """Should be raised when combinging multiple scenario files by extension leads to zero scenario columns. Due to no
    scenario columns being found in common between the scenario files."""

    pass


class ScenarioDatabaseNotFoundError(ABError):
    """Should be raised when looking up one of the processes in an SDF file and the values used don't match those
    present in the local AB/BW databases."""

    pass


class ScenarioExchangeNotFoundError(ABError):
    """Should be raised when looking up a process key from the metadata in a scenario difference file, if THAT process
    key cannot be located in the local databases."""

    pass


class ScenarioExchangeDataNotFoundError(ABError):
    """Should be raised if no actual quantities for the exchanges can be found in the scenario difference file"""

    pass


class ScenarioExchangeDataNonNumericError(ABError):
    """Should be raised if non-numeric data is provided for the exchanges in a scenario difference file."""

    pass


class UnalignableScenarioColumnsWarning(ABWarning):
    """Should be raised if there is a mismatch between the scenario columns from multiple scenario difference files"""


class WrongFileTypeImportError(ABError):
    """Should be raised when a user tries to import the wrong type of file for the import in question.
    For example a database file with the scenario import dialog, or vice versa."""

    pass
