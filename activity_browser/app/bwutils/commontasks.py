# -*- coding: utf-8 -*-
import textwrap

import arrow
import brightway2 as bw
from bw2data.utils import natural_sort
from bw2data import databases

from ..settings import ab_settings


def wrap_text(string, max_length=80):
    """wrap the label making sure that key and name are in 2 rows"""
    # idea from https://stackoverflow.com/a/39134215/4929813
    wrapArgs = {'width': max_length, 'break_long_words': True, 'replace_whitespace': False}
    fold = lambda line, wrapArgs: textwrap.fill(line, **wrapArgs)
    return '\n'.join([fold(line, wrapArgs) for line in string.splitlines()])


def format_activity_label(act, style='pnl', max_length=40):
    try:
        a = bw.get_activity(act)

        if style == 'pnl':
            label = wrap_text(
                '\n'.join([a.get('reference product', ''), a.get('name', ''),
                           a.get('location', '')]), max_length=max_length)
        elif style == 'pl':
            label = wrap_text(', '.join([a.get('reference product', '') or a.get('name', ''),
                                         a.get('location', ''),
                                         ]), max_length=40)
        elif style == 'key':
            label = wrap_text(str(a.key))  # safer to use key, code does not always exist

        elif style == 'bio':
            label = wrap_text(',\n'.join(
                [a.get('name', ''), str(a.get('categories', ''))]), max_length=30
            )
        else:
            label = wrap_text(
                '\n'.join([a.get('reference product', ''), a.get('name', ''),
                           a.get('location', '')]))
    except:
        if isinstance(act, tuple):
            return wrap_text(str(''.join(act)))
        else:
            return wrap_text(str(act))
    return label


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
            'Database': ds['database'],
            'Uncertain': "True" if ds.get("uncertainty type", 0) > 1 else "False",
            'key': ds,
        }
        yield obj


def get_exchanges_data(exchanges):
    # TODO: not finished
    results = []
    for exc in exchanges:
        results.append(exc)
    for r in results:
        print(r)


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

def get_LCIA_method_name_dict(keys):
    """LCIA methods in brightway2 are stored in tuples, which is unpractical for display in, e.g. dropdown Menues.
    Returns a dictionary with
    key: comma separated string
    value: brightway2 method tuple
    """
    return {', '.join(key): key for key in keys}