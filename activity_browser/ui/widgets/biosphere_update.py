# -*- coding: utf-8 -*-
import brightway2 as bw
from bw2data.errors import ValidityError
from PySide2 import QtCore, QtWidgets
from PySide2.QtCore import Signal, Slot

from ...signals import signals


class BiosphereUpdater(QtWidgets.QProgressDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Updating '{}' database".format(bw.config.biosphere))
        self.setLabelText("Adding new flows to biosphere database")
        self.setRange(0, 0)
        self.show()

        self.thread = UpdateBiosphereThread(self)
        self.setMaximum(self.thread.total_patches)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.finished)
        self.thread.start()

    def finished(self, result: int = None) -> None:
        outcome = result or 0
        self.thread.exit(outcome)
        self.setMaximum(1)
        self.setValue(1)
        signals.database_changed.emit(bw.config.biosphere)
        signals.databases_changed.emit()

    @Slot(int)
    def update_progress(self, current: int):
        self.setValue(current)


class UpdateBiosphereThread(QtCore.QThread):
    data = __import__('bw2io.data')
    PATCHES = [patch for patch in dir(data) if patch.startswith('add_ecoinvent') and patch.endswith('biosphere_flows')]
    progress = Signal(int)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_patches = len(self.PATCHES)

    def run(self):
        try:
            for i, patch in enumerate(self.PATCHES):
                self.progress.emit(i)
                update_bio = getattr(UpdateBiosphereThread.data, patch)
                update_bio()
        except ValidityError as e:
            print("Could not patch biosphere: {}".format(str(e)))
            self.exit(1)
