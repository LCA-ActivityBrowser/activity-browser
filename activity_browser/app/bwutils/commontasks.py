# -*- coding: utf-8 -*-
import arrow
import brightway2 as bw
from bw2data.utils import natural_sort
from bw2data import databases


def format_activity_label(act, style='pnl'):
    try:
        a = bw.get_activity(act)

        if style == 'pnl':
            label = '\n'.join([a.get('reference product',''),
                               a['name'],
                               a['location'],
                               ])
        elif style == 'pl':
            label = ', '.join([a.get('reference product') or a.get('name'),
                               a['location'],
                               ])
        elif style == 'key':
            label = tuple([a['database'], a['code']])

        elif style == 'bio':
            label = ', '.join([a['name'],
                               str(a['categories']),
                               ])
        else:
            label = '\n'.join([a.get('reference product',''),
                               a['name'],
                               a['location'],
                               ])
    except:
        if isinstance(act, tuple):
            return str(''.join(act))
        else:
            return str(act)
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
