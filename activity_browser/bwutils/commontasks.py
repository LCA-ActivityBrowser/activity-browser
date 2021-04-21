# -*- coding: utf-8 -*-
from datetime import datetime as dt
import hashlib
from pathlib import Path
import os
import textwrap
import arrow
import brightway2 as bw
from bw2data import databases
from bw2data.proxies import ActivityProxyBase
from bw2data.utils import natural_sort
from bw2data.project import ProjectDataset, SubstitutableDatabase

from .importers import ABPackage

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
        elif style == 'pnld':
            label = ' | '.join([act.get('reference product', ''), act.get('name', ''),
                           str(act.get('location', '')), act.get('database', ''),])
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

def update_and_shorten_label(label, text, length=15, enable=True) -> None:
    """update and shorten label text to given given length and move entire name to tooltip.

    Can be useful for shortening database names

    label: Label object
    text: original label text
    length: cut-off length
    enable: enable/disable cut-off"""

    tooltip = ''
    if enable and len(text) > length:
        tooltip = text
        text = text[:(length - 3)] + '...'

    label.setText('[{}]'.format(text))
    label.setToolTip(tooltip)

# Switch brightway directory
def switch_brightway2_dir(dirpath):
    if dirpath == bw.projects._base_data_dir:
        print('dirpath already loaded')
        return False
    try:
        assert os.path.isdir(dirpath)
        bw.projects._base_data_dir = dirpath
        bw.projects._base_logs_dir = os.path.join(dirpath, "logs")
        # create folder if it does not yet exist
        if not os.path.isdir(bw.projects._base_logs_dir):
            os.mkdir(bw.projects._base_logs_dir)
        # load new brightway directory
        bw.projects.db = SubstitutableDatabase(
            os.path.join(bw.projects._base_data_dir, "projects.db"),
            [ProjectDataset]
        )
        print('Loaded brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        return True

    except AssertionError:
        print('Could not access BW_DIR as specified in settings.py')
        return False

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


def is_technosphere_db(db_name: str) -> bool:
    """Returns True if database describes the technosphere, False if it describes a biosphere."""
    if not db_name in bw.databases:
        raise KeyError("Not an existing database:", db_name)
    act = bw.Database(db_name).random()
    if act is None or act.get("type", "process") == "process":
        return True
    else:
        return False


def is_technosphere_activity(activity: ActivityProxyBase) -> bool:
    """ Avoid database lookups by testing the activity for a type, calls the
    above method if the field does not exist.
    """
    if "type" not in activity:
        return is_technosphere_db(activity.key[0])
    return activity.get("type") == "process"


def store_database_as_package(db_name: str, directory: str = None) -> bool:
    """ Attempt to use `bw.BW2Package` to save the given database as an
    isolated package that can be shared with others.
    Returns a boolean signifying success or failure.
    """
    if db_name not in bw.databases:
        return False
    metadata = bw.databases[db_name]
    db = bw.Database(db_name)
    directory = directory or bw.projects.output_dir
    output_dir = Path(directory)
    if output_dir.suffix == ".bw2package":
        out_file = output_dir
    else:
        out_file = output_dir / "{}.bw2package".format(db.filename)
    # First, ensure the metadata on the database is up-to-date.
    modified = dt.strptime(metadata["modified"], "%Y-%m-%dT%H:%M:%S.%f")
    if "processed" in metadata:
        processed = dt.strptime(metadata["processed"], "%Y-%m-%dT%H:%M:%S.%f")
        if processed < modified:
            db.process()
    else:
        db.process()
    # Now that processing is done, perform the export.
    ABPackage.unrestricted_export(db, out_file)
    return True


def import_database_from_package(filepath: str, alternate_name: str = None) -> (str, bool):
    """ Make use of `bw.BW2Package` to import a database-like object
    from the given file path.
    Returns a string and boolean signifying the database name (if found)
    and the success or failure of the import.
    """
    data = bw.BW2Package.import_file(filepath=filepath)
    db = next(iter(data))
    if alternate_name:
        db.rename(alternate_name)
    return db.name, True


def count_database_records(name: str) -> int:
    """To account for possible brightway database types that do not implement
    the __len__ method.
    """
    db = bw.Database(name)
    try:
        return len(db)
    except TypeError as e:
        print("{}. Counting manually".format(e))
        return sum(1 for _ in db)


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
    "Categories": "categories",
    "Type": "type",
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

    These are ' -,.%[]'
    Integers are also removed aggressively, there are allowed, but not
    at the start of a parameter name.
    """
    remove = ",.%[]()0123456789"
    replace = " -"
    # Remove invalid characters
    for char in remove:
        if char in activity_name:
            activity_name = activity_name.replace(char, "")
    # Replace spacing and dashes with underscores
    for char in replace:
        if char in activity_name:
            activity_name = activity_name.replace(char, "_")
    # strip underscores from start of string
    activity_name = activity_name.lstrip("_")
    return activity_name


def build_activity_group_name(key: tuple, name: str = None) -> str:
    """ Constructs a group name unique to a given bw activity.

    If given a `name`, use that instead of looking up the activity name.

    NOTE: The created group name is not easy for users to understand, so hide
    it from them where possible.
    """
    simple_hash = hashlib.md5(":".join(key).encode()).hexdigest()
    if name:
        return "{}_{}".format(name, simple_hash)
    act = bw.get_activity(key)
    clean = clean_activity_name(act.get("name"))
    return "{}_{}".format(clean, simple_hash)


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


# LCIA
def unit_of_method(method):
    assert method in bw.methods
    return bw.methods[method].get('unit')

def get_LCIA_method_name_dict(keys):
    """Impact categories in brightway2 are stored in tuples, which is unpractical for display in, e.g. dropdown Menues.
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
