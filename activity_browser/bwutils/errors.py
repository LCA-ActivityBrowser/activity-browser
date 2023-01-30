# -*- coding: utf-8 -*-


class ImportCanceledError(Exception):
    """Import of data was cancelled by the user."""
    pass


class LinkingFailed(Exception):
    """Unlinked exchanges remain after relinking."""
    pass


class IncompatibleDatabaseNamingError(Exception):
    """Database and keys do not match."""
    pass


class ActivityProductionValueError(Exception):
    """Production value for an activity == 0"""
    pass


class InvalidSDFEntryValue(Exception):
    """NA values found for data type that cannot hold \"NA\"."""
    pass


class ExchangeErrorValues(Exception):
    """In Brightway2 if there is an error in an exchange calculation the 'amount' field is not available for the
        Exchange"""
    pass


class ReferenceFlowValueError(Warning):
    """While a user can technically perform a calculation with the reference flows all set to 0, such a calculation
     makes no logical sense and will lead to downstream errors (due to 0 results)."""
    pass