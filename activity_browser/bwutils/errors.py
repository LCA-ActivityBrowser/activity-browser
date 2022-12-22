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