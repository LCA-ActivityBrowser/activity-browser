"""Regression: the query strings built by MetaDataStore must work with pandas 3.

pandas 3 no longer resolves the builtin ``str`` inside ``DataFrame.query()``, so
``"`name`.fillna('').astype(str) == 'steel'"`` raised
``UndefinedVariableError: name 'str' is not defined``. ``MetaDataStore.match`` uses
such a query for every exchange in the Excel / bw2package import linking
(``metadatastore_link``), so with pandas 3 nothing linked and ``write_database``
failed with ``InvalidExchange``. ``astype('str')`` (a string literal) works with
pandas 2 and 3 and gives the same result.
"""
import pandas as pd
import pytest

from activity_browser.bwutils.metadata.metadata import MetaDataStore


def _frame() -> pd.DataFrame:
    idx = pd.MultiIndex.from_tuples(
        [("db", "a"), ("db", "b"), ("bio", "c")], names=["database", "code"]
    )
    return pd.DataFrame(
        {
            "database": ["db", "db", "bio"],
            "name": ["steel", "glass", "Carbon dioxide, fossil"],
            "unit": ["kilogram", None, "kilogram"],
            "categories": [None, None, ("air", "urban air close to ground")],
        },
        index=idx,
    )


@pytest.fixture
def mds_with_frame():
    mds = MetaDataStore()
    old = mds._dataframe
    mds._dataframe = _frame()
    yield mds
    mds._dataframe = old


def test_match_on_text_fields(mds_with_frame):
    match = mds_with_frame.match(database="db", name="steel", unit="kilogram")
    assert list(match.index) == [("db", "a")]


def test_match_on_tuple_categories(mds_with_frame):
    match = mds_with_frame.match(
        name="Carbon dioxide, fossil", categories=("air", "urban air close to ground")
    )
    assert list(match.index) == [("bio", "c")]


def test_match_on_missing_value(mds_with_frame):
    match = mds_with_frame.match(database="db", unit=None)
    assert list(match.index) == [("db", "b")]


def test_search_parameter_filter(mds_with_frame):
    # key:value filters of the search use the same kind of query
    df = mds_with_frame._pandas_search("name:GLA", columns=["name"])
    assert list(df.index) == [("db", "b")]
