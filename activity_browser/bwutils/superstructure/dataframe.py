# -*- coding: utf-8 -*-
from typing import List, Tuple
from PySide2.QtWidgets import QMessageBox
import sys

import brightway2 as bw
import numpy as np
import pandas as pd

from ..commontasks import AB_names_to_bw_keys
from ..metadata import AB_metadata
from ..utils import Index
from .activities import data_from_index
from .utils import SUPERSTRUCTURE
from .file_imports import ABPopup
from ..errors import ABError

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

    Parameters
    ----------

    df_ : the dataframe that is produced from the supplied scenario files provided to the AB

    replacements : a dictionary of key-value pairs where the key corresponds to the database in the supplied dataframe
            and the value corresponds to the respective database in the local brightway environment

    bw_dbs : a list of Brightway databases held locally
    """
    df = df_.loc[(df_['from database'].isin(replacements.keys())) | (df_['to database'].isin(replacements.keys()))].copy(True)
    FROM_FIELDS = pd.Index([
        "from activity name", "from categories",
        "from reference product", "from location",
        ])
    TO_FIELDS = pd.Index(["to activity name", "to categories",
                          "to reference product", "to location"
    ])
    DB_FIELDS = ['name', 'categories', 'reference product', 'location']
    critical = {'from database': [], 'from activity name': [], 'to database': [], 'to activity name': []}  # To be used in the exchange_replace_database internal method scope
    changes = ['from database', 'from key', 'to database', 'to key']
    # this variable will accumulate the activity names and databases for the activities in both
    # directions
    # for those databases not loaded into the metadata load them
    AB_metadata.add_metadata(replacements.values())
    metadata = AB_metadata.dataframe

    def exchange_replace_database(ds: pd.Series, replacements: dict, critical: list) -> tuple:
        """  For a row in the scenario dataframe check the databases involved for whether replacement is required.
            If so use the key-value pair within the replacements dictionary to replace the dictionary names
            and obtain the correct activity key
        """
        for i, fields in enumerate([FROM_FIELDS, TO_FIELDS]):
            db_name = ds[['from database', 'to database'][i]]
            # check to see whether we can skip the activity, or not
            if db_name not in replacements.keys():
                continue
            # if we can't link the activity key then we try to find it
            try:
                if isinstance(ds[fields[1]], float):
                    key = metadata[(metadata[DB_FIELDS[0]] == ds[fields[0]]) &
                                                (metadata[DB_FIELDS[2]] == ds[fields[2]]) &
                                                (metadata[DB_FIELDS[3]] == ds[fields[3]])].copy()
                else:
                    key = metadata[(metadata[DB_FIELDS[0]] == ds[fields[0]]) &
                                    (metadata[DB_FIELDS[1]] == ds[fields[1]])].copy()
                for j, col in enumerate([['from key', 'from database'], ['to key', 'to database']][i]):
#                    ds.loc[ds[col]] = (key['database'][0], key['code'][0]) if j == 0 else key['database'][0]
                    ds.loc[col] = (key['database'][0], key['code'][0]) if j == 0 else key['database'][0]
            # if the key is not discoverable then we add an exception that we can handle later
            except Exception as e:
                if len(critical['from database']) <= 5:
                    critical['from database'].append(ds['from database'])
                    critical['from activity name'].append(ds['from activity name'])
                    critical['to database'].append(ds['to database'])
                    critical['to activity name'].append(ds['to activity name'])
        return ds
    # actual replacement of the activities in the main method
    for idx in df.index:
        df.loc[idx, changes] = exchange_replace_database(df.loc[idx, :], replacements, critical)[changes]
        sys.stdout.write("\r{}".format(idx/df.shape[0]))
        sys.stdout.flush()
    # prepare a warning message in case unlinkable activities were found in the scenario dataframe
    if critical['from database']:
        critical_message = ABPopup()
        critical_message.dataframe(pd.DataFrame(critical),
                                       ['from database', 'from activity name', 'to database', 'to activity name'])
        if len(critical['from database']) > 1:
            msg = f"Multiple activities in the exchange flows could not be linked. The first five of these are provided.\n\n" \
                  f"If you want to proceed with the import then press 'Ok' (doing so will enable you to save the dataframe\n" \
                  f"to either .csv, or .xlsx formats), otherwise press 'Cancel'"
            response = critical_message.abCritical("Activities not found", msg, QMessageBox.Save, QMessageBox.Cancel, default=2)
        else:
            msg = f"An activity in the exchange flows could not been linked (See below for the activity).\n\nIf you want to" \
                  f"proceed with the import then press 'Ok' (doing so will enable you to save the dataframe to\n either .csv," \
                  f"or .xlsx formats), otherwise press 'Cancel'"
            response = critical_message.abCritical("Activity not found", msg, QMessageBox.Save, QMessageBox.Cancel, default=2)
        if response == critical_message.Cancel:
            return pd.DataFrame({}, columns=df.columns)
        else:
            critical_message.save_dataframe(df)
            raise ABError("Incompatible Databases in the scenario file, unable to complete further checks on the file")
    else:
        df_.loc[df.index] = df
    return df_
