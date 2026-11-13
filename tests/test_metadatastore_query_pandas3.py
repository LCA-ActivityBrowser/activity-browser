"""Regression: MetaDataStore / ABTreeView query strings must work with pandas 3.

``DataFrame.query()`` does not resolve the builtin ``str``, so expressions like
``"`name`.fillna('').astype(str) == 'steel'"`` raise
``UndefinedVariableError: name 'str' is not defined``. That broke
``MetaDataStore.match`` (Excel / bw2package ``metadatastore_link``) and table
filters in ``ABTreeView``. ``astype('str')`` works on pandas 2.3 and 3.

See ADR-0014 for MDS dtypes; fixtures go through ``apply_metadata_dtypes``.
"""
import re

import numpy as np
import pandas as pd
import pytest
from pandas.api.types import is_string_dtype

from activity_browser.bwutils.metadata.fields import all_fields
from activity_browser.bwutils.metadata.metadata import MetaDataStore
from activity_browser.ui.core.tree_model import ABTreeModel
from activity_browser.ui.widgets.tree_view import ABTreeView


def _raw_frame() -> pd.DataFrame:
    idx = pd.MultiIndex.from_tuples(
        [("db", "a"), ("db", "b"), ("bio", "c")], names=["database", "code"]
    )
    return pd.DataFrame(
        {
            "key": [("db", "a"), ("db", "b"), ("bio", "c")],
            "id": [1, 2, 3],
            "code": ["a", "b", "c"],
            "database": ["db", "db", "bio"],
            "location": ["GLO", "DE", None],
            "name": ["steel", "glass", "Carbon dioxide, fossil"],
            "product": ["steel", "glass", None],
            "type": ["process", "process", "emission"],
            "synonyms": [None, None, None],
            "unit": ["kilogram", None, "kilogram"],
            "CAS number": [np.nan, np.nan, np.nan],
            "categories": [None, None, ("air", "urban air close to ground")],
            "processor": [None, None, None],
            "allocation": [None, None, None],
            "allocation_factor": [np.nan, np.nan, np.nan],
            "properties": [None, None, None],
        },
        index=idx,
    )


@pytest.fixture
def mds_with_frame():
    """Typed MDS frame via the public setter (ADR-0014), then restore prior state."""
    mds = MetaDataStore()
    old = mds._dataframe
    mds.dataframe = _raw_frame()
    assert list(mds.dataframe.columns) == all_fields
    assert is_string_dtype(mds.dataframe["name"].dtype)
    assert mds.dataframe["categories"].dtype == object
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
    df = mds_with_frame._pandas_search("name:GLA", columns=["name"])
    assert list(df.index) == [("db", "b")]


def test_meta_from_result_parameter_filter(mds_with_frame):
    # Keep default columns: _meta_from_result sorts by ``id`` after slicing.
    df = mds_with_frame._meta_from_result({"name": "GLA"}, result=[1, 2])
    assert list(df.index) == [("db", "b")]


def _assert_query_uses_string_literal_astype(query: str) -> None:
    assert "astype('str')" in query
    assert re.search(r"astype\(str\)", query) is None


def test_tree_view_column_filter_query_under_pandas_3(qtbot):
    """Product-table style filter: buildQuery + applyFilter on a real model."""
    df = pd.DataFrame(
        {
            "name": ["steel", "glass"],
            "location": ["GLO", "DE"],
            "key": [("db", "a"), ("db", "b")],
        }
    )
    model = ABTreeModel(df)
    view = ABTreeView()
    qtbot.addWidget(view)
    view.setModel(model)

    applied: list[bool] = []
    view.filtered.connect(applied.append)

    view.columnFilters["location"] = "DE"
    query = view.buildQuery()
    _assert_query_uses_string_literal_astype(query)

    view.applyFilter()
    assert applied == [True]
    # Hierarchy is rebuilt from the filtered index; self.df keeps all rows.
    assert model.rowCount() == 1
