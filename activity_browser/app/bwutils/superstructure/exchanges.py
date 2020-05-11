# -*- coding: utf-8 -*-
from typing import List

import brightway2 as bw
from bw2data.backends.peewee import Exchange, ExchangeDataset
import pandas as pd
from peewee import BaseQuery

from .utils import EXCHANGE_KEYS


def process_ed_namedtuple(row) -> tuple:
    """Take a given ExchangeDataset namedtuple and return two hashable tuples."""
    in_key = (row.input_database, row.input_code)
    out_key = (row.output_database, row.output_code)
    return in_key, out_key


def select_exchanges_from_database(db_name: str, as_namedtuples: bool = True) -> BaseQuery:
    query = (ExchangeDataset
             .select()
             .where(ExchangeDataset.output_database == db_name))
    if as_namedtuples:
        query = query.namedtuples()
    return query


def select_exchanges_by_database_codes(db_name: str, codes: set) -> BaseQuery:
    inputs = set(x[0] for x in codes)
    outputs = set(x[1] for x in codes)
    query = (ExchangeDataset
             .select()
             .where((ExchangeDataset.output_database == db_name) &
                    (ExchangeDataset.input_code.in_(inputs)) &
                    (ExchangeDataset.output_code.in_(outputs)))
             .namedtuples())
    return query


def construct_exchanges_search(df: pd.DataFrame) -> (pd.Series, set):
    keys = df.loc[:, EXCHANGE_KEYS]
    if keys.isna().all().all():
        return pd.Series([]), set()

    # Separate into component sets.
    in_dbs = set(x[0] for x in keys["from key"])
    in_codes = set(x[1] for x in keys["from key"])
    out_dbs = set(x[0] for x in keys["to key"])
    out_codes = set(x[1] for x in keys["to key"])

    query = (ExchangeDataset
             .select(ExchangeDataset.input_code, ExchangeDataset.input_database,
                     ExchangeDataset.output_code, ExchangeDataset.output_database)
             .where((ExchangeDataset.input_code.in_(in_codes)) &
                    (ExchangeDataset.input_database.in_(in_dbs)) &
                    (ExchangeDataset.output_code.in_(out_codes)) &
                    (ExchangeDataset.output_database.in_(out_dbs)))
             .namedtuples())

    found_exc = set(process_ed_namedtuple(x) for x in query.iterator())
    exchanges = keys.apply(tuple, axis=1)
    return exchanges, found_exc


def all_exchanges_found(df: pd.DataFrame) -> bool:
    """Given a dataframe, determines if all exchanges exist in the database already."""
    exchanges, found_exc = construct_exchanges_search(df)
    if exchanges.empty:
        return False
    return exchanges.isin(found_exc).all()


def filter_existing_exchanges(df: pd.DataFrame) -> pd.Series:
    """Given a dataframe, return a series of input/output keys that do not exist."""
    exchanges, found_exc = construct_exchanges_search(df)
    return exchanges[~exchanges.isin(found_exc)]


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


def nullify_exchanges(data: List[dict]) -> (List[dict], List[float]):
    """Take a list of exchange dictionaries, extract all the amounts
    and set the 'amount' in the dictionaries to 0."""
    amounts = [exc.get("amount", 0) for exc in data]

    def set_null(d):
        d["amount"] = 0
        return d

    nulled = list(map(set_null, data))
    return nulled, amounts


def swap_exchange_activities(data: dict, super_db: str, delta_db: str) -> Exchange:
    """Take the exchange data and replace one or two activities inside with
    new ones containing the same information.

    This works best with activities constructed like those of ecoinvent.
    """
    in_key = data.get("input", ("",))
    out_key = data.get("output", ("",))
    if in_key[0] == delta_db:
        data["input"] = (super_db, in_key[1])
    if out_key[0] == delta_db:
        data["output"] = (super_db, out_key[1])
    # Constructing the Exchange this way will cause a new row to be written
    e = Exchange(**data)
    return e


def create_new_exchange(in_key: tuple, out_key: tuple, data: dict, exc_type: str = "technosphere") -> Exchange:
    # Override default exc_type if inputdb is biosphere
    if in_key[0] == bw.config.biosphere:
        exc_type = "biosphere"
    data["input"] = in_key
    data["output"] = out_key
    data["type"] = exc_type
    e = Exchange(**data)
    return e
