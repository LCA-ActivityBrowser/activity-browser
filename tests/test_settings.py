# -*- coding: utf-8 -*-
import os

import brightway2 as bw
import pytest

from activity_browser.settings import (ABSettings, BaseSettings,
                                           ProjectSettings)


@pytest.fixture()
def ab_settings(qtbot, ab_app):
    """ Remove the test settings file after finishing the tests.
    """
    qtbot.waitForWindowShown(ab_app.main_window)
    settings = ABSettings('test_ab.json')
    yield settings
    if os.path.isfile(settings.settings_file):
        os.remove(settings.settings_file)


@pytest.fixture()
def project_settings(qtbot, ab_app):
    """ No cleanup needed as the entire project is removed after testing.
    """
    qtbot.waitForWindowShown(ab_app.main_window)
    settings = ProjectSettings('test_project.json')
    yield settings


def test_base_class():
    """ Test that the base class raises an error on initialization
    """
    current_path = os.path.dirname(os.path.abspath(__file__))
    with pytest.raises(NotImplementedError):
        settings = BaseSettings(current_path)


def test_ab_default_keys(ab_settings):
    """ Test that default setting are only created for the given keys.
    """
    defaults = ab_settings.get_default_settings()
    assert not {"custom_bw_dir", "startup_project", "plugins_list"}.symmetric_difference(defaults)


def test_ab_default_settings(ab_settings):
    assert ABSettings.get_default_directory() == ab_settings.custom_bw_dir
    assert ABSettings.get_default_project_name() == ab_settings.startup_project


def test_ab_edit_settings(ab_settings):
    current_path = os.path.dirname(os.path.abspath(__file__))
    ab_settings.custom_bw_dir = current_path
    assert ab_settings.custom_bw_dir != ABSettings.get_default_directory()


@pytest.mark.skipif("pytest_project" not in bw.projects, reason="test project not created")
def test_ab_existing_startup(ab_settings):
    """ Alter the startup project and assert that it is correctly changed.

    Will be skipped if test_settings.py is run in isolation because the test
    project has not been created (results in duplicate of test below)
    """
    ab_settings.startup_project = "pytest_project"
    assert ab_settings.startup_project != ABSettings.get_default_project_name()


def test_ab_unknown_startup(ab_settings):
    """ Alter the startup project with an unknown project, assert that it
    was not altered because the project does not exist.
    """
    ab_settings.startup_project = "unknown_project"
    assert ab_settings.startup_project == ABSettings.get_default_project_name()


def test_project_default_keys(project_settings):
    defaults = project_settings.get_default_settings()
    assert not {"plugins_list", "read-only-databases"}.symmetric_difference(defaults)


def test_project_add_dbs(project_settings):
    project_settings.add_db("fakedb")
    project_settings.add_db("fake_readabledb", False)
    assert project_settings.db_is_readonly("fakedb") is True
    assert project_settings.db_is_readonly("fake_readabledb") is False


def test_project_modify_db(project_settings):
    assert project_settings.db_is_readonly("fakedb") is True
    project_settings.modify_db("fakedb", False)
    assert project_settings.db_is_readonly("fakedb") is False


def test_project_editable_dbs(project_settings):
    editable_dbs = {"fakedb", "fake_readabledb"}
    assert all(db in editable_dbs for db in project_settings.get_editable_databases())


def test_project_remove_db(project_settings):
    project_settings.remove_db("fakedb")
    # If db cannot be found, return True
    assert project_settings.db_is_readonly("fakedb") is True
