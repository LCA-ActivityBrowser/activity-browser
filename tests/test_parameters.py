# -*- coding: utf-8 -*-
import brightway2 as bw
from bw2data.parameters import (ActivityParameter, DatabaseParameter, Group,
                                ProjectParameter)
from PySide2 import QtCore, QtWidgets
import pytest

from activity_browser.signals import signals
from activity_browser.ui.tables.delegates import FormulaDelegate
from activity_browser.ui.tables.parameters import (
    ActivityParameterTable, DataBaseParameterTable,
    ProjectParameterTable
)
from activity_browser.layouts.tabs.parameters import ParameterDefinitionTab


def test_create_project_param(qtbot):
    """ Create a single Project parameter.

    Does not user the overarching application due to mouseClick failing
    """
    assert bw.projects.current == "pytest_project"
    assert ProjectParameter.select().count() == 0

    project_db_tab = ParameterDefinitionTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_tables()
    table = project_db_tab.project_table.get_table()

    bw.parameters.new_project_parameters([
        {"name": "param_1", "amount": 1.0},
        {"name": "param_2", "amount": 1.0},
        {"name": "param_3", "amount": 1.0},
    ])
    table.model.sync()
    assert table.rowCount() == 3

    # New parameter is named 'param_1'
    assert table.model.index(0, 0).data() == "param_1"
    assert ProjectParameter.select().count() == 3
    assert ProjectParameter.select().where(ProjectParameter.name == "param_1").exists()


def test_edit_project_param(qtbot, monkeypatch):
    """ Edit the existing parameter to have new values.
    """
    table = ProjectParameterTable()
    qtbot.addWidget(table)
    table.model.sync()

    # Edit both the name and the amount of the first parameter.
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("test_project", True))
    )
    table.model.handle_parameter_rename(table.proxy_model.index(0, 0))
    table.model.setData(table.model.index(0, 1), 2.5)

    # Check that parameter is correctly stored in brightway.
    assert ProjectParameter.get(name="test_project").amount == 2.5

    # Now edit the formula directly (without delegate)
    with qtbot.waitSignal(signals.parameters_changed, timeout=1000):
        table.model.setData(table.model.index(0, 2), "2 + 3")
    assert ProjectParameter.get(name="test_project").amount == 5

    # Now edit the formula of the 3rd param to use the 2nd param
    with qtbot.waitSignal(signals.parameters_changed, timeout=1000):
        table.model.setData(table.model.index(2, 2), "param_2 + 3")
    assert ProjectParameter.get(name="param_3").amount == 4


def test_delete_project_param(qtbot):
    """ Try and delete project parameters through the tab.
    """
    table = ProjectParameterTable()
    qtbot.addWidget(table)
    table.model.sync()

    # The 2nd parameter cannot be deleted
    param = table.get_parameter(table.proxy_model.index(1, 0))
    assert not param.is_deletable()

    # Delete the 3rd parameter, removing the dependency
    table.delete_parameter(table.proxy_model.index(2, 0))

    # 2nd parameter can now be deleted, so delete it.
    assert param.is_deletable()
    table.delete_parameter(table.proxy_model.index(1, 0))


def test_create_database_params(qtbot):
    """ Create three database parameters

    Does not user the overarching application due to mouseClick failing
    """
    assert DatabaseParameter.select().count() == 0

    project_db_tab = ParameterDefinitionTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_tables()
    table = project_db_tab.database_table.get_table()

    # Open the database foldout
    assert not project_db_tab.database_table.isHidden()
    with qtbot.waitSignal(project_db_tab.show_database_params.stateChanged, timeout=1000):
        qtbot.mouseClick(project_db_tab.show_database_params, QtCore.Qt.LeftButton)
    assert project_db_tab.database_table.isHidden()
    project_db_tab.show_database_params.toggle()

    # Generate a few database parameters
    bw.parameters.new_database_parameters([
        {"name": "param_2", "amount": 1.0},
        {"name": "param_3", "amount": 1.0},
        {"name": "param_4", "amount": 1.0},
    ], database="biosphere3")
    table.model.sync()

    # First created parameter is named 'param_2'
    assert table.model.index(0, 0).data() == "param_2"
    assert table.rowCount() == 3
    assert DatabaseParameter.select().count() == 3


def test_edit_database_params(qtbot, monkeypatch):
    table = DataBaseParameterTable()
    qtbot.addWidget(table)
    table.model.sync()

    # Fill rows with new variables
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("test_db1", True))
    )
    table.model.handle_parameter_rename(table.proxy_model.index(0, 0))
    table.model.setData(table.model.index(0, 2), "test_project + 3.5")
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("test_db2", True))
    )
    table.model.handle_parameter_rename(table.proxy_model.index(1, 0))
    table.model.setData(table.model.index(1, 2), "test_db1 ** 2")
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("test_db3", True))
    )
    table.model.handle_parameter_rename(table.proxy_model.index(2, 0))
    table.model.setData(table.model.index(2, 1), "8.5")
    table.model.setData(table.model.index(2, 3), "testdb")

    # 5 + 3.5 = 8.5 -> 8.5 ** 2 = 72.25
    assert DatabaseParameter.get(name="test_db2").amount == 72.25
    # There are two parameters for `biosphere3` and one for `testdb`
    assert (DatabaseParameter.select()
            .where(DatabaseParameter.database == "biosphere3").count()) == 2
    assert (DatabaseParameter.select()
            .where(DatabaseParameter.database == "testdb").count()) == 1


def test_delete_database_params(qtbot):
    """ Attempt to delete a parameter.
    """
    project_db_tab = ParameterDefinitionTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_tables()
    table = project_db_tab.database_table.get_table()

    # Check that we can delete the parameter and remove it.
    proxy = table.proxy_model.index(1, 0)
    assert table.get_parameter(proxy).is_deletable()
    table.delete_parameter(proxy)

    # Now we have two rows left
    assert table.rowCount() == 2
    assert DatabaseParameter.select().count() == 2


def test_downstream_dependency(qtbot):
    """ A database parameter uses a project parameter in its formula.

    Means we can't delete it right?
    """
    table = ProjectParameterTable()
    qtbot.addWidget(table)
    table.model.sync()

    # First parameter of the project table is used by the database parameter
    param = table.get_parameter(table.proxy_model.index(0, 0))
    assert not param.is_deletable()


def test_create_activity_param(qtbot):
    """ Create several activity parameters.

    TODO: Figure out some way of performing a drag action between tables.
     Use method calls for now.
     Until the above is implemented, take shortcuts and don't check db validity
    """
    project_db_tab = ParameterDefinitionTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_tables()
    table = project_db_tab.activity_table.get_table()

    # Open the order column just because we can
    col = table.model.order_col
    assert table.isColumnHidden(col)
    with qtbot.waitSignal(project_db_tab.activity_table.parameter.stateChanged, timeout=1000):
        qtbot.mouseClick(project_db_tab.activity_table.parameter, QtCore.Qt.LeftButton)
    assert not table.isColumnHidden(col)

    # Create multiple parameters for a single activity
    act_key = ("testdb", "act1")
    for _ in range(3):
        table.model.add_parameter(act_key)

    # Test created parameters
    assert ActivityParameter.select().count() == 3
    # First of the multiple parameters
    assert table.proxy_model.index(0, 0).data() == "act_1"
    # Second of the multiple parameters
    assert table.proxy_model.index(1, 0).data() == "act_2"
    # The group name for the `testdb` parameters is the same.
    loc = table.visualRect(table.proxy_model.index(0, 0))
    qtbot.mouseClick(table.viewport(), QtCore.Qt.LeftButton, pos=loc.center())
    group = table.get_current_group()
    assert table.proxy_model.index(2, table.model.group_col).data() == group


def test_edit_activity_param(qtbot, monkeypatch):
    """ Alter names, amounts and formulas.

    Introduce dependencies through formulas
    """
    table = ActivityParameterTable()
    qtbot.addWidget(table)
    table.model.sync()

    # Fill rows with new variables
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("edit_act_1", True))
    )
    table.model.handle_parameter_rename(table.proxy_model.index(0, 0))
    table.model.setData(table.model.index(0, 2), "test_db3 * 3")
    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("edit_act_2", True))
    )
    table.model.handle_parameter_rename(table.proxy_model.index(1, 0))
    table.model.setData(table.model.index(1, 2), "edit_act_1 - 3")

    # Test updated values
    assert ActivityParameter.get(name="edit_act_1").amount == 25.5
    assert ActivityParameter.get(name="edit_act_2").amount == 22.5


def test_activity_order_edit(qtbot):
    table = ActivityParameterTable()
    qtbot.addWidget(table)
    table.model.sync()
    group = table.model.index(0, table.model.group_col).data()
    with qtbot.waitSignal(signals.parameters_changed, timeout=1000):
        table.model.setData(table.model.index(0, 5), [group])


@pytest.mark.parametrize(
    "table_class", [
        ProjectParameterTable,
        DataBaseParameterTable,
        ActivityParameterTable,
    ]
)
def test_table_formula_delegates(qtbot, table_class):
    """ Open the formula delegate to test all related methods within the table.
    """
    table = table_class()
    qtbot.addWidget(table)
    table.model.sync()

    assert isinstance(table.itemDelegateForColumn(2), FormulaDelegate)

    delegate = FormulaDelegate(table)
    option = QtWidgets.QStyleOptionViewItem()
    option.rect = QtCore.QRect(0, 0, 100, 100)
    index = table.proxy_model.index(0, 2)
    # Note: ActivityParameterTable depends on the user having clicked
    # the table to correctly extract the group for the activity
    rect = table.visualRect(index)
    qtbot.mouseClick(table.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
    editor = delegate.createEditor(table, option, index)
    qtbot.addWidget(editor)
    delegate.setEditorData(editor, index)
    delegate.setModelData(editor, table.proxy_model, index)


def test_open_activity_tab(qtbot, ab_app):
    """ Trigger an 'open tab and switch to' action for a parameter.
    """
    # First, look at the parameters tab
    panel = ab_app.main_window.right_panel
    param_tab = panel.tabs["Parameters"]
    activities_tab = panel.tabs["Activity Details"]
    ab_app.main_window.right_panel.select_tab(param_tab)

    # Select an activity
    tab = param_tab.tabs["Definitions"]
    table = tab.activity_table.get_table()
    rect = table.visualRect(table.proxy_model.index(0, 3))
    qtbot.mouseClick(table.viewport(), QtCore.Qt.LeftButton, pos=rect.center())

    # Trigger the tab to open
    table.open_activity_tab()

    # We should now be looking at the activity tab
    assert panel.currentIndex() != panel.indexOf(param_tab)
    assert panel.currentIndex() == panel.indexOf(activities_tab)

    # And close the tab again.
    activities_tab.close_all()


def test_delete_activity_param(qtbot):
    """ Remove activity parameters.
    """
    project_db_tab = ParameterDefinitionTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_tables()
    table = project_db_tab.activity_table.get_table()

    rect = table.visualRect(table.proxy_model.index(0, 0))
    qtbot.mouseClick(table.viewport(), QtCore.Qt.LeftButton, pos=rect.center())

    group = table.get_current_group()

    # Now delete the parameter for the selected row.
    table.delete_parameter(table.currentIndex())
    assert table.rowCount() == 2
    assert ActivityParameter.select().count() == 2
    assert Group.select().where(Group.name == group).exists()

    # And delete the other two parameters one by one.
    table.delete_parameter(table.proxy_model.index(0, 0))
    table.delete_parameter(table.proxy_model.index(0, 0))
    assert table.rowCount() == 0
    assert ActivityParameter.select().count() == 0
    # Group is automatically removed with the last parameter gone
    assert not Group.select().where(Group.name == group).exists()
