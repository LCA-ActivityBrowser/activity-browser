"""ABTreeModel.row must avoid DataFrame.iloc[i] (pandas 3 fast_xs abort)."""
from datetime import datetime

import pandas as pd
from PySide6.QtCore import Qt

from activity_browser.app.panes.databases import DatabasesModel
from activity_browser.ui.core.tree_model import ABTreeModel


def _mixed_db_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "read_only": [True],
            "name": pd.Series(["basic"], dtype="string"),
            "records": [3],
            "depends": pd.Series([""], dtype="string"),
            "default_allocation": pd.Series(["unspecified"], dtype="string"),
            "modified": [datetime(2026, 1, 1)],
            "backend": pd.Series(["sqlite"], dtype="string"),
        }
    )


def test_row_safe_on_mixed_string_datetime_frame(qapp):
    df = _mixed_db_df()
    model = ABTreeModel(df)
    # StringDtype is coerced to object on ingest to avoid pandas 3 fast_xs aborts.
    assert model.df["name"].dtype == object
    assert model.df.columns.dtype == object

    index = model.index(0, 0)
    row = model.row(index)
    assert row is not None
    assert row.get("name") == "basic"
    assert bool(row.get("read_only")) is True
    assert model.get(index, "records") == 3
    # Paint path: membership must not use StringDtype Index.__contains__.
    assert "index" not in model.df.columns.tolist()
    assert "name" in model.df.columns.tolist()

    # Replacing the frame (DatabasesModel.sync) must stay safe under pandas 3.
    model.set_dataframe(df)
    assert model.df["name"].dtype == object
    assert model.df.columns.dtype == object
    assert model.get(model.index(0, 0), "name") == "basic"


def test_databases_model_display_data_after_set_dataframe(qapp):
    """CI abort: displayData used ``in df.columns`` during sync/resize paint."""
    model = DatabasesModel()
    model.set_dataframe(_mixed_db_df())
    assert model.df.columns.dtype == object

    # Column 0 is the synthetic tree "index" label (not a DataFrame column).
    assert model.displayData(model.index(0, 0)) is None
    # Name column (section 2 after tree + read_only decoration column layout)
    name_col = model.columns().index("name")
    name_index = model.index(0, name_col)
    assert model.data(name_index, Qt.ItemDataRole.DisplayRole) == "basic"
