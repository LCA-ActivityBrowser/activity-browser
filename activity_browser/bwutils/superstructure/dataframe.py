# -*- coding: utf-8 -*-
from typing import List, Tuple
from PySide2.QtWidgets import QMessageBox

import brightway2 as bw
import numpy as np
import pandas as pd

from ..utils import Index
from .activities import data_from_index
from .utils import SUPERSTRUCTURE
from .file_imports import ABPopup

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
        map(data_from_index, indices), columns=SUPERSTRUCTURE
    )
    # Construct scenarios from samples
    scenarios = pd.DataFrame(samples, columns=names)

    df = pd.concat([superstructure, scenarios], axis=1)
    return df


def arrays_from_indexed_superstructure(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    result = np.zeros(df.shape[0], dtype=object)
    for i, data in enumerate(df.index.to_flat_index()):
        result[i] = Index.build_from_dict(
            {"input": data[0], "output": data[1], "flow type": data[2]}
        )
    return result, df.to_numpy(dtype=float)


def filter_databases_indexed_superstructure(df: pd.DataFrame, include: set) -> pd.DataFrame:
    """Filters the given superstructure so that only indexes where the output
    database is in the `include` set are valid.
    """
    return df.loc[[x[1][0] in include for x in df.index.to_flat_index()], :]


def scenario_columns(df: pd.DataFrame) -> pd.Index:
    # 'sort=False' ensures that order of scenario names is not altered.
    return df.columns.difference(SUPERSTRUCTURE, sort=False)


def scenario_names_from_df(df: pd.DataFrame) -> List[str]:
    """Returns the list of scenario names from a given superstructure.

    Strip out any possible carriage returns (excel junk)
    """
    cols = scenario_columns(df)
    return [
        str(x).replace("\n", " ").replace("\r", "") for x in cols
    ]

def scenario_replace_databases(df_: pd.DataFrame, replacements: dict) -> pd.DataFrame:
    """ For a provided dataframe the function will check for the presence of a unidentified database for all rows.
    If an unidentified database is found as a key in the replacements argument the corresponding value provided is used
    to provide an alternative database. The corresponding key for the activity from the unidentified database is
    collected from the provided alternative.

    If an activity cannot be identified within the provided database a warning message is provided. The process can
    either be terminated, or can proceed without replacement of those activities not identified (the unidentified
    database names in these instances will be retained)

    """
    df = df_.copy(True)
    FROM_FIELDS = pd.Index([
        "from activity name", "from categories",
        "from reference product", "from location",
        ])
    TO_FIELDS = pd.Index(["to activity name", "to categories",
                          "to reference product", "to location"
    ])
    FILTER_FIELDS = ['name', 'categories', 'reference product', 'location']

    # TODO the following method can be removed on updating to bw2.5
    def filter(_activity, values, fields):
        """ Return True if the _activity matches the input (values) from the data series, based on the fields (Used to
        determine the direction ('to', or 'from'))
        """
        for i in range(len(FILTER_FIELDS)):
            try:
                # first do we need to check all the elements in a tuple
                if FILTER_FIELDS[i] == 'categories' and _activity['categories']:
                    value = values[fields[i]]
                    for j, c in enumerate(value[1: -1].split(', ') if isinstance(value, str) else enumerate(value)):
                        if _activity[FILTER_FIELDS[i]][j] != c[1:-1]:
                            return 0
                # otherwise run a simple equality check for the scalar fields
                elif _activity[FILTER_FIELDS[i]] != values[fields[i]]:
                    return 0
            except (KeyError, IndexError) as e:
                pass
        return 1
    def exchange_replace_database(ds: pd.Series, replacements: dict) -> tuple:
        """  For a row in the scenario dataframe check the databases involved for whether replacement is required.
            If so use the key-value pair within the replacements dictionary to replace the dictionary names
            and obtain the correct activity key
        """
        critical = list()
        for i, fields in enumerate([FROM_FIELDS, TO_FIELDS]):
            db_name = ds[['from database', 'to database'][i]]
            if db_name not in replacements.keys():
                continue
            db = bw.Database(replacements[db_name])
             #TODO update this following section to use get_node from bw2data.utils when updating to bw2.5
            activities = db.search(ds[fields[0]])
            if not activities:
 #               critical = ABPopup()
 #               msg = f"An activity from {db_name} could not be located in {replacements[db_name]}. The activity from {db_name} will be retained if you wish to proceed (press ok), otherwise press cancel"
 #               response = critical.abCritical("Activity not found", msg, QMessageBox.Ok, QMessageBox.Cancel)
 #               if critical.Cancel == response:
 #                   raise Exception()
                break
            filtered = [act for act in activities if filter(act, ds, fields)]
            if len(filtered) > 0:
                for j, col in enumerate([['from key', 'from database'], ['to key', 'to database']][i]):
                    ds[col] = (filtered[0]['database'], filtered[0]['code']) if j == 0 else filtered[0]['database']
        return ds
    # Code for scenario_replace_dataframe
    try:
        df = df.apply(lambda row: exchange_replace_database(row, replacements), axis=1)
    except:
        return
    return df