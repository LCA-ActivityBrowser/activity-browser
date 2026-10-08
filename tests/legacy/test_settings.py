# -*- coding: utf-8 -*-
import json
import os

import pytest

import activity_browser.settings as settings_module
from activity_browser.settings import ABSettings, BaseSettings, ProjectSettings


@pytest.fixture()
def ab_settings(qtbot, ab_app):
    """Remove the test settings file after finishing the tests."""
    qtbot.waitForWindowShown(ab_app.main_window)
    settings = ABSettings("test_ab.json")
    yield settings
    if os.path.isfile(settings.settings_file):
        os.remove(settings.settings_file)


@pytest.fixture()
def project_settings(qtbot, ab_app):
    """No cleanup needed as the entire project is removed after testing."""
    qtbot.waitForWindowShown(ab_app.main_window)
    settings = ProjectSettings("test_project.json")
    yield settings


def test_base_class():
    """Test that the base class raises an error on initialization"""
    current_path = os.path.dirname(os.path.abspath(__file__))
    with pytest.raises(NotImplementedError):
        settings = BaseSettings(current_path)


def test_ab_default_keys(ab_settings):
    """Test that default setting are only created for the given keys."""
    defaults = ab_settings.get_default_settings()
    assert not {
        "current_bw_dir",
        "custom_bw_dirs",
        "language",
        "startup_project",
    }.symmetric_difference(defaults)


def test_ab_default_settings(ab_settings):
    assert ABSettings.get_default_directory() == ab_settings.custom_bw_dir[0]
    assert ABSettings.get_default_project_name() == ab_settings.startup_project


def test_ab_edit_settings(ab_settings):
    current_path = os.path.dirname(os.path.abspath(__file__))
    ab_settings.custom_bw_dir = current_path
    assert ab_settings.custom_bw_dir != ABSettings.get_default_directory()


def test_ab_language_uses_stable_code(ab_settings):
    assert ab_settings.language == "system"
    ab_settings.language = "Simplified Chinese"
    assert ab_settings.language == "zh_CN"


def test_ab_language_migration_is_persisted(ab_settings):
    ab_settings.settings.pop("language")
    ab_settings.settings["ui_language"] = "简体中文"

    ab_settings.migrate_settings()

    assert ab_settings.settings["language"] == "zh_CN"
    assert "ui_language" not in ab_settings.settings
    with open(ab_settings.settings_file, "r", encoding="utf-8") as settings_file:
        assert json.load(settings_file)["language"] == "zh_CN"


def test_old_settings_migration_preserves_language(tmp_path):
    settings_file = tmp_path / "legacy.json"
    settings_file.write_text(
        json.dumps(
            {
                "custom_bw_dir": str(tmp_path),
                "language": "Simplified Chinese",
                "startup_project": "default",
            }
        ),
        encoding="utf-8",
    )

    ABSettings.update_old_settings(str(tmp_path), settings_file.name)

    migrated = json.loads(settings_file.read_text(encoding="utf-8"))
    assert migrated["language"] == "Simplified Chinese"
    assert migrated["current_bw_dir"] == str(tmp_path)
    assert migrated["custom_bw_dirs"] == [str(tmp_path)]


def test_settings_json_uses_utf8(tmp_path):
    class UnicodeSettings(BaseSettings):
        @classmethod
        def get_default_settings(cls):
            return {"label": "中文界面"}

    settings = UnicodeSettings(str(tmp_path), "unicode.json")
    settings.write_settings()

    raw = (tmp_path / "unicode.json").read_bytes()
    assert "中文界面" in raw.decode("utf-8")
    settings.load_settings()
    assert settings.settings["label"] == "中文界面"


def test_remove_missing_directory_keeps_runtime_error_as_message_detail(
    ab_settings, monkeypatch
):
    displayed = []
    monkeypatch.setattr(
        settings_module.QMessageBox,
        "warning",
        lambda *arguments: displayed.append(arguments),
    )

    ab_settings.remove_custom_bw_dir("directory-not-in-settings")

    assert len(displayed) == 1
    parent, title, message, button = displayed[0]
    assert parent is None
    assert title
    assert "list.remove" in message
    assert button == settings_module.QMessageBox.Ok


def test_ab_unknown_startup(ab_settings):
    """Alter the startup project with an unknown project, assert that it
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
