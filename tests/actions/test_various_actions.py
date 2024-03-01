import pytest
import os
import brightway2 as bw
from PySide2 import QtWidgets
from activity_browser import actions, project_controller, database_controller, signals
from activity_browser.ui.widgets import EcoinventVersionDialog


def test_default_install(ab_app, monkeypatch, qtbot):
    if os.environ["TEST_FAST"]: return

    project_name = "biosphere_project"
    project_controller.new_project(project_name)

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

    with qtbot.waitSignal(signals.databases_changed, timeout=5 * 60 * 1000): pass

    assert "biosphere3" in bw.databases
    assert database_controller.record_count("biosphere3") == 4324
    assert len(bw.methods) == 762


def test_biosphere_update(ab_app, monkeypatch, qtbot):
    if os.environ["TEST_FAST"]: return

    project_name = "biosphere_project"
    project_controller.change_project(project_name, reload=True)

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
    assert database_controller.record_count("biosphere3") == 4324

    action = actions.BiosphereUpdate(None)
    action.trigger()

    with qtbot.waitSignal(action.updater.finished, timeout=5*60*1000): pass

    assert database_controller.record_count("biosphere3") == 4743


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
