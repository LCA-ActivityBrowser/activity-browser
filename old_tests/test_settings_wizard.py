# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QMessageBox, QWizard

from activity_browser.ui.wizards.settings_wizard import SettingsWizard
from activity_browser.settings import ab_settings

def test_settings_wizard_simple(qtbot, bw2test):
    """Test some of the default values of the wizard."""
    wizard = SettingsWizard(None)
    qtbot.addWidget(wizard)
    wizard.show()

    # Check that the default fields are default
    assert wizard.field("startup_project") == "default"
    assert wizard.field("current_bw_dir") == ab_settings.current_bw_dir
    assert wizard.last_bwdir == bw.projects._base_data_dir

    # We can't click 'Save' from the start.
    assert not wizard.button(QWizard.FinishButton).isEnabled()

    # cancel out of the wizard.
    qtbot.mouseClick(wizard.button(QWizard.CancelButton), Qt.LeftButton)


def test_alter_startup_project(qtbot):
    """Alter the default startup project"""
    wizard = SettingsWizard(None)
    qtbot.addWidget(wizard)
    wizard.show()

    # Check we can't Save, alter the startup project and check again.
    assert not wizard.settings_page.isComplete()
    with qtbot.waitSignal(wizard.settings_page.completeChanged, timeout=100):
        index = wizard.settings_page.project_names.index("pytest_project")
        wizard.settings_page.startup_project_combobox.setCurrentIndex(index)
    assert wizard.field("startup_project") == "pytest_project"
    assert wizard.settings_page.isComplete()

    with qtbot.waitSignal(wizard.finished, timeout=100):
        qtbot.mouseClick(wizard.button(QWizard.FinishButton), Qt.LeftButton)


def test_restore_defaults(qtbot, monkeypatch):
    """Restore the default startup project."""
    wizard = SettingsWizard(None)
    qtbot.addWidget(wizard)
    wizard.show()

    # Follow-up from the last test, restore the startup_project to default
    assert wizard.field("startup_project") == "pytest_project"

    with qtbot.waitSignal(wizard.settings_page.startup_project_combobox.currentIndexChanged, timeout=100):
        # No handle the popup about changing the brightway2 directory.
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
        qtbot.mouseClick(
            wizard.settings_page.restore_defaults_button,
            Qt.LeftButton
        )

    assert wizard.field("startup_project") == "default"

    with qtbot.waitSignal(wizard.finished, timeout=100):
        qtbot.mouseClick(wizard.button(QWizard.FinishButton), Qt.LeftButton)
