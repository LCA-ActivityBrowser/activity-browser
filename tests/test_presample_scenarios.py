# -*- coding: utf-8 -*-
from pathlib import Path

import brightway2 as bw
from bw2data.parameters import ProjectParameter
import numpy as np
import pandas as pd
import presamples as ps
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QFileDialog, QInputDialog
import pytest

from activity_browser.signals import signals
from activity_browser.ui.tables.scenarios import PresamplesList, ScenarioTable
from activity_browser.ui.tables.models import ScenarioModel
from activity_browser.layouts.tabs.parameters import ParametersTab, ParameterScenariosTab


# TODO ps

@pytest.fixture
def project_parameters(bw2test):
    ProjectParameter.create(name="test1", amount=3)
    ProjectParameter.create(name="test2", amount=5)
    ProjectParameter.create(name="test3", amount=7)
    return


@pytest.fixture
def scenario_dataframes():
    data = [
        ("test1", "project", 3.0),
        ("test2", "project", 5.0),
        ("test3", "project", 7.0),
    ]
    df = pd.DataFrame(data, columns=ScenarioModel.HEADERS)
    new_df = df.copy()
    return df, new_df


@pytest.mark.skip(reason="test needs to be fixed")
def test_empty_presamples_list(qtbot, bw2test):
    """ The presamples dropdown list has default values when no presample
    packages exist.
    """
    p_list = PresamplesList()
    qtbot.addWidget(p_list)
    assert p_list.get_package_names() == []
    assert p_list.has_packages is False
    assert p_list.selection == ""


@pytest.mark.skip(reason="test needs to be fixed")
def test_existing_presamples_list(qtbot, bw2test):
    """ The presamples dropdown can recognize existing presample packages.
    """
    cereal = np.array([49197200, 50778200, 50962400], dtype=np.int64)
    fertilizer = np.array([57.63016664, 58.92761065, 54.63277483], dtype=np.float64)
    land = np.array([17833000, 16161700, 15846800], dtype=np.int64)
    array_stack = np.stack([cereal, fertilizer, land], axis=0)
    names = ['cereal production [t]', 'fert consumption [kg/km2]', 'land [ha]']
    _, pp_path = ps.create_presamples_package(
        parameter_data=[(array_stack, names, "default")], name="testificate"
    )

    p_list = PresamplesList()
    qtbot.addWidget(p_list)

    packages = p_list.get_package_names()
    pkg_name = next(iter(packages))
    p_list.sync(pkg_name)

    assert packages == ["testificate"]
    assert p_list.has_packages is True
    assert p_list.selection == "testificate"


@pytest.mark.skip(reason="test needs to be fixed")
def test_empty_scenario_table(qtbot, bw2test):
    """ In a new/unparameterized project, the scenario table is empty.
    """
    table = ScenarioTable()
    qtbot.addWidget(table)
    table.model.sync()
    assert table.rowCount() == 0


@pytest.mark.skip(reason="test needs to be fixed")
def test_scenario_table(qtbot, project_parameters):
    """ The scenario table will recognize existing parameters during sync.
    """
    table = ScenarioTable()
    qtbot.addWidget(table)
    table.model.sync()
    assert table.rowCount() == 3


@pytest.mark.skip(reason="test needs to be fixed")
def test_scenario_table_rebuild(qtbot, project_parameters):
    """ Altering the amount of a parameter causes the scenario table to rebuild.
    """
    tab = ParametersTab()
    qtbot.addWidget(tab)
    project_table = tab.tabs.get("Definitions").project_table
    scenario_table = tab.tabs.get("Scenarios").tbl
    scenario_table.model.sync()  # Trigger a clean sync

    begin_df = scenario_table.model._dataframe.copy()

    assert begin_df.equals(scenario_table.model._dataframe)
    with qtbot.waitSignal(signals.parameters_changed, timeout=500):
        project_table.model.setData(project_table.model.index(0, 1), 16)
    assert not begin_df.equals(scenario_table.model._dataframe)


@pytest.mark.skip(reason="test needs to be fixed")
def test_scenario_table_rename(qtbot, project_parameters, monkeypatch):
    """ Renaming a parameter will change the index of the dataframe
    but not the values. (not that there is an easy way to test this)
    """
    tab = ParametersTab()
    qtbot.addWidget(tab)
    project_table = tab.tabs.get("Definitions").project_table
    scenario_table = tab.tabs.get("Scenarios").tbl
    scenario_table.model.sync()  # Trigger a clean sync

    assert scenario_table.model._dataframe.index[0] == "test1"
    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *args, **kwargs: ("newname", True))
    )
    with qtbot.waitSignal(signals.parameter_renamed, timeout=500):
        project_table.model.handle_parameter_rename(project_table.proxy_model.index(0, 0))
    assert scenario_table.model._dataframe.index[0] == "newname"


def test_scenario_merge_new_scenarios(scenario_dataframes):
    df, new = scenario_dataframes
    assert df.equals(new)
    new.insert(3, "Scenario1", [5.0, 7.0, 9.0])
    new.insert(4, "Scenario2", [12.0, 16.0, 19.0])
    assert not df.equals(new)

    # `_perform_merge` is destructive to the 2nd DataFrame passed, so use a copy
    df = ScenarioModel._perform_merge(df, new.copy())
    assert df.equals(new)


def test_scenario_merge_new_rows(scenario_dataframes):
    df, new = scenario_dataframes
    new: pd.DataFrame
    new.insert(3, "Scenario1", [5.0, 7.0, 9.0])
    new.insert(4, "Scenario2", [12.0, 16.0, 19.0])
    df = ScenarioModel._perform_merge(df, new.copy())
    assert df.equals(new)

    new = new.append({
        "Name": "test4", "Group": "act1", "default": 3.0,
        "Scenario1": 2.5, "Scenario2": 7.4
    }, ignore_index=True)
    assert not df.equals(new)
    df = ScenarioModel._perform_merge(df, new.copy())
    # Unknown Name/Group combinations are ignored when merging
    assert "test4" not in df["Name"]


def test_scenario_merge_new_values(scenario_dataframes):
    df, new = scenario_dataframes
    new.insert(3, "Scenario1", [5.0, 7.0, 9.0])
    new.insert(4, "Scenario2", [12.0, 16.0, 19.0])
    df = ScenarioModel._perform_merge(df, new.copy())
    assert df.equals(new)
    # Now alter values in the existing scenario columns.
    new.iat[1, 3] = 71.0
    new.iat[0, 4] = 2.0
    assert not df.equals(new)
    df = ScenarioModel._perform_merge(df, new.copy())
    assert df.equals(new)


def test_scenario_merge_empty_values(scenario_dataframes):
    df, new = scenario_dataframes
    new.insert(3, "Scenario1", [5.0, 7.0, 9.0])
    df = ScenarioModel._perform_merge(df, new.copy())
    assert df.equals(new)

    new.iat[0, 3] = 50.0
    new.insert(4, "Scenario2", [12.0, np.NaN, 19.0])
    assert not df.equals(new)
    df = ScenarioModel._perform_merge(df, new.copy())
    # Now the dataframes are not equal! Why?
    assert not df.equals(new)
    # Because the merge causes the value from the 'default' column to be copied
    # over the NaN value.
    assert new["Scenario2"].hasnans
    assert df.iat[1, 4] == df.iat[1, 2]


@pytest.mark.skip(reason="test needs to be fixed")
def test_scenario_tab(qtbot, monkeypatch, project_parameters):
    """ Test the simple functioning of the scenario presamples tab.
    clicky buttons!
    """
    tab = ParameterScenariosTab()
    qtbot.addWidget(tab)
    tab.tbl.model.sync()
    tab.tbl.group_column(False)
    store_path = Path(bw.projects.dir) / "testsave.xlsx"

    # Save the table to the store_path, and load it in afterwards.
    assert not store_path.is_file()  # The file doesn't exist.
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (store_path, True)))
    with qtbot.waitSignal(tab.save_btn.clicked, timeout=500):
        qtbot.mouseClick(tab.save_btn, Qt.LeftButton)
    qtbot.wait(500)
    assert store_path.is_file()  # Yes, saving the file worked.
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *args, **kwargs: (store_path, True)))
    with qtbot.waitSignal(tab.load_btn.clicked, timeout=500):
        qtbot.mouseClick(tab.load_btn, Qt.LeftButton)

    assert tab.tbl.isColumnHidden(0) is True
    tab.hide_group.toggle()
    assert tab.tbl.isColumnHidden(0) is False
