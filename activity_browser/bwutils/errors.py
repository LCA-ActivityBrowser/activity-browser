# -*- coding: utf-8 -*-


class ImportCanceledError(Exception):
    """Import of data was cancelled by the user."""
    pass


class LinkingFailed(Exception):
    """Unlinked exchanges remain after relinking."""
    pass
