import os

import bw2data as bd
import pytest
from PySide2 import QtWidgets

from activity_browser import actions, application
from activity_browser.mod.bw2data import Database
from activity_browser.ui.wizards.plugins_manager_wizard import PluginsManagerWizard
from activity_browser.ui.widgets import EcoinventVersionDialog
from activity_browser.ui.wizards import ProjectSetupWizard
from activity_browser.ui.wizards.settings_wizard import SettingsWizard


@pytest.mark.skipif(
    os.environ.get("TEST_FAST", False), reason="Skipped for faster testing"
)
def test_default_install(ab_app, monkeypatch, qtbot):
    project_name = "biosphere_project"
    bd.projects.set_current(project_name)

    monkeypatch.setattr(
        EcoinventVersionDialog,
        "exec_",
        staticmethod(lambda *args, **kwargs: EcoinventVersionDialog.Accepted),
    )
    monkeypatch.setattr(
        QtWidgets.QComboBox, "currentText", staticmethod(lambda *args, **kwargs: "3.7")
    )

    assert bd.projects.current == project_name
    assert "biosphere3" not in bd.databases
    assert not application.main_window.findChild(ProjectSetupWizard)

    actions.DefaultInstall.run()

    wizard: ProjectSetupWizard = application.main_window.findChild(ProjectSetupWizard)
    wizard.next()

    thread = wizard.page(wizard.install_page).install_thread

    with qtbot.waitSignal(thread.finished, timeout=5 * 60 * 1000):
        pass
    # qtbot.waitUntil(lambda: len(AB_metadata.dataframe) == 4709)

    assert "biosphere3" in bd.databases
    assert len(Database("biosphere3")) == 4709
    assert len(bd.methods) == 762


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
