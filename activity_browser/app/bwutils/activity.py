# -*- coding: utf-8 -*-
import copy

import brightway2 as bw
from bw2data.backends.peewee.proxies import ExchangeDataset, Activity
from bw2data.backends.peewee.utils import dict_as_exchangedataset


def copy_to_db(activity, database):
    """modified from bw2data.backends.peewee.proxies.Activity.copy"""
    new_act = Activity()
    for key, value in activity.items():
        new_act[key] = value
    new_act._data['database'] = database.name
    new_act.save()
    for exc in activity.exchanges():
        data = copy.deepcopy(exc._data)
        data['output'] = new_act.key
        # Change `input` for production exchanges
        if exc['input'] == exc['output']:
            data['input'] = new_act.key
        ExchangeDataset.create(**dict_as_exchangedataset(data))
    bw.databases.clean()
    return new_act
