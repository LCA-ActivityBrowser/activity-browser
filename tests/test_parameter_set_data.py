"""Parameter models report a successful amount or formula edit as a success.

Qt's QAbstractItemModel::setData contract: return True when the data was set. Both
parameter models wrote amount, formula, name and comment edits and then fell through
to `return False`; only the uncertainty branch returned True.

When a name create or rename is refused (invalid name), setData must return False so
Qt does not treat the edit as committed.
"""

import bw2data as bd
import pytest
from bw2data.parameters import ProjectParameter
from qtpy import QtWidgets
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


def _new_row_index(model, parent=None):
    parent = QModelIndex() if parent is None else parent
    for row in range(model.rowCount(parent)):
        index = model.index(row, 0, parent)
        if (
            model.get(index, "_class") == "new"
            and model.get(index, "_param_type") == "project"
        ):
            return index
        found = _new_row_index(model, index)
        if found is not None:
            return found
    return None


@pytest.fixture
def dialogs(monkeypatch):
    shown = {"warning": [], "critical": []}
    for kind in shown:
        monkeypatch.setattr(
            QtWidgets.QMessageBox,
            kind,
            staticmethod(lambda *args, _kind=kind, **kwargs: shown[_kind].append(args)),
        )
    return shown


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


@pytest.mark.parametrize("view", ["parameters-page", "activity-tab"])
def test_parameter_set_data_returns_false_for_invalid_rename(
    basic_project, qtbot, dialogs, view
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
    name_index = index.siblingAtColumn(model.columns().index("name"))
    assert model.setData(name_index, "e", Qt.ItemDataRole.EditRole) is False

    section.sync()
    assert model.get(_index_by_name(model, "first"), "name") == "first"
    assert len(dialogs["warning"]) == 1


@pytest.mark.parametrize("view", ["parameters-page", "activity-tab"])
def test_parameter_set_data_returns_false_for_invalid_new_name(
    basic_project, qtbot, dialogs, view
):
    section = (
        ParametersSection()
        if view == "parameters-page"
        else ParametersTab(("basic", "process"))
    )
    qtbot.addWidget(section)
    section.sync()
    model = section.model

    new_index = _new_row_index(model)
    name_index = new_index.siblingAtColumn(model.columns().index("name"))
    assert model.setData(name_index, "max", Qt.ItemDataRole.EditRole) is False
    assert [p.name for p in ProjectParameter.select()] == []
    assert len(dialogs["warning"]) == 1
