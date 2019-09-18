# -*- coding: utf-8 -*-
import textwrap
import arrow
import brightway2 as bw
from bw2data import databases
from bw2data.utils import natural_sort

from ..settings import ab_settings, project_settings

"""
bwutils is a collection of methods that build upon brightway2 and are generic enough to provide here so that we avoid 
re-typing the same code in different parts of the Activity Browser.

When adding new methods, please use the sections below (or add a new section, if required).
"""


# Formatting
def wrap_text(string, max_length=80):
    """wrap the label making sure that key and name are in 2 rows"""
    # idea from https://stackoverflow.com/a/39134215/4929813
    wrapArgs = {'width': max_length, 'break_long_words': True, 'replace_whitespace': False}
    fold = lambda line, wrapArgs: textwrap.fill(line, **wrapArgs)
    return '\n'.join([fold(line, wrapArgs) for line in string.splitlines()])


def format_activity_label(key, style='pnl', max_length=40):
    try:
        act = bw.get_activity(key)

        if style == 'pnl':
            label = '\n'.join([act.get('reference product', ''), act.get('name', ''),
                           str(act.get('location', ''))])
        elif style == 'pnl_':
            label = ' | '.join([act.get('reference product', ''), act.get('name', ''),
                           str(act.get('location', ''))])
        elif style == 'pl':
            label = ', '.join([act.get('reference product', '') or act.get('name', ''),
                                         str(act.get('location', '')),])
        elif style == 'key':
            label = str(act.key)  # safer to use key, code does not always exist

        elif style == 'bio':
            label = ',\n'.join([act.get('name', ''), str(act.get('categories', ''))])
        else:
            label = '\n'.join([act.get('reference product', ''), act.get('name', ''),
                           str(act.get('location', ''))])
    except:
        if isinstance(key, tuple):
            return wrap_text(str(''.join(key)))
        else:
            return wrap_text(str(key))
    return wrap_text(label, max_length=max_length)


# Database
def get_database_metadata(name):
    """ Returns a dictionary with database meta-information. """
    d = dict()
    d['Name'] = name
    d['Depends'] = "; ".join(databases[name].get('depends', []))
    dt = databases[name].get('modified', '')
    if dt:
        dt = arrow.get(dt).humanize()
    d['Last modified'] = dt
    return d


def get_databases_data(databases):
    """Returns a list with dictionaries that describe the available databases."""
    data = []
    for row, name in enumerate(natural_sort(databases)):
        data.append(get_database_metadata(name))
    yield data


def get_editable_databases():
    editable_dbs = []
    databases_read_only_settings = project_settings.settings.get('read-only-databases', {})
    for db_name, read_only in databases_read_only_settings.items():
        if not read_only and db_name != 'biosphere3':
            editable_dbs.append(db_name)
    return editable_dbs


def is_database_read_only(db_name):
    if "read-only-databases" in project_settings.settings:
        return project_settings.settings["read-only-databases"].get(db_name, True)


def is_technosphere_db(db_name):
    """Returns True if database describes the technosphere, False if it describes a biosphere."""
    if not db_name in bw.databases:
        raise KeyError('Not an existing database:', db_name)
    db = bw.Database(db_name)
    act = db.random()
    if act.get('type', 'process') == "process":
        return True
    else:
        return False


# Activity
AB_names_to_bw_keys = {
    "Amount": "amount",
    "Product": "reference product",
    "Activity": "name",
    "Unit": "unit",
    "Location": "location",
    "Database": "database",
    "Uncertainty": "uncertainty type",
    "Formula": "formula",
}

bw_keys_to_AB_names = {v: k for k, v in AB_names_to_bw_keys.items()}

def get_activity_data(datasets):
    # if not fields:
    #     fields = ["name", "reference product", "amount", "location", "unit", "database"]
    # obj = {}
    # for field in fields:
    #     obj.update({field: key.get(field, '')})
    # obj.update({"key": key})
    for ds in datasets:
        obj = {
            'Activity': ds.get('name', ''),
            'Reference product': ds.get('reference product', ''),  # only in v3
            'Location': ds.get('location', 'unknown'),
            # 'Amount': "{:.4g}".format(key['amount']),
            'Unit': ds.get('unit', 'unknown'),
            'Database': ds.get(['database'], 'unknown'),
            'Uncertain': "True" if ds.get("uncertainty type", 0) > 1 else "False",
            'key': ds,
        }
        yield obj


def get_activity_name(key, str_length=22):
    return ','.join(key.get('name', '').split(',')[:3])[:str_length]


def clean_activity_name(activity_name: str) -> str:
    """ Takes a given activity name and remove or replace all characters
    not allowed to be in there.

    Use this when creating parameters, as there are specific characters not
    allowed to be in parameter names.

    These are ' -,.%[]' and all integers
    """
    remove = ",.%[]0123456789"
    replace = " -"
    for char in remove:
        if char in activity_name:
            activity_name = activity_name.replace(char, "")
    for char in replace:
        if char in activity_name:
            activity_name = activity_name.replace(char, "_")
    return activity_name


def get_activity_data_as_lists(act_keys, keys=None):
    results = dict()
    for key in keys:
        results[key] = []

    for act_key in act_keys:
        act = bw.get_activity(act_key)
        for key in keys:
            results[key].append(act.get(key, 'Unknown'))

    return results


def identify_activity_type(activity):
    """Return the activity type based on its naming."""
    name = activity["name"]
    if "treatment of" in name:
        return "treatment"
    elif "market for" in name:
        # if not "to generic" in name:  # these are not markets, but also transferring activities
        return "market"
    elif "market group" in name:
        # if not "to generic" in name:
        return "marketgroup"
    else:
        return "production"


# Exchanges
def get_exchanges_data(exchanges):
    # TODO: not finished
    results = []
    for exc in exchanges:
        results.append(exc)
    for r in results:
        print(r)


# Settings (directory, project, etc.)
def get_startup_bw_dir():
    """Returns the brightway directory as defined in the settings file.
    If it has not been defined here, it returns the brightway default directory."""
    return ab_settings.settings.get('custom_bw_dir', get_default_bw_dir())


def get_default_bw_dir():
    """Returns the default brightway directory."""
    return bw.projects._get_base_directories()[0]


def get_current_bw_dir():
    """Returns the current used brightway directory."""
    return bw.projects._base_data_dir


def get_startup_project_name():
    """Returns the startup or default project name."""
    custom_startup = ab_settings.settings.get('startup_project')
    if custom_startup in bw.projects:
        return ab_settings.settings['startup_project']
    else:
        return get_default_project_name()


def get_default_project_name():
    """Returns the default project name."""
    if "default" in bw.projects:
        return "default"
    elif len(bw.projects):
        return next(iter(bw.projects)).name
    else:
        return None


# LCIA
def unit_of_method(method):
    assert method in bw.methods
    return bw.methods[method].get('unit')

def get_LCIA_method_name_dict(keys):
    """LCIA methods in brightway2 are stored in tuples, which is unpractical for display in, e.g. dropdown Menues.
    Returns a dictionary with
    keys: comma separated strings
    values: brightway2 method tuples
    """
    return {', '.join(key): key for key in keys}


#
# def get_locations_in_db(db_name):
#     """returns the set of locations in a database"""
#     db = bw.Database(db_name)
#     loc_set = set()
#     [loc_set.add(act.get("location")) for act in db]
#     return loc_set
