# -*- coding: utf-8 -*-
import os

import pytest

from activity_browser.app.settings import (ABSettings, BaseSettings,
                                           ProjectSettings)


def test_base_class():
    """ Test that the base class raises an error on initialization
    """
    current_path = os.path.dirname(os.path.abspath(__file__))
    with pytest.raises(NotImplementedError):
        settings = BaseSettings(current_path)


def test_application_settings():
    """ Test various things about the application settings
    """
    ab_settings = ABSettings('testABsettings.json')
    defaults = ab_settings.get_default_settings()
    assert all(key in defaults for key in ["custom_bw_dir", "startup_project"])
    assert ABSettings.get_default_directory() == defaults["custom_bw_dir"]
    assert ABSettings.get_default_project_name() == defaults["startup_project"]

    # Alter variables
    current_path = os.path.dirname(os.path.abspath(__file__))
    ab_settings.custom_bw_dir = current_path
    assert ab_settings.custom_bw_dir != ABSettings.get_default_directory()
    # set existing project as startup project
    ab_settings.startup_project = "pytest_project"
    assert ab_settings.startup_project != ABSettings.get_default_project_name()
    # set unknown project as startup project
    ab_settings.startup_project = "unknown_project"
    assert ab_settings.startup_project == ABSettings.get_default_project_name()

    # Clear created settings file, helps with local testing
    if os.path.isfile(ab_settings.settings_file):
        os.remove(ab_settings.settings_file)


def test_project_settings():
    """ Test various things about the project settings
    """
    project_settings = ProjectSettings('testAB_project_settings.json')
    defaults = project_settings.get_default_settings()
    assert all(key in defaults for key in ["read-only-databases", "biosphere"])
    assert ProjectSettings.get_default_biosphere_types() == defaults["biosphere"]

    # Add some fake dbs to the settings
    project_settings.add_db("fakedb")
    project_settings.add_db("fake_readabledb", False)
    assert project_settings.db_is_readonly("fakedb") is True
    assert project_settings.db_is_readonly("fake_readabledb") is False
    project_settings.modify_db("fakedb", False)
    assert project_settings.db_is_readonly("fakedb") is False
    assert project_settings.get_editable_databases() == ["fakedb", "fake_readabledb"]
    project_settings.remove_db("fakedb")
    # If db cannot be found, return True
    assert project_settings.db_is_readonly("fakedb") is True

    # Clear created settings file, helps with local testing
    if os.path.isfile(project_settings.settings_file):
        os.remove(project_settings.settings_file)
