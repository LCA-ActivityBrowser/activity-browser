# -*- coding: utf-8 -*-
import os

import pytest

from activity_browser.app.settings import (ABSettings, BaseSettings,
                                           ProjectSettings)


@pytest.fixture()
def ab_settings():
    return ABSettings('test_ab.json')


@pytest.fixture()
def project_settings():
    return ProjectSettings('test_project.json')


AB_SETTINGS_KEYS = ["custom_bw_dir", "startup_project"]
PROJECT_SETTINGS_KEYS = ["read-only-databases", "biosphere"]


def test_base_class():
    """ Test that the base class raises an error on initialization
    """
    current_path = os.path.dirname(os.path.abspath(__file__))
    with pytest.raises(NotImplementedError):
        settings = BaseSettings(current_path)


def test_ab_default_keys(ab_settings):
    defaults = ab_settings.get_default_settings()
    assert all(key in defaults for key in AB_SETTINGS_KEYS)


def test_ab_default_settings(ab_settings):
    assert ABSettings.get_default_directory() == ab_settings.custom_bw_dir
    assert ABSettings.get_default_project_name() == ab_settings.startup_project


def test_ab_edit_settings(ab_settings):
    current_path = os.path.dirname(os.path.abspath(__file__))
    ab_settings.custom_bw_dir = current_path
    assert ab_settings.custom_bw_dir != ABSettings.get_default_directory()


def test_ab_existing_startup(ab_settings):
    ab_settings.startup_project = "pytest_project"
    assert ab_settings.startup_project != ABSettings.get_default_project_name()


def test_ab_unknown_startup(ab_settings):
    ab_settings.startup_project = "unknown_project"
    assert ab_settings.startup_project == ABSettings.get_default_project_name()


def test_cleanup_ab_settings(ab_settings):
    if os.path.isfile(ab_settings.settings_file):
        os.remove(ab_settings.settings_file)
    assert not os.path.isfile(ab_settings.settings_file)


def test_project_default_keys(project_settings):
    defaults = project_settings.get_default_settings()
    assert all(key in defaults for key in PROJECT_SETTINGS_KEYS)


def test_project_default_biosphere(project_settings):
    assert ProjectSettings.get_default_biosphere_types() == project_settings.biosphere_types


def test_project_valid_biospheres(ab_app, project_settings):
    valid_types = ["emission", "social", "economic"]
    assert len(project_settings.valid_biospheres(valid_types)) == 0


def test_project_invalid_biospheres(ab_app, project_settings):
    wrong_types = ["emission", "testing"]
    invalid = project_settings.valid_biospheres(wrong_types)
    assert len(invalid) == 1
    assert "testing" in invalid
    assert "emission" not in invalid


def test_project_edit_biospheres(project_settings):
    project_settings.biosphere_types = ["emission", "social", "economic"]
    assert set(ProjectSettings.get_default_biosphere_types()).issuperset(project_settings.biosphere_types)


def test_project_add_dbs(project_settings):
    project_settings.add_db("fakedb")
    project_settings.add_db("fake_readabledb", False)
    assert project_settings.db_is_readonly("fakedb") is True
    assert project_settings.db_is_readonly("fake_readabledb") is False


def test_project_modify_db(project_settings):
    project_settings.modify_db("fakedb", False)
    assert project_settings.db_is_readonly("fakedb") is False


def test_project_editable_dbs(project_settings):
    editable_dbs = ["fakedb", "fake_readabledb"]
    assert all(db in editable_dbs for db in project_settings.get_editable_databases())


def test_project_remove_db(project_settings):
    project_settings.remove_db("fakedb")
    # If db cannot be found, return True
    assert project_settings.db_is_readonly("fakedb") is True


def test_cleanup_project_settings(project_settings):
    # Clear created settings file, helps with local testing
    if os.path.isfile(project_settings.settings_file):
        os.remove(project_settings.settings_file)
    assert not os.path.isfile(project_settings.settings_file)
