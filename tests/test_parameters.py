# -*- coding: utf-8 -*-
import brightway2 as bw
from bw2data.parameters import DatabaseParameter, ProjectParameter
import pandas as pd
from PyQt5 import QtCore

from activity_browser.app.signals import signals
from activity_browser.app.ui.tabs.parameters import ProjectDatabaseTab


def test_create_project_param(qtbot):
    """ Create a single Project parameter.

    Does not user the overarching application due to mouseClick failing
    """
    assert bw.projects.current == "pytest_project"
    assert ProjectParameter.select().count() == 0

    project_db_tab = ProjectDatabaseTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_dataframes()
    proj_table = project_db_tab.project_table

    with qtbot.waitSignal(proj_table.new_parameter, timeout=1000):
        qtbot.mouseClick(project_db_tab.new_project_param, QtCore.Qt.LeftButton)

    # Fill with variables
    assert proj_table.dataframe.shape[0] == 1
    df = pd.DataFrame([{
        "name": "test_project", "amount": 2.5, "formula": ""
    }], columns = ["name", "amount", "formula"])
    proj_table.dataframe.update(df)

    with qtbot.waitSignal(signals.parameters_changed, timeout=1000):
        qtbot.mouseClick(project_db_tab.save_project_btn, QtCore.Qt.LeftButton)

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

    project_db_tab = ProjectDatabaseTab()
    qtbot.addWidget(project_db_tab)
    project_db_tab.build_dataframes()
    db_table = project_db_tab.database_table

    with qtbot.waitSignals([db_table.new_parameter, db_table.new_parameter], timeout=1000):
        qtbot.mouseClick(project_db_tab.new_database_param, QtCore.Qt.LeftButton)
        qtbot.mouseClick(project_db_tab.new_database_param, QtCore.Qt.LeftButton)

    assert db_table.dataframe.shape[0] == 2
    df = pd.DataFrame([
        {"database": "biosphere3", "name": "test_db1", "formula": "test_project + 3.5"},
        {"database": "biosphere3", "name": "test_db2", "formula": "test_db1 ** 2"}
    ], columns = ["database", "name", "amount", "formula"])
    db_table.dataframe.update(df)

    with qtbot.waitSignal(signals.parameters_changed, timeout=1000):
        qtbot.mouseClick(project_db_tab.save_database_btn, QtCore.Qt.LeftButton)

    assert DatabaseParameter.select().count() == 2
    # 2.5 + 3.5 = 6 -> 6 ** 2 = 36
    assert DatabaseParameter.get(name="test_db2").amount == 36
