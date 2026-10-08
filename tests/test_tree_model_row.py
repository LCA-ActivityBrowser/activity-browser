"""Tree-model / DatabasesPane access patterns safe under pandas 2 and 3."""
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeView

from activity_browser.app.panes.databases import DatabasesModel, DatabasesPane
from activity_browser.ui.core.tree_model import ABTreeModel


def test_row_uses_take_not_fast_xs(qapp):
    """Full-row access must use iloc[[i]] (take), not iloc[i] (fast_xs)."""
    df = pd.DataFrame(
        {
            "read_only": [True],
            "name": ["basic"],
            "records": [3],
            "depends": [""],
            "default_allocation": ["unspecified"],
            "modified": ["2026-01-01T00:00:00.000000"],
            "backend": ["sqlite"],
        }
    )
    for col in df.columns:
        df[col] = pd.Series(df[col].tolist(), dtype=object)

    model = ABTreeModel(df)
    row = model.row(model.index(0, 0))
    assert row is not None
    assert row.get("name") == "basic"
    assert model.get(model.index(0, 0), "records") == 3


def test_databases_build_df_is_object_block(qapp, monkeypatch):
    """Databases pane frame must be a uniform object block (CI Linux/3.11)."""
    pane = DatabasesPane.__new__(DatabasesPane)
    monkeypatch.setattr(
        "activity_browser.app.panes.databases.bd.databases",
        {
            "basic": {
                "modified": "2026-01-01T00:00:00.000000",
                "depends": [],
                "read_only": True,
                "default_allocation": "unspecified",
                "backend": "sqlite",
            }
        },
    )
    monkeypatch.setattr(
        "activity_browser.app.panes.databases.count_database_records",
        lambda _name: 3,
    )
    df = DatabasesPane.build_df(pane)
    assert all(df[c].dtype == object for c in df.columns)

    # Refresh the model the view is already showing. Same object, new frame.
    model = DatabasesModel()
    view = QTreeView()
    view.setModel(model)
    model.set_dataframe(df)
    assert view.model() is model
    name_col = model.columns().index("name")
    assert model.data(model.index(0, name_col), Qt.ItemDataRole.DisplayRole) == "basic"
    assert model.displayData(model.index(0, 0)) is None

    refreshed = df.copy()
    refreshed.loc[refreshed.index[0], "name"] = "renamed"
    model.set_dataframe(refreshed)
    assert view.model() is model
    assert model.get(model.index(0, 0), "name") == "renamed"
