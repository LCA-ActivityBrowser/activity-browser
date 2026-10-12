"""Metadata store column types: pandas strings vs Python objects (ADR-0014)."""
import numpy as np
import pandas as pd
from pandas.api.types import is_string_dtype

from activity_browser.bwutils.metadata.metadata import (
    apply_metadata_dtypes,
    dataframe_for_pickle_cache,
)


def _raw_frame() -> pd.DataFrame:
    idx = pd.MultiIndex.from_tuples([("db", "a")], names=["database", "code"])
    return pd.DataFrame(
        {
            "key": [("db", "a")],
            "id": [1],
            "code": ["a"],
            "database": ["db"],
            "location": ["GLO"],
            "name": ["steel"],
            "product": ["steel"],
            "type": ["process"],
            "synonyms": [["metal"]],
            "unit": ["kilogram"],
            "CAS number": [np.nan],
            "categories": [None],
            "processor": [None],
            "allocation": [None],
            "allocation_factor": [np.nan],
            "properties": [{"mass": 1.0}],
        },
        index=idx,
    )


def test_apply_metadata_dtypes_uses_pandas_str_for_scalar_text():
    typed = apply_metadata_dtypes(_raw_frame())
    assert is_string_dtype(typed["name"].dtype)
    assert is_string_dtype(typed["code"].dtype)
    assert typed.loc[("db", "a"), "name"] == "steel"


def test_apply_metadata_dtypes_keeps_python_objects_for_identity_fields():
    typed = apply_metadata_dtypes(_raw_frame())
    row = typed.loc[("db", "a")]
    assert row["key"] == ("db", "a")
    assert row["synonyms"] == ["metal"]
    assert row["properties"] == {"mass": 1.0}


def test_pickle_cache_downcasts_string_dtype():
    typed = apply_metadata_dtypes(_raw_frame())
    cached = dataframe_for_pickle_cache(typed)
    assert not isinstance(cached["name"].dtype, pd.StringDtype)
    assert cached.loc[("db", "a"), "name"] == "steel"
