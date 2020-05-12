# -*- coding: utf-8 -*-
from typing import Iterable, List

import brightway2 as bw
import numpy as np
import pandas as pd

from .activities import data_from_index
from .utils import SUPERSTRUCTURE, EXCHANGE_KEYS


def parse_exchange_data(data: Iterable) -> dict:
    """Build a dictionary that can be fed into a superstructure DataFrame."""
    iterator = iter(data)
    ss_exc = next(iterator)
    inp = ss_exc.get("input")
    outp = ss_exc.get("output")
    result = {
        "from database": inp[0],
        "from key": inp,
        "to database": outp[0],
        "to key": outp,
        "from activity name": ss_exc.get("name"),
    }

    exc_type = ss_exc.get("type")
    if exc_type == "biosphere":
        result["from categories"] = ss_exc.get("categories")
    elif exc_type == "technosphere":
        result["from reference product"] = ss_exc.get("product")
        result["from location"] = ss_exc.get("location")

    # Now actually read the amounts from the exchanges.
    result.update(extract_amounts(data))
    return result


def extract_amounts(data: Iterable) -> dict:
    return {
        exc.get("output")[0]: exc.get("amount")
        for exc in data
    }


def create_scenario_index(data: Iterable) -> pd.Index:
    """Given an iterable of exchange dictionaries, build an ordered Index
    that represents the scenario names.
    """
    names = [x.get("output")[0] for x in data if "output" in x]
    return pd.Index(names)


def build_superstructure(data: list) -> pd.DataFrame:
    """Given a list of tuples, construct a Superstructure DataFrame.

    the first item in each will be the inital scenario (superstructure)
    with each following item representing a new scenario.
    """
    assert len(data) > 0, "Given list of data cannot be empty"

    initial = next(iter(data))
    len_first = len(initial)
    assert all(len_first == len(x) for x in data), "All items in the list must be of same length"

    df_index = SUPERSTRUCTURE.append(create_scenario_index(initial))
    struct_data = [
        parse_exchange_data(row)
        for row in data
    ]
    df = pd.DataFrame(struct_data, columns=df_index)
    return df


def superstructure_from_arrays(samples: np.ndarray, indices: np.ndarray, names: List[str] = None) -> pd.DataFrame:
    """Process indices into the superstructure itself, the samples represent
    the scenarios.
    """
    assert samples.ndim == 2, "Samples array should be 2-dimensional"
    assert indices.ndim == 1, "Indices array should be 1-dimensional"
    assert samples.shape[0] == indices.shape[0], "Length mismatch between arrays"
    if names is not None:
        assert len(names) == samples.shape[1], "Number of names should match number of samples columns"
        names = pd.Index(names)
    else:
        names = pd.Index(["scenario{}".format(i+1) for i in range(samples.shape[1])])

    # Construct superstructure from indices
    superstructure = pd.DataFrame(
        [data_from_index(idx) for idx in indices], columns=SUPERSTRUCTURE
    )
    # Construct scenarios from samples
    scenarios = pd.DataFrame(samples, columns=names)

    df = pd.concat([superstructure, scenarios], axis=1)
    return df


def match_exchanges(origin: dict, delta: Iterable, db_name: str) -> dict:
    """Matches a delta iterable against the superstructure dictionary,
    appending exchanges to the relevant keys.

    Any exchanges not present in the delta will have a very simple placeholder.
    """
    expected_len = len(next(iter(origin.values()))) + 1
    for exc in delta:
        keys = (exc.get("input")[1], exc.get("output")[1])
        assert keys in origin, "Exchange {} does not exist in superstructure".format(keys)
        origin[keys].append(exc)

    # Add 'None' values for exchanges that do not exist in the delta.
    for i in (m for m in origin.values() if len(m) != expected_len):
        i.append({"output": [db_name], "amount": 0})

    return origin


def construct_ss_dictionary(struct_excs: Iterable) -> dict:
    return {(x.get("input")[1], x.get("output")[1]): [x] for x in struct_excs}


def scenario_names_from_df(df: pd.DataFrame) -> list:
    """Returns the list of scenario names from a given superstructure.

    Strip out any possible carriage returns (excel junk)
    """
    # 'sort=False' ensures that order of scenario names is not altered.
    cols = df.columns.difference(SUPERSTRUCTURE, sort=False)
    return [
        str(x).replace("\n", " ").replace("\r", "") for x in cols
    ]


def guesstimate_flow_type(df: pd.DataFrame) -> pd.DataFrame:
    """Yes, this method guesses the flow type based on the key-pair given."""
    def guess(row: pd.Series) -> str:
        if row.iat[0][0] == bw.config.biosphere:
            return "biosphere"
        elif row.iat[0] == row.iat[1]:
            return "production"
        else:
            return "technosphere"

    keys = df.loc[:, EXCHANGE_KEYS]
    if keys.isna().any().all():
        print("Failed to insert flow types into the dataframe, keys missing.")
        return df
    df["flow type"] = keys.apply(guess, axis=1)
    return df
