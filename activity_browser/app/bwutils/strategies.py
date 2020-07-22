# -*- coding: utf-8 -*-
from typing import Collection

import brightway2 as bw
from bw2data.backends.peewee import ActivityDataset


def relink_exchanges_dbs(data: Collection, relink: dict) -> Collection:
    """Use this to relink exchanges during an actual import."""
    for act in data:
        for exc in act.get("exchanges", []):
            input_key = exc.get("input", ("", ""))
            if input_key[0] in relink:
                new_key = (relink[input_key[0]], input_key[1])
                try:
                    # try and find the new key
                    _ = bw.get_activity(new_key)
                    exc["input"] = new_key
                except ActivityDataset.DoesNotExist as e:
                    raise ValueError("Cannot relink exchange '{}', key '{}' not found.".format(exc, new_key)
                                     ).with_traceback(e.__traceback__)
    return data


def relink_exchanges_bw2package(data: dict, relink: dict) -> dict:
    """Use this to relink exchanges during an BW2Package import."""
    for key, value in data.items():
        for exc in value.get("exchanges", []):
            input_key = exc.get("input", ("", ""))
            if input_key[0] in relink:
                new_key = (relink[input_key[0]], input_key[1])
                try:
                    # try and find the new key
                    _ = bw.get_activity(new_key)
                    exc["input"] = new_key
                except ActivityDataset.DoesNotExist as e:
                    raise ValueError("Cannot relink exchange '{}', key '{}' not found.".format(exc, new_key)
                                     ).with_traceback(e.__traceback__)
    return data
