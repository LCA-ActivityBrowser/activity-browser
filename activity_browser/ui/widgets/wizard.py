from typing import TYPE_CHECKING
from qtpy import QtWidgets

if TYPE_CHECKING:
    from activity_browser.ui.widgets import ABWizardPage


class ABWizard(QtWidgets.QWizard):
    pages = []

    def __init__(self, *args, title: str = None, context: dict = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)

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
