"""Parameter amount cells stay editable unless a formula or a database lock owns them.

Regression test for issue #1735. The amount guard used a plain falsiness check on the
formula cell, but the formula column is object dtype only when at least one parameter
carries a formula string. With none, pandas infers float64 from the all-missing column,
every formula reads back as NaN, `not NaN` is False, and every amount cell went
read-only. That is also why the symptom looked intermittent: a formula anywhere in the
table changes the inferred dtype and restores editability for every row without a
formula.

Deliberately out of scope: the "New parameter..." placeholder row, the
ParameterizedExchangesSection, and the exchanges tab.
"""

import bw2data as bd
import pytest
from qtpy.QtCore import QModelIndex, Qt

# Initialize ABApplication before pytest-qt creates a QApplication.
from activity_browser import app  # noqa: F401
from activity_browser.app.pages.activity_details.parameters_tab import ParametersTab
from activity_browser.app.pages.parameters.parameters_section import ParametersSection
from activity_browser.ui import icons


def _parameter_indexes(model, parent=None):
    parent = QModelIndex() if parent is None else parent
    for row in range(model.rowCount(parent)):
        index = model.index(row, 0, parent)
        if model.get(index, "_class") == "instantiated":
            yield index
        yield from _parameter_indexes(model, index)


def _index_by_name(model, name):
    for index in _parameter_indexes(model):
        if model.get(index, "name") == name:
            return index
    raise AssertionError(f"parameter {name!r} is not in the model")


@pytest.mark.parametrize("view", ["parameters-page", "activity-tab"])
@pytest.mark.parametrize("scope", ["project", "database", "activity"])
@pytest.mark.parametrize(
    "parameters, expected_editable",
    [
        # No formula anywhere: the all-missing formula column is what #1735 tripped on.
        ([{"name": "first", "amount": 1}], {"first": True}),
        # A formula string keeps the column object dtype. Guard: "" is not a formula.
        (
            [
                {"name": "first", "amount": 1},
                {"name": "blank", "amount": 2, "formula": ""},
                {"name": "derived", "amount": 3, "formula": "first * 2"},
            ],
            {"first": True, "blank": True, "derived": False},
        ),
    ],
    ids=["constants-only", "with-formulas"],
)
def test_parameter_amount_editability(
    basic_project, qtbot, view, scope, parameters, expected_editable
):
    parameters = [dict(parameter) for parameter in parameters]
    bd.databases["basic"]["read_only"] = False
    bd.databases.flush()
    if scope == "project":
        bd.parameters.new_project_parameters(parameters)
    elif scope == "database":
        bd.parameters.new_database_parameters(parameters, "basic")
    else:
        bd.parameters.new_activity_parameters(
            [
                dict(parameter, database="basic", code="process")
                for parameter in parameters
            ],
            "test_group",
        )

    section = (
        ParametersSection()
        if view == "parameters-page"
        else ParametersTab(("basic", "process"))
    )
    qtbot.addWidget(section)
    section.sync()
    model = section.model
    amount_column = model.columns().index("amount")
    actual = {}
    for index in _parameter_indexes(model):
        name = model.get(index, "name")
        if name in expected_editable:
            amount_index = index.siblingAtColumn(amount_column)
            editable = bool(model.flags(amount_index) & Qt.ItemFlag.ItemIsEditable)
            actual[name] = editable
            # The parameterized marker and the editable flag must agree.
            marked = model.decorationData(amount_index) is icons.qicons.parameterized
            assert marked == (not editable), name
    assert actual == expected_editable

    # What the issue reported losing: an amount typed into a constant parameter sticks.
    # ParameterModify writes it and then calls parameters.recalculate(), which may only
    # overwrite amounts a formula owns.
    first = _index_by_name(model, "first")
    model.setData(first.siblingAtColumn(amount_column), 42.0, Qt.ItemDataRole.EditRole)
    section.sync()
    assert model.get(_index_by_name(model, "first"), "amount") == 42.0

    # A formula keeps owning its amount: the cell stays read-only and recomputes.
    if "derived" in expected_editable:
        derived = _index_by_name(model, "derived")
        assert model.get(derived, "formula") == "first * 2"
        assert model.get(derived, "amount") == 84.0
        amount_index = derived.siblingAtColumn(amount_column)
        assert not model.flags(amount_index) & Qt.ItemFlag.ItemIsEditable

    if scope != "project":
        bd.databases["basic"]["read_only"] = True
        bd.databases.flush()
        for index in _parameter_indexes(model):
            if model.get(index, "name") in expected_editable:
                amount_index = index.siblingAtColumn(amount_column)
                assert not model.flags(amount_index) & Qt.ItemFlag.ItemIsEditable
