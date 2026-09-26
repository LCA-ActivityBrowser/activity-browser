"""Parameter models report a successful amount or formula edit as a success.

Qt's QAbstractItemModel::setData contract: return True when the data was set. Both
parameter models wrote amount, formula, name and comment edits and then fell through
to `return False`; only the uncertainty branch returned True.
"""

import bw2data as bd
import pytest
from qtpy.QtCore import QModelIndex, Qt

# Initialize ABApplication before pytest-qt creates a QApplication.
from activity_browser import app  # noqa: F401
from activity_browser.app.pages.activity_details.parameters_tab import ParametersTab
from activity_browser.app.pages.parameters.parameters_section import ParametersSection


def _index_by_name(model, name, parent=None):
    parent = QModelIndex() if parent is None else parent
    for row in range(model.rowCount(parent)):
        index = model.index(row, 0, parent)
        instantiated = model.get(index, "_class") == "instantiated"
        if instantiated and model.get(index, "name") == name:
            return index
        found = _index_by_name(model, name, index)
        if found is not None:
            return found
    return None


@pytest.mark.parametrize("view", ["parameters-page", "activity-tab"])
@pytest.mark.parametrize(
    "column, value, expected_amount",
    [("amount", 42.0, 42.0), ("formula", "6 * 7", 42.0)],
)
def test_parameter_set_data_returns_true(
    basic_project, qtbot, view, column, value, expected_amount
):
    bd.parameters.new_project_parameters([{"name": "first", "amount": 1}])
    section = (
        ParametersSection()
        if view == "parameters-page"
        else ParametersTab(("basic", "process"))
    )
    qtbot.addWidget(section)
    section.sync()
    model = section.model

    index = _index_by_name(model, "first")
    index = index.siblingAtColumn(model.columns().index(column))
    assert model.setData(index, value, Qt.ItemDataRole.EditRole) is True

    section.sync()
    assert model.get(_index_by_name(model, "first"), "amount") == expected_amount
