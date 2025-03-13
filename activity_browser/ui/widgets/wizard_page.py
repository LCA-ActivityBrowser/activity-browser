from typing import TYPE_CHECKING
from qtpy import QtWidgets

if TYPE_CHECKING:
    from activity_browser.ui.widgets import ABWizard


class ABWizardPage(QtWidgets.QWizardPage):
    def wizard(self) -> "ABWizard":
        return super().wizard()

    def nextPage(self) -> type[QtWidgets.QWizardPage] | None:
        i = self.wizard().currentId() + 1
        if i > len(self.wizard().pages) - 1:
            return None
        return self.wizard().pages[i]

    def nextId(self):
        next_page = self.nextPage()
        if next_page is None:
            return -1
        return self.wizard().pages.index(next_page)

    def initializePage(self, context: dict):
        pass

    def finalize(self, context: dict):
        pass
