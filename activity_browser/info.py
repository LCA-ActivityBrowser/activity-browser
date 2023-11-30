import ast
from importlib.metadata import version, PackageNotFoundError
from .utils import safe_link_fetch, sort_semantic_versions

import logging
from .logger import ABHandler
logger = logging.getLogger('ab_logs')
log = ABHandler.setup_with_logger(logger, __name__)

# get AB version
try:
    __version__ = version(__package__)
except PackageNotFoundError:
    __version__ = "0.0.0"

# get compatible versions of ecoinvent for this AB version
try:
    # read versions
    versions_URL = 'https://raw.githubusercontent.com/marc-vdm/activity-browser/better_biosphere_handling/compatible_ei_versions.txt'
    success, page = safe_link_fetch(versions_URL)
    if not success:
        raise Exception(page)
    all_versions = ast.literal_eval(page.text)
    sorted_versions = sort_semantic_versions(all_versions.keys())

    # select either the latest lower version available or if none available the lowest version for safety
    for ab_version in sorted_versions:
        if sort_semantic_versions([__version__, ab_version])[0] == __version__:
            # current version is higher than or equal to tested AB version:
            ei_versions = all_versions[ab_version]
            break
    else:
        ei_versions = all_versions[sorted_versions[-1]]

    log.debug(f'following versions of ecoinvent are compatible with AB {__version__}: {ei_versions}')
    __ei_versions__ = ei_versions
except Exception as e:
    log.debug(f'Reading compatible ecoinvent versions failed with the following error: {e}')
    __ei_versions__ = {}