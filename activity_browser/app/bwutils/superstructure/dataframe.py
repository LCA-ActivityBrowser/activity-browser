# -*- coding: utf-8 -*-
from typing import List

import brightway2 as bw
import numpy as np
import pandas as pd

from ..utils import Index
from .activities import data_from_index
from .utils import SUPERSTRUCTURE, EXCHANGE_KEYS, INDEX_KEYS


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


def arrays_from_superstructure(df: pd.DataFrame) -> (np.ndarray, np.ndarray):
    """Construct a presamples package from a superstructure DataFrame.

    Shortcut over the previous method, avoiding database calls improves
    speed at the risk of allowing possibly invalid data.
    """
    assert df.loc[:, EXCHANGE_KEYS].notna().all().all(), "Need all the keys for this."
    data = df.loc[:, INDEX_KEYS].rename(columns={"from key": "input", "to key": "output"})
    result = np.zeros(data.shape[0], dtype=object)
    for i, data in enumerate(data.to_dict("records")):
        result[i] = Index.build_from_dict(data)
    values = df.loc[:, df.columns.difference(SUPERSTRUCTURE, sort=False)]
    return result, values.to_numpy()


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
