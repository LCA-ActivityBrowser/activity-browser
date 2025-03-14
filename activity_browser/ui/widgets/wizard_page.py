from typing import TYPE_CHECKING
from qtpy import QtWidgets

if TYPE_CHECKING:
    from activity_browser.ui.widgets import ABWizard
    from activity_browser.ui.threading import ABThread


class ABWizardPage(QtWidgets.QWizardPage):
    title: str = ""
    subtitle: str = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(self.title)
        self.setSubTitle(self.subtitle)

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


class ABThreadedWizardPage(ABWizardPage):
    Thread: type["ABThread"]

    def __init__(self, parent=None):
        from activity_browser import application

        super().__init__(parent)

        self.thread = self.Thread(application)
        self.thread.finished.connect(self.completeChanged)
        self.thread.finished.connect(lambda: self.statusUpdate(100, "Complete"))
        self.thread.status.connect(self.statusUpdate)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, 0)
        self.message = QtWidgets.QLabel(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.message)

        self.setLayout(layout)

    def statusUpdate(self, progress: int, message: str):
        self.message.setText(message)

        if progress == -1:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress)


    def isComplete(self):
        """Check if the download thread has finished"""
        return self.thread.isFinished()

