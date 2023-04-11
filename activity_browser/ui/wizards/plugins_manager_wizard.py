from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Slot

from ...ui.style import header
from ...ui.tables import PluginsTable


class PluginsManagerWizard(QtWidgets.QWizard):

    def __init__(self, key: tuple, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plugins manager")
        self.manager_page = ManagePluginsPage(self)
        self.pages = [self.manager_page]
        for i, page in enumerate(self.pages):
            self.setPage(i, page)

    def accept(self) -> None:
        super().accept()


class ManagePluginsPage(QtWidgets.QWizardPage):

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.wizard = parent
        self.plugins_widget = PluginWidget(self)
        self.complete = False

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.plugins_widget)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        self.setFinalPage(True)

    def initializePage(self):
        self.wizard.setButtonLayout(
            [QtWidgets.QWizard.Stretch, QtWidgets.QWizard.FinishButton]
        )


class PluginWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.table = PluginsTable()

        self._construct_layout()
        self._connect_signals()

    def _connect_signals(self):
        pass

    def _construct_layout(self):
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignLeft)
        header_layout.addWidget(header("Available plugins:"))
        header_widget.setLayout(header_layout)

        # Overall Layout
        layout = QtWidgets.QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(header_widget)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self.table.model.sync()

    def update_widget(self):
        no_plugins = self.table.rowCount() == 0
        self.table.setVisible(not no_plugins)