import ast
from importlib.metadata import version, PackageNotFoundError
from .utils import safe_link_fetch

# get AB version
try:
    __version__ = version(__package__)
except PackageNotFoundError:
    __version__ = "0.0.0"

# get available versions of ecoinvent per AB version
try:
    versions_URL = 'https://raw.githubusercontent.com/marc-vdm/activity-browser/better_biosphere_handling/compatible_ei_versions.txt'
    success, page = safe_link_fetch(versions_URL)
    if not success:
        raise Exception(page)
    page = page.text
    __ei_versions__ = page.text
except Exception as e:
    print('err:', e)
    __ei_versions__ = {}