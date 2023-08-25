from PySide2.QtWidgets import QPushButton
from bw2data.backends.peewee import ExchangeDataset
import pandas as pd
import numpy as np
from .utils import _time_it_, SUPERSTRUCTURE
from ..errors import ScenarioExchangeDataNotFoundError
from .file_dialogs import ABPopup

"""
Interface for the brightway Exchange database.

Responsibilities
----------------
Access and data retrieval from the Brightway exchange database.
Does NOT MANIPULATE, or ALTER data held by the Brightway exchange databases.

"""


np.warnings.filterwarnings('error', category=np.VisibleDeprecationWarning)

def edit_superstructure_for_string():
    text_list = ""
    for field in SUPERSTRUCTURE:
        text_list+= f"{field} <br>"
    return text_list

def get_exchange_value(to_key: tuple, from_key: tuple, type: str):
    """ Gets a single exchange based on the values of the input and output keys and the exchange type"""
    return ExchangeDataset.get(
        ExchangeDataset.input_database == to_key[0][0],
        ExchangeDataset.input_code == to_key[0][1],
        ExchangeDataset.output_database == from_key[0][0],
        ExchangeDataset.output_code == from_key[0][1],
        ExchangeDataset.type == type[0]
    ).data['amount']

def get_exchange_values(to_database: str, from_database: str):
    """
    Access the Brightway Exchanges database to obtain the full list of Exchanges available for the
    provided args.

    Parameters
    ----------
    Arguments provided must be valid Brightway databases for the current project and environment.

    Returns
    -------
    A python dictionary object containing the mappings (the Activity keys - to and from - and type)
    and the 'amount' field as the value
    """
    qry = (ExchangeDataset.select(
        ExchangeDataset.data
    ).where(
        (ExchangeDataset.input_database == to_database) |
        (ExchangeDataset.output_database == from_database)
    ).namedtuples())
    exchanges = {}
    for row in qry:
        exchanges.update({(row[0]['input'], row[0]['output'], row[0]['type']): row[0]['amount']})
    return exchanges

@_time_it_
def set_default_exchange_values_deprecated(df: pd.DataFrame, cols: pd.Index):
    """
    Currently deprecated.
    Replaces the exchanges (identifiable by the cols argument) that evaluate to numpy's nan, with the
    values held by the respective brightway database.

    Parameters
    ----------
    df: a pandas dataframe holding the current files scenario data, should be a full scenario file, with
    all the fields defined in the utils.SUPERSTRUCTURE global
    cols: a pandas index that indicates the scenario columns holding the 'amounts' to be used in the
    scenario calculations

    Returns
    -------
    A pandas dataframe that has either 'default' values or user specified values in all of the scenario
    input amounts
    """
    assert len(cols) > 0
    # for each exchange with a scenario that doesn't have a set value
    _nas = df.loc[:, cols].isna()
    df.sort_index(level=df.index.names, inplace=True)
    for idx in df.loc[_nas.any(axis=1), :].index:
        idx_nas = _nas.loc[idx, :]
        __nas = idx_nas.values if isinstance(idx_nas, pd.Series) else idx_nas.iloc[0, :]
        for i, na in enumerate(__nas):
            if na:
                try:
                    df.loc[idx, idx_nas.columns[i]] = get_exchange_value(df.loc[idx, 'to key'], df.loc[idx, 'from key'], df.loc[idx, 'flow type'])
                except:
                    df.loc[idx, idx_nas.columns[i]] = get_exchange_value(df.loc[idx, 'from key'], df.loc[idx, 'to key'], df.loc[idx, 'flow type'])
    return df

@_time_it_
def set_default_exchange_values(df: pd.DataFrame, cols: pd.Index):
    """
    Replaces the exchanges (identifiable by the cols argument) that evaluate to numpy's nan, with the
    values held by the respective brightway database.

    Raises
    ------
    A ScenarioExchangeDataNotFoundError if no valid values are found in the scenario 'amounts'
        Includes the raising of an ActivityBrowser critical pop up message
    A logged warning before replacement of invalid scenario values

    Parameters
    ----------
    df: a pandas dataframe holding the current files scenario data, should be a full scenario file, with
    all the fields defined in the utils.SUPERSTRUCTURE global
    cols: a pandas index that indicates the scenario columns holding the 'amounts' to be used in the
    scenario calculations

    Returns
    -------
    A pandas dataframe that has either 'default' values or user specified values in all of the scenario
    input amounts
    """
    assert len(cols) > 0
    _nas = df.loc[:, cols].isna()
    df.sort_index(level=df.index.names, inplace=True)
    if not _nas.any(axis=0).any(): # if all values are set
        return df
    elif _nas.all(axis=0).all() and _nas.shape[0] == df.shape[0]: # if there is no provided values
        msg = "<p>No exchange values could be observed in the last loaded scenario file. " + \
        "Exchange values must be recorded in a labelled scenario column with a name distinguishable from the" + \
        " default (required) columns, which are:</p>" + \
        edit_superstructure_for_string() + \
        "<p>Please check the file contents for the scenario columns and the exchange amounts before loading again.</p>"
        critical = ABPopup.abCritical(
            "No scenario exchange data", msg, QPushButton('Cancel')
        )
        critical.exec_()
        raise ScenarioExchangeDataNotFoundError
    print("Warning: Replacing empty values from the last loaded scenario difference file")
    dbs = set(df.loc[:, 'from database']).union((df.loc[:, 'from database']))
    try:
        dbs.remove('biosphere3')
    except KeyError as e:
        print('Warning: No usage of the biosphere database in the scenario file')
    exchanges_values = dict()
    for db in dbs:
        exchanges_values.update(get_exchange_values(db, db))
    for idx in df.loc[_nas.any(axis=1), :].index:
        idx_nas = _nas.loc[idx, :]
        row = df.loc[idx,:]
        __nas = idx_nas.values if isinstance(idx_nas, pd.Series) else idx_nas.iloc[0, :]
        __row = row if isinstance(row, pd.Series) else row.iloc[0,:]
        for i, na in enumerate(__nas):
            if na:
                try:
                    df.loc[idx, idx_nas.columns[i]] = exchanges_values[(__row['to key'], __row['from key'],
                                                                     __row['flow type'])]
                except KeyError as e: # construction of the local dictionary can result in reversal of the
                    # input and output
                    df.loc[idx, idx_nas.columns[i]] = exchanges_values[(__row['from key'], __row['to key'],
                                                                        __row['flow type'])]
    return df
