import pytest
import os
import bw2data as bd
from PySide2 import QtWidgets
from activity_browser import actions, application
from activity_browser.mod.bw2data import Database
from activity_browser.bwutils import AB_metadata
from activity_browser.ui.widgets import EcoinventVersionDialog, DefaultBiosphereDialog, BiosphereUpdater
from activity_browser.ui.wizards.settings_wizard import SettingsWizard
from activity_browser.ui.wizards.plugins_manager_wizard import PluginsManagerWizard



@pytest.mark.skipif(os.environ.get("TEST_FAST", False), reason="Skipped for faster testing")
def test_default_install(ab_app, monkeypatch, qtbot):
    project_name = "biosphere_project"
    bd.projects.set_current(project_name)

    monkeypatch.setattr(
        EcoinventVersionDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: EcoinventVersionDialog.Accepted)
    )
    monkeypatch.setattr(
        QtWidgets.QComboBox, 'currentText',
        staticmethod(lambda *args, **kwargs: '3.7')
    )

    assert bd.projects.current == project_name
    assert "biosphere3" not in bd.databases
    assert not application.main_window.findChild(DefaultBiosphereDialog)

    actions.DefaultInstall.run()

    dialog = application.main_window.findChild(DefaultBiosphereDialog)
    with qtbot.waitSignal(dialog.finished, timeout=5 * 60 * 1000): pass
    qtbot.waitUntil(lambda: len(AB_metadata.dataframe) == 4324)

    assert "biosphere3" in bd.databases
    assert len(Database("biosphere3")) == 4324
    assert len(bd.methods) == 762


@pytest.mark.skipif(os.environ.get("TEST_FAST", False), reason="Skipped for faster testing")
def test_biosphere_update(ab_app, monkeypatch, qtbot):
    project_name = "biosphere_project"
    bd.projects.set_current(project_name)

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'question',
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Ok)
    )
    monkeypatch.setattr(
        EcoinventVersionDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: EcoinventVersionDialog.Accepted)
    )
    monkeypatch.setattr(
        QtWidgets.QComboBox, 'currentText',
        staticmethod(lambda *args, **kwargs: '3.9.1')
    )

    assert bd.projects.current == project_name
    assert "biosphere3" in bd.databases
    assert len(Database("biosphere3")) == 4324

    actions.BiosphereUpdate.run()

    dialog = application.main_window.findChild(BiosphereUpdater)
    with qtbot.waitSignal(dialog.finished, timeout=5*60*1000): pass

    assert len(Database("biosphere3")) == 4743


def test_plugin_wizard_open(ab_app):
    assert not application.main_window.findChild(PluginsManagerWizard)

    actions.PluginWizardOpen.run()

    assert application.main_window.findChild(PluginsManagerWizard).isVisible()

    application.main_window.findChild(PluginsManagerWizard).destroy()


def test_settings_wizard_open(ab_app):
    assert not application.main_window.findChild(SettingsWizard)

    actions.SettingsWizardOpen.run()

    assert application.main_window.findChild(SettingsWizard).isVisible()

    application.main_window.findChild(SettingsWizard).destroy()
