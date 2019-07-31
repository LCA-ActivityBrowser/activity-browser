# -*- coding: utf-8 -*-
import os

from PyQt5 import QtCore, QtWidgets

from activity_browser.app.signals import signals
from activity_browser.app.settings import ABSettings, ProjectSettings
from activity_browser.app.ui.wizards.settings_wizard import SettingsWizard


def test_open_ab_settings(qtbot):
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    first_page = wizard.page(wizard.choice_page)

    assert wizard.currentId() == wizard.choice_page
    with qtbot.waitSignal(wizard.currentIdChanged, timeout=1000):
        qtbot.mouseClick(first_page.ab_settings_btn, QtCore.Qt.LeftButton)
    assert wizard.currentId() == wizard.ab_page


def test_open_project_settings(qtbot):
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    first_page = wizard.page(wizard.choice_page)

    assert wizard.currentId() == wizard.choice_page
    with qtbot.waitSignal(wizard.currentIdChanged, timeout=1000):
        qtbot.mouseClick(first_page.project_settings_btn, QtCore.Qt.LeftButton)
    assert wizard.currentId() == wizard.project_page


def test_save_btn_visibility(qtbot):
    """ 'Finish' or 'Save' button is not visible on the first page,
    but is on either of the other pages.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    first_page = wizard.page(wizard.choice_page)

    assert wizard.currentId() == wizard.choice_page
    assert not wizard.button(QtWidgets.QWizard.FinishButton).isVisible()

    with qtbot.waitSignal(wizard.currentIdChanged, timeout=1000):
        qtbot.mouseClick(first_page.ab_settings_btn, QtCore.Qt.LeftButton)
    assert wizard.currentId() == wizard.ab_page
    assert wizard.button(QtWidgets.QWizard.FinishButton).isVisible()

    with qtbot.waitSignal(wizard.currentIdChanged, timeout=1000):
        qtbot.mouseClick(first_page.project_settings_btn, QtCore.Qt.LeftButton)
    assert wizard.currentId() == wizard.project_page
    assert wizard.button(QtWidgets.QWizard.FinishButton).isVisible()


def test_save_settings_wizard(qtbot):
    """ Ignore that we can't see the button and trigger a save.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)

    with qtbot.waitSignal(wizard.accepted, timeout=1000):
        qtbot.mouseClick(wizard.button(QtWidgets.QWizard.FinishButton), QtCore.Qt.LeftButton)


def test_change_cancel_ab_dir_known(qtbot, mock):
    """ Open the 'change directory' selection menu, select the default
    directory and do nothing.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    ab_page = wizard.page(wizard.ab_page)
    default = ABSettings.get_default_directory()

    # First, check that the current text is the default
    assert ab_page.bwdir_edit.placeholderText() == default
    assert ab_page.bwdir_edit.text() == ""
    # Ensure the filedialog returns the default brightway directory
    mock.patch.object(
        QtWidgets.QFileDialog, "getExistingDirectory",
        return_value=default
    )
    # Tell the settings no when it asks if we want to switch directory
    mock.patch.object(
        QtWidgets.QMessageBox, "question",
        return_value=QtWidgets.QMessageBox.No
    )
    qtbot.mouseClick(ab_page.bwdir_browse_btn, QtCore.Qt.LeftButton)
    # 'changing' to a known directory means the text field is also filled out
    assert ab_page.bwdir_edit.placeholderText() == default
    assert ab_page.bwdir_edit.text() == default


def test_change_cancel_ab_dir_new(qtbot, mock):
    """ Open the 'change directory' selection menu, select a directory without
    brightway files and cancel.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    ab_page = wizard.page(wizard.ab_page)
    default = ABSettings.get_default_directory()
    current_path = os.path.dirname(os.path.abspath(__file__))

    # First, check that the current text is the default
    assert ab_page.bwdir_edit.placeholderText() == default
    assert ab_page.bwdir_edit.text() == ""
    # Ensure the filedialog returns the 'tests' directory.
    mock.patch.object(
        QtWidgets.QFileDialog, "getExistingDirectory",
        return_value=current_path
    )
    # Tell the settings no when it asks if we want to switch directory
    mock.patch.object(
        QtWidgets.QMessageBox, "question",
        return_value=QtWidgets.QMessageBox.Cancel
    )
    qtbot.mouseClick(ab_page.bwdir_browse_btn, QtCore.Qt.LeftButton)
    # And now, everything should still be the same
    assert ab_page.bwdir_edit.placeholderText() == default
    assert ab_page.bwdir_edit.text() == ""


def test_change_ab_startup_project(qtbot):
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    ab_page = wizard.page(wizard.ab_page)
    startup_project = ab_page.startup_project_combobox

    assert startup_project.currentText() == ABSettings.get_default_project_name()
    with qtbot.waitSignal(startup_project.currentIndexChanged, timeout=1000):
        qtbot.keyClicks(startup_project, "pytest_project")
    assert startup_project.currentText() == "pytest_project"


def test_revert_ab_settings(qtbot, mock):
    """ Revert the AB settings back to the defaults.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    ab_page = wizard.page(wizard.ab_page)
    startup_project = ab_page.startup_project_combobox

    # Tell the settings yes, we do want to want to revert the settings
    mock.patch.object(
        QtWidgets.QMessageBox, "question",
        return_value=QtWidgets.QMessageBox.Yes
    )
    with qtbot.waitSignal(signals.switch_bw2_dir_path, timeout=1000):
        qtbot.mouseClick(ab_page.restore_defaults_btn, QtCore.Qt.LeftButton)
    # Check that both fields are now back to defaults
    assert ab_page.bwdir_edit.placeholderText() == ABSettings.get_default_directory()
    assert ab_page.bwdir_edit.text() == ABSettings.get_default_directory()
    assert startup_project.currentText() == ABSettings.get_default_project_name()


def test_project_settings_validate(qtbot):
    """ The initial settings page leaves the validate btn non-active.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    project_page = wizard.page(wizard.project_page)

    assert not project_page.biospheres_valid_btn.isEnabled()
    with qtbot.assertNotEmitted(project_page.valid_change, wait=100):
        qtbot.mouseClick(project_page.biospheres_valid_btn, QtCore.Qt.LeftButton)


def test_project_settings_biospheres(qtbot):
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    project_page = wizard.page(wizard.project_page)
    default_types = ", ".join(ProjectSettings.get_default_biosphere_types())

    assert project_page.biospheres_field.text() == default_types


def test_project_settings_edit_biospheres_valid(qtbot):
    """ Input valid biosphere types into the field.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    project_page = wizard.page(wizard.project_page)
    valid_input = "emission, natural resource"
    default_types = ", ".join(ProjectSettings.get_default_biosphere_types())

    assert project_page.biospheres_field.text() == default_types
    # Change the text in the input field
    with qtbot.waitSignal(project_page.biospheres_field.textChanged, timeout=1000):
        project_page.biospheres_field.clear()
        qtbot.keyClicks(project_page.biospheres_field, valid_input)
    # The validate button is now active
    assert project_page.biospheres_valid_btn.isEnabled()
    # The changes are valid
    with qtbot.waitSignal(project_page.valid_change, timeout=1000):
        qtbot.mouseClick(project_page.biospheres_valid_btn, QtCore.Qt.LeftButton)
    # And not equal to the defaults
    assert project_page.biospheres_field.text() != default_types


def test_project_settings_edit_biospheres_invalid(qtbot, mock):
    """ Input invalid biosphere types into the field.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    project_page = wizard.page(wizard.project_page)
    invalid_input = "emission, fission mailed"
    default_types = ", ".join(ProjectSettings.get_default_biosphere_types())

    assert project_page.biospheres_field.text() == default_types
    # Change the text in the input field
    with qtbot.waitSignal(project_page.biospheres_field.textChanged, timeout=1000):
        qtbot.keyClicks(project_page.biospheres_field, invalid_input)
    assert project_page.biospheres_valid_btn.isEnabled()
    # Prepare to press the Ok button.
    mock.patch.object(
        QtWidgets.QMessageBox, "exec",
        return_value=QtWidgets.QMessageBox.Ok
    )
    # The changes are invalid and a warning is raised
    with qtbot.assertNotEmitted(project_page.valid_change, wait=1000):
        qtbot.mouseClick(project_page.biospheres_valid_btn, QtCore.Qt.LeftButton)


def test_revert_project_settings(qtbot):
    """ Revert the project settings back to the defaults.
    """
    wizard = SettingsWizard()
    qtbot.addWidget(wizard)
    project_page = wizard.page(wizard.project_page)
    default_types = ", ".join(ProjectSettings.get_default_biosphere_types())

    with qtbot.waitSignal(project_page.biospheres_field.textChanged, timeout=1000):
        qtbot.mouseClick(project_page.restore_defaults_btn, QtCore.Qt.LeftButton)
    # The validate button is now active
    assert project_page.biospheres_valid_btn.isEnabled()
    # The changes are valid
    with qtbot.waitSignal(project_page.valid_change, timeout=1000):
        qtbot.mouseClick(project_page.biospheres_valid_btn, QtCore.Qt.LeftButton)
    # And the text in the field is now equal to the defaults
    # Check that both fields are now back to defaults
    assert project_page.biospheres_field.text() == default_types
