# -*- coding: utf-8 -*-
import ast
import sys
from typing import List, Tuple

import numpy as np
import pandas as pd
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication, QPushButton

from ..errors import ScenarioDatabaseNotFoundError
from ..metadata import AB_metadata
from ..utils import Index
from .activities import data_from_index
from .file_dialogs import ABPopup
from .utils import SUPERSTRUCTURE


def superstructure_from_arrays(
    samples: np.ndarray, indices: np.ndarray, names: List[str] = None
) -> pd.DataFrame:
    """Process indices into the superstructure itself, the samples represent
    the scenarios.
    """
    assert samples.ndim == 2, "Samples array should be 2-dimensional"
    assert indices.ndim == 1, "Indices array should be 1-dimensional"
    assert samples.shape[0] == indices.shape[0], "Length mismatch between arrays"
    if names is not None:
        assert (
            len(names) == samples.shape[1]
        ), "Number of names should match number of samples columns"
        names = pd.Index(names)
    else:
        names = pd.Index(["scenario{}".format(i + 1) for i in range(samples.shape[1])])

    # Construct superstructure from indices
    superstructure = pd.DataFrame(map(data_from_index, indices), columns=SUPERSTRUCTURE)
    # Construct scenarios from samples
    scenarios = pd.DataFrame(samples, columns=names)

    df = pd.concat([superstructure, scenarios], axis=1)
    return df


def arrays_from_indexed_superstructure(
    df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray]:
    result = np.zeros(df.shape[0], dtype=object)
    for i, data in enumerate(df.index.to_flat_index()):
        result[i] = Index.build_from_dict(
            {"input": data[0], "output": data[1], "flow type": data[2]}
        )
    return result, df.to_numpy(dtype=float)


def filter_databases_indexed_superstructure(
    df: pd.DataFrame, include: set
) -> pd.DataFrame:
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
    return [str(x).replace("\n", " ").replace("\r", "") for x in cols]


def scenario_replace_databases(df_: pd.DataFrame, replacements: dict) -> pd.DataFrame:
    """For a provided dataframe the function will check for the presence of a unidentified database for all rows.
    If an unidentified database is found as a key in the replacements argument the corresponding value provided is used
    to provide an alternative database. The corresponding key for the activity from the unidentified database is
    collected from the provided alternative.

    If an activity cannot be identified within the provided database a warning message is provided. The process can
    either be terminated, or can proceed without replacement of those activities not identified (the unidentified
    database names in these instances will be retained)

    Raises
    ------
    ScenarioDatabaseNotFoundError

    Parameters
    ----------

    df_ : the dataframe that is produced from the supplied scenario files provided to the AB

    replacements : a dictionary of key-value pairs where the key corresponds to the database in the supplied dataframe
            and the value corresponds to the respective database in the local brightway environment

    bw_dbs : a list of Brightway databases held locally

    Returns
    -------
    """

    def exchange_replace_database(
        ds: pd.Series, replacements: dict, critical: list, idx: pd.Index
    ) -> tuple:
        """
        For a row in the scenario dataframe check the databases involved for whether replacement is required.
        If so use the key-value pair within the replacements dictionary to replace the dictionary names
        and obtain the correct activity key

        Raises
        ------
        No exception however it creates a store of five values that indicate non-linkable flows with the
        new database

        Parameters
        ----------
        ds: dataseries from a pandas dataframe containing the data from the scenario difference file
        replacements: a key -- value pair containing the old -- new database names
        critical: an initially empty list that is filled with dataseries that fail in the relinking process
        idx: the index for the dataseries object, in the "parent" dataframe
        """
        ds_ = ds.copy()
        for i, field in enumerate([FROM_FIELDS, TO_FIELDS]):
            db_name = ds_[["from database", "to database"][i]]
            # check for the relevance of the particular field
            if db_name not in replacements.keys():
                continue
            try:
                # try to find the matching records (after loaded into the metadata)
                if isinstance(ds_[field[1]], float):
                    # try to find a technosphere record
                    key = metadata[
                        (metadata[DB_FIELDS[0]] == ds_[field[0]])
                        & (metadata[DB_FIELDS[2]] == ds_[field[2]])
                        & (metadata[DB_FIELDS[3]] == ds_[field[3]])
                    ].copy()
                else:
                    # try to find a biosphere record
                    if isinstance(ds_[field[1]], str):
                        categories = ast.literal_eval(ds_[field[1]])
                    else:
                        categories = ds_[field[1]]
                    key = metadata[
                        (metadata[DB_FIELDS[0]] == ds_[field[0]])
                        & (metadata[DB_FIELDS[1]] == categories)
                    ].copy()
                # replace the records that can be found
                for j, col in enumerate(
                    [["from key", "from database"], ["to key", "to database"]][i]
                ):
                    ds_.loc[col] = (
                        (key["database"][0], key["code"][0])
                        if j == 0
                        else key["database"][0]
                    )
            except Exception as e:
                # if the record cannot be found add an exception (to a maximum of five)
                if len(critical["from database"]) <= 5:
                    critical["index"].append(idx)
                    critical["from database"].append(ds_["from database"])
                    critical["from activity name"].append(ds_["from activity name"])
                    critical["to database"].append(ds_["to database"])
                    critical["to activity name"].append(ds_["to activity name"])
        return ds_

    # Create a new database from those records in the scenario files that include exchanges where a replacement database
    # is required
    df = df_.loc[
        (df_["from database"].isin(replacements.keys()))
        | (df_["to database"].isin(replacements.keys()))
    ].copy(True)

    # A LIST OF FIELDS FOR ITERATION
    FROM_FIELDS = pd.Index(
        [
            "from activity name",
            "from categories",
            "from reference product",
            "from location",
        ]
    )
    TO_FIELDS = pd.Index(
        ["to activity name", "to categories", "to reference product", "to location"]
    )
    DB_FIELDS = ["name", "categories", "reference product", "location"]

    # setting up the variables in case some exchanges cannot be relinked
    critical = {
        "index": [],
        "from database": [],
        "from activity name": [],
        "to database": [],
        "to activity name": [],
    }  # To be used in the exchange_replace_database internal method scope
    changes = ["from database", "from key", "to database", "to key"]

    # Load all required databases into the metadata
    AB_metadata.add_metadata(replacements.values())
    metadata = AB_metadata.dataframe

    for idx in df.index:
        df.loc[idx, changes] = exchange_replace_database(
            df.loc[idx, :], replacements, critical, idx
        )[changes]
        sys.stdout.write(
            "\r{}".format(idx / df.shape[0])
        )  # TODO check adaptation for the logger
        sys.stdout.flush()

    if critical["from database"]:
        # prepare a warning message in case unlinkable activities were found in the scenario dataframe
        QApplication.restoreOverrideCursor()
        if len(critical["from database"]) > 1:
            msg = (
                f'Multiple activities could not be "relinked" to the local database.<br> The first five are provided. '
                f"If you want to save the dataframe you can either save those scenario exchanges where relinking failed "
                f"(check the excerpt box), or save the entire dataframe with a new column indicating failed relinking."
                f"<br> To abort the process press 'Cancel'"
            )
            critical_message = ABPopup.abCritical(
                "Activities not found",
                msg,
                QPushButton("Save"),
                QPushButton("Cancel"),
                default=2,
            )
            critical_message.save_options()
            critical_message.dataframe(df.loc[critical["index"], :], SUPERSTRUCTURE)
            critical_message.dataframe_to_file(df_, critical["index"])
            response = critical_message.exec_()
        else:
            msg = (
                f'An activity could not be "relinked" to the local database.<br> Some additional information is '
                f"provided. If you want to save the dataframe you can either save those scenario exchanges where "
                f"relinking failed (check the excerpt box), or save the entire dataframe with a new column indicating"
                f" failed relinking.<br>To abort the process press 'Cancel'"
            )
            critical_message = ABPopup.abCritical(
                "Activity not found",
                msg,
                QPushButton("Save"),
                QPushButton("Cancel"),
                default=2,
            )
            critical_message.save_options()
            critical_message.dataframe(df.loc[critical["index"], :], SUPERSTRUCTURE)
            critical_message.dataframe_to_file(df_, critical["index"])
            response = critical_message.exec_()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        raise ScenarioDatabaseNotFoundError(
            "Incompatible Databases in the scenario file, unable to complete further checks on the file"
        )
    else:
        df_.loc[df.index] = df
    return df_
