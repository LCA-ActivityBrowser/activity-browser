from typing import TYPE_CHECKING, Literal
from qtpy import QtWidgets, QtCore

if TYPE_CHECKING:
    from activity_browser.ui.widgets import ABWizardPage


ABWizardButtonLayout = list[Literal[
    "Stretch",
    "BackButton",
    "NextButton",
    "CancelButton",
    "FinishButton",
    "HelpButton",
    "CommitButton",
]]

class ABWizard(QtWidgets.QWizard):
    pages = []
    context = {}
    defaultButtonLayout: ABWizardButtonLayout = ["Stretch", "BackButton", "NextButton", "CancelButton"]
    finalButtonLayout: ABWizardButtonLayout = ["Stretch", "FinishButton"]

    def __init__(self, *args, title: str = None, context: dict = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self.setWindowFlags(
            QtCore.Qt.WindowType.Sheet |
            QtCore.Qt.WindowType.CustomizeWindowHint |
            QtCore.Qt.WindowType.WindowTitleHint
        )

        if title:
            self.setWindowTitle(title)

        for page in self.pages:
            self.addPage(page(self))

        self.context = context or {}

    def page(self, page_id: int) -> "ABWizardPage":
        return super().page(page_id)

    def initializePage(self, page_id):

        # finalize the previous page if it exists
        if self.visitedIds():
            previous_page_id = self.visitedIds()[-1]
            previous_page = self.page(previous_page_id)
            previous_page.finalize(self.context)

        # initialize the next page
        page = self.page(page_id)
        page.initializePage(self.context)
        if page.buttonLayout:
            if "CommitButton" in page.buttonLayout:
                page.setCommitPage(True)
            if "FinishButton" in page.buttonLayout:
                page.setFinalPage(True)
            self.setButtonLayout(page.buttonLayout)
        elif self.currentId() == self.pageIds()[-1]:
            self.setButtonLayout(self.finalButtonLayout)
        else:
            self.setButtonLayout(self.defaultButtonLayout)

    def setButtonLayout(self, layout: ABWizardButtonLayout):
            button_map = {
                "Stretch": QtWidgets.QWizard.WizardButton.Stretch,
                "BackButton": QtWidgets.QWizard.WizardButton.BackButton,
                "NextButton": QtWidgets.QWizard.WizardButton.NextButton,
                "CancelButton": QtWidgets.QWizard.WizardButton.CancelButton,
                "FinishButton": QtWidgets.QWizard.WizardButton.FinishButton,
                "HelpButton": QtWidgets.QWizard.WizardButton.HelpButton,
                "CommitButton": QtWidgets.QWizard.WizardButton.CommitButton,
            }
            qt_layout = [button_map[item] for item in layout]
            super().setButtonLayout(qt_layout)

            default_button = "NextButton"
            default_button = "FinishButton" if "FinishButton" in layout else default_button
            default_button = "CommitButton" if "CommitButton" in layout else default_button

            # Set the default button after a short delay to ensure the UI is updated
            def set_default():
                button = self.button(button_map[default_button])
                button.setFocus()

            QtCore.QTimer.singleShot(50, set_default)

