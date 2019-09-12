# -*- coding: utf-8 -*-
import brightway2 as bw
from bw2data.parameters import DatabaseParameter, ProjectParameter
from PyQt5 import QtCore

from activity_browser.app.signals import signals
from activity_browser.app.ui.tabs.parameters import ParameterDefinitionTab


def test_create_project_param(qtbot):
    """ Create a single Project parameter.

    Does not user the overarching application due to mouseClick failing
    """
    assert bw.projects.current == "pytest_project"
    assert ProjectParameter.select().count() == 0

    project_db_tab = ParameterDefinitionTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_tables()
    proj_table = project_db_tab.project_table

    with qtbot.waitSignal(proj_table.new_parameter, timeout=1000):
        qtbot.mouseClick(project_db_tab.new_project_param, QtCore.Qt.LeftButton)
    assert proj_table.rowCount() == 1

    # Fill new row with variables
    proj_table.model.setData(proj_table.model.index(0, 0), "test_project")
    proj_table.model.setData(proj_table.model.index(0, 1), 2.5)

    # Store variables
    with qtbot.waitSignal(signals.parameters_changed, timeout=1000):
        qtbot.mouseClick(project_db_tab.save_project_btn, QtCore.Qt.LeftButton)

    # Check that parameter is correctly stored in brightway.
    assert ProjectParameter.select().count() == 1
    assert ProjectParameter.get(name="test_project").amount == 2.5


def test_create_database_params(qtbot):
    """ Create two database parameters, one dependent on the above
    project parameter and one dependent on the first database parameter.

    Depends on the test above

    Does not user the overarching application due to mouseClick failing
    """
    assert bw.projects.current == "pytest_project"
    assert DatabaseParameter.select().count() == 0

    project_db_tab = ParameterDefinitionTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_tables()
    db_table = project_db_tab.database_table

    with qtbot.waitSignals([db_table.new_parameter, db_table.new_parameter], timeout=1000):
        qtbot.mouseClick(project_db_tab.new_database_param, QtCore.Qt.LeftButton)
        qtbot.mouseClick(project_db_tab.new_database_param, QtCore.Qt.LeftButton)
    assert db_table.rowCount() == 2

    # Fill new rows with variables
    db_table.model.setData(db_table.model.index(0, 0), "test_db1")
    db_table.model.setData(db_table.model.index(0, 2), "test_project + 3.5")
    db_table.model.setData(db_table.model.index(0, 3), "biosphere3")
    db_table.model.setData(db_table.model.index(1, 0), "test_db2")
    db_table.model.setData(db_table.model.index(1, 2), "test_db1 ** 2")
    db_table.model.setData(db_table.model.index(1, 3), "biosphere3")

    with qtbot.waitSignal(signals.parameters_changed, timeout=1000):
        qtbot.mouseClick(project_db_tab.save_database_btn, QtCore.Qt.LeftButton)

    assert DatabaseParameter.select().count() == 2
    # 2.5 + 3.5 = 6 -> 6 ** 2 = 36
    assert DatabaseParameter.get(name="test_db2").amount == 36
