"""ABTreeModel.row must avoid DataFrame.iloc[i] (pandas 3 fast_xs abort)."""
from datetime import datetime

import pandas as pd

from activity_browser.ui.core.tree_model import ABTreeModel


def test_row_safe_on_mixed_string_datetime_frame(qapp):
    df = pd.DataFrame(
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
    model = ABTreeModel(df)
    # Stored dtypes are unchanged (no ingest-time rewrite).
    assert isinstance(model.df["name"].dtype, pd.StringDtype)

    index = model.index(0, 0)
    row = model.row(index)
    assert row is not None
    assert row.get("name") == "basic"
    assert bool(row.get("read_only")) is True
    assert model.get(index, "records") == 3
