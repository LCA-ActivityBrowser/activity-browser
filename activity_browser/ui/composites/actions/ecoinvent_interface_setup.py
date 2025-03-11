from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Signal, SignalInstance

from activity_browser.mod.ecoinvent_interface import ABEcoinventRelease
from . import ecoinvent_setup


class EcoinventInterfaceSetupComposite(ecoinvent_setup.EcoinventSetupComposite):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    release: ABEcoinventRelease

    def __init__(self):
        super().__init__()

        # set up the version & model comboboxes
        self.versions = QtWidgets.QComboBox()
        self.models = QtWidgets.QComboBox()

        # insert underneath the name choice
        self.layout().insertWidget(3, QtWidgets.QLabel("Choose ecoinvent version"))
        self.layout().insertWidget(4, self.versions)
        self.layout().insertWidget(5, self.models)

    def load(self, release: ABEcoinventRelease):
        self.release = release
        self.versions.currentTextChanged.connect(self.collect_models)
        self.versions.addItems(self.release.list_versions())

    def get_version(self) -> str:
        return self.versions.currentText()

    def get_model(self) -> str:
        return self.models.currentText()

    def collect_models(self, version: str):
        """Slot for when the version selection changes"""
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.models.clear()
        self.models.addItems(self.release.list_system_models(version))
        QtWidgets.QApplication.restoreOverrideCursor()


