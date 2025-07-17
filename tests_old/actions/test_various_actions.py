from activity_browser import actions, application
from activity_browser.ui.wizards.plugins_manager_wizard import PluginsManagerWizard
from activity_browser.ui.wizards.settings_wizard import SettingsWizard

####### DEPRECATED IN BW25
#
# @pytest.mark.skipif(
#     os.environ.get("TEST_FAST", False), reason="Skipped for faster testing"
# )
# def test_default_install(ab_app, monkeypatch, qtbot):
#     project_name = "biosphere_project"
#     projects.set_current(project_name)
#
#     monkeypatch.setattr(
#         EcoinventVersionDialog,
#         "exec_",
#         staticmethod(lambda *args, **kwargs: EcoinventVersionDialog.Accepted),
#     )
#     monkeypatch.setattr(
#         QtWidgets.QComboBox, "currentText", staticmethod(lambda *args, **kwargs: "3.9")
#     )
#
#     assert projects.current == project_name
#     assert "biosphere3" not in databases
#     assert not application.main_window.findChild(DefaultBiosphereDialog)
#
#     actions.DefaultInstall.run(check_patches=False)
#
#     dialog = application.main_window.findChild(DefaultBiosphereDialog)
#     with qtbot.waitSignal(dialog.finished, timeout=5 * 60 * 1000):
#         pass
#     # TODO: look into why AB_metadata not being populated
#     # qtbot.waitUntil(lambda: len(AB_metadata.dataframe) == 4709)
#
#     assert "biosphere3" in databases
#     assert len(Database("biosphere3")) == 4709
#     assert len(methods) == 762
#
#
# @pytest.mark.skipif(
#     os.environ.get("TEST_FAST", False), reason="Skipped for faster testing"
# )
# def test_biosphere_update(ab_app, monkeypatch, qtbot):
#     project_name = "biosphere_project"
#     projects.set_current(project_name)
#
#     monkeypatch.setattr(
#         QtWidgets.QMessageBox,
#         "question",
#         staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Ok),
#     )
#     monkeypatch.setattr(
#         EcoinventVersionDialog,
#         "exec_",
#         staticmethod(lambda *args, **kwargs: EcoinventVersionDialog.Accepted),
#     )
#     monkeypatch.setattr(
#         QtWidgets.QComboBox,
#         "currentText",
#         staticmethod(lambda *args, **kwargs: "3.9.1"),
#     )
#
#     assert projects.current == project_name
#     assert "biosphere3" in databases
#     assert len(Database("biosphere3")) == 4709
#
#     actions.BiosphereUpdate.run()
#
#     dialog = application.main_window.findChild(BiosphereUpdater)
#     with qtbot.waitSignal(dialog.finished, timeout=5 * 60 * 1000):
#         pass
#
#     assert len(Database("biosphere3")) == 4718


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
