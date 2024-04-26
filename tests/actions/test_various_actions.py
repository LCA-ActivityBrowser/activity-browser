import pytest
import os
import brightway2 as bw
from PySide2 import QtWidgets
from activity_browser import actions, signals
from activity_browser.brightway.bw2data import Database
from activity_browser.ui.widgets import EcoinventVersionDialog


@pytest.mark.skipif(os.environ.get("TEST_FAST", False), reason="Skipped for faster testing")
def test_default_install(ab_app, monkeypatch, qtbot):
    project_name = "biosphere_project"
    bw.projects.set_current(project_name)

    monkeypatch.setattr(
        EcoinventVersionDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: EcoinventVersionDialog.Accepted)
    )
    monkeypatch.setattr(
        QtWidgets.QComboBox, 'currentText',
        staticmethod(lambda *args, **kwargs: '3.7')
    )

    assert bw.projects.current == project_name
    assert "biosphere3" not in bw.databases

    action = actions.DefaultInstall(None)
    action.trigger()

    with qtbot.waitSignal(action.dialog.finished, timeout=5 * 60 * 1000): pass

    assert "biosphere3" in bw.databases
    print(len(Database("biosphere3")))
    assert len(Database("biosphere3")) == 4318
    assert len(bw.methods) == 762


@pytest.mark.skipif(os.environ.get("TEST_FAST", False), reason="Skipped for faster testing")
def test_biosphere_update(ab_app, monkeypatch, qtbot):
    project_name = "biosphere_project"
    bw.projects.set_current(project_name)

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

    assert bw.projects.current == project_name
    assert "biosphere3" in bw.databases
    assert len(Database("biosphere3")) == 4318

    action = actions.BiosphereUpdate(None)
    action.trigger()

    with qtbot.waitSignal(action.updater.finished, timeout=5*60*1000): pass

    assert len(Database("biosphere3")) == 4743


def test_plugin_wizard_open(ab_app):
    action = actions.PluginWizardOpen(None)

    with pytest.raises(AttributeError): assert not action.wizard.isVisible()

    action.trigger()

    assert action.wizard.isVisible()


def test_settings_wizard_open(ab_app):
    action = actions.SettingsWizardOpen(None)

    with pytest.raises(AttributeError): assert not action.wizard.isVisible()

    action.trigger()

    assert action.wizard.isVisible()

    action.wizard.destroy()
