"""Scenario names must stay strings; product combine joins with ' | '."""
import pandas as pd

from activity_browser.bwutils.superstructure.dataframe import (
    ensure_string_scenario_names,
)
from activity_browser.bwutils.superstructure.manager import SuperstructureManager
from activity_browser.bwutils.superstructure.utils import SUPERSTRUCTURE


def _minimal_sdf(from_code: str, to_code: str, scenario_amounts: dict) -> pd.DataFrame:
    row = {col: None for col in SUPERSTRUCTURE}
    row.update(
        {
            "from key": ("db", from_code),
            "to key": ("db", to_code),
            "flow type": "technosphere",
            "from database": "db",
            "to database": "db",
        }
    )
    row.update(scenario_amounts)
    return pd.DataFrame([row])


def test_ensure_string_scenario_names_from_numeric_headers():
    df = _minimal_sdf("a", "b", {2025: 1.0, 2026: 2.0})
    coerced = ensure_string_scenario_names(df)
    assert list(coerced.columns.difference(SUPERSTRUCTURE, sort=False)) == [
        "2025",
        "2026",
    ]


def test_product_combine_with_numeric_scenario_names():
    df1 = _minimal_sdf("a", "b", {"A": 10.0, "B": 20.0})
    df2 = _minimal_sdf("c", "d", {2025: 3.0, 2026: 4.0})

    combined = SuperstructureManager(df1, df2).combined_data(
        kind="product", skip_checks=True
    )

    assert list(combined.columns) == [
        "A | 2025",
        "A | 2026",
        "B | 2025",
        "B | 2026",
    ]

    row1 = (("db", "a"), ("db", "b"), "technosphere")
    row2 = (("db", "c"), ("db", "d"), "technosphere")

    assert combined.at[row1, "A | 2025"] == 10.0
    assert combined.at[row1, "A | 2026"] == 10.0
    assert combined.at[row1, "B | 2025"] == 20.0
    assert combined.at[row1, "B | 2026"] == 20.0

    assert combined.at[row2, "A | 2025"] == 3.0
    assert combined.at[row2, "A | 2026"] == 4.0
    assert combined.at[row2, "B | 2025"] == 3.0
    assert combined.at[row2, "B | 2026"] == 4.0
