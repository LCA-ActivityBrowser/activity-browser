# -*- coding: utf-8 -*-
from ast import literal_eval

from bw2data.backends.peewee import ExchangeDataset
import numpy as np
import pandas as pd
import presamples as ps
from presamples.packaging import format_matrix_data, to_2d, to_array

from ..utils import Index
from .dataframe import scenario_names_from_df
from .utils import SUPERSTRUCTURE, EXCHANGE_KEYS, INDEX_KEYS


def build_presamples_array_from_df(df: pd.DataFrame) -> (np.ndarray, np.ndarray):
    """Construct a presamples package from a superstructure DataFrame."""
    keys = df.loc[pd.IndexSlice[:, EXCHANGE_KEYS]]
    scenario_columns = df.columns.difference(SUPERSTRUCTURE, sort=False)
    values = df.loc[pd.IndexSlice[:, scenario_columns]]
    assert keys.notna().all().all(), "Need all the keys for this."
    exchanges = (
        ExchangeDataset.get(
            input_database=x[0][0], input_code=x[0][1],
            output_database=x[1][0], output_code=x[1][1],
        ) for x in keys.itertuples(index=False)
    )
    indices = [Index.build_from_exchange(exc) for exc in exchanges]

    result = np.zeros(len(indices), dtype=object)
    for i, idx in enumerate(indices):
        result[i] = (idx.input, idx.output, idx.input.database_type)
    return result, values.to_numpy()


def build_arrays_from_df(df: pd.DataFrame) -> (np.ndarray, np.ndarray):
    """Construct a presamples package from a superstructure DataFrame.

    Shortcut over the previous method, avoiding database calls improves
    speed at the cost of not throwing 'NotFound' exceptions.
    """
    keys = df.loc[:, EXCHANGE_KEYS]
    scenario_columns = df.columns.difference(SUPERSTRUCTURE, sort=False)
    values = df.loc[:, scenario_columns]
    assert keys.notna().all().all(), "Need all the keys for this."
    data = df.loc[:, INDEX_KEYS].rename(columns={"from key": "input", "to key": "output"})
    indices = [
        Index.build_from_dict(x) for x in data.to_dict("records")
    ]

    result = np.zeros(len(indices), dtype=object)
    for i, idx in enumerate(indices):
        result[i] = (idx.input, idx.output, idx.input.database_type)
    return result, values.to_numpy()


def scenario_names_to_string(df: pd.DataFrame) -> str:
    """Returns the scenario names from the superstructure as a string"""
    return str(tuple(scenario_names_from_df(df)))


def scenario_names_from_string(description: str) -> pd.Series:
    """ Convert a given string into a pd.Series, use to generate scenario
    names from the description field of PresampleResource
    """
    return pd.Series(data=[str(x) for x in literal_eval(description)])


def process_arrays_to_package(indices: np.ndarray, values: np.ndarray) -> list:
    """ Follow along `presamples` path of splitting the inventories and
    formatting the exchange indexes into numpy arrays.

    Instead of writing the entire thing to a file, return the list of formatted
    data.
    """
    package = []
    arrays = ps.split_inventory_presamples(values, indices)
    for obj in arrays:
        samples, indices, kind, *other = obj
        samples = to_2d(to_array(samples))
        # Convert the key indexes to the actual db ids
        indices, metadata = format_matrix_data(indices, kind, *other)
        metadata["type"] = kind
        package.append((samples, indices, metadata))
    return package
