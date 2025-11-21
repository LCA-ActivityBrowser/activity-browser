"""Test wizard button visibility based on page.buttons property"""
import pytest
from qtpy import QtWidgets
from activity_browser.ui.widgets import ABWizard, ABWizardPage


class TestPage1(ABWizardPage):
    """Test page with custom button configuration"""
    title = "Page 1"
    buttons = [
        QtWidgets.QWizard.WizardButton.NextButton,
        QtWidgets.QWizard.WizardButton.CancelButton,
    ]


class TestPage2(ABWizardPage):
    """Test page with different button configuration"""
    title = "Page 2"
    buttons = [
        QtWidgets.QWizard.WizardButton.BackButton,
        QtWidgets.QWizard.WizardButton.FinishButton,
        QtWidgets.QWizard.WizardButton.CancelButton,
    ]


class TestPage3(ABWizardPage):
    """Test page using default button configuration"""
    title = "Page 3"


class TestWizard(ABWizard):
    """Test wizard with multiple pages"""
    pages = [TestPage1, TestPage2, TestPage3]


def test_wizard_button_visibility_first_page(qtbot):
    """Test that buttons are visible/hidden correctly on the first page"""
    wizard = TestWizard()
    qtbot.addWidget(wizard)

    # Initialize first page
    wizard.restart()

    # Check button visibility for first page (only Next and Cancel should be visible)
    assert not wizard.button(QtWidgets.QWizard.WizardButton.BackButton).isVisible()
    assert wizard.button(QtWidgets.QWizard.WizardButton.NextButton).isVisible()
    assert wizard.button(QtWidgets.QWizard.WizardButton.CancelButton).isVisible()
    assert not wizard.button(QtWidgets.QWizard.WizardButton.FinishButton).isVisible()


def test_wizard_button_visibility_second_page(qtbot):
    """Test that buttons are visible/hidden correctly on the second page"""
    wizard = TestWizard()
    qtbot.addWidget(wizard)

    # Navigate to second page
    wizard.restart()
    wizard.next()

    # Check button visibility for second page (Back, Finish, Cancel should be visible)
    assert wizard.button(QtWidgets.QWizard.WizardButton.BackButton).isVisible()
    assert not wizard.button(QtWidgets.QWizard.WizardButton.NextButton).isVisible()
    assert wizard.button(QtWidgets.QWizard.WizardButton.CancelButton).isVisible()
    assert wizard.button(QtWidgets.QWizard.WizardButton.FinishButton).isVisible()


def test_wizard_button_visibility_third_page_default(qtbot):
    """Test that default buttons are shown when page.buttons is not customized"""
    wizard = TestWizard()
    qtbot.addWidget(wizard)

    # Navigate to third page (uses default buttons)
    wizard.restart()
    wizard.next()
    wizard.next()

    # Check that default buttons are visible (Back, Next, Cancel from ABWizardPage default)
    assert wizard.button(QtWidgets.QWizard.WizardButton.BackButton).isVisible()
    assert wizard.button(QtWidgets.QWizard.WizardButton.NextButton).isVisible()
    assert wizard.button(QtWidgets.QWizard.WizardButton.CancelButton).isVisible()

