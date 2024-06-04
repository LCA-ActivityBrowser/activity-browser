import bw2io.data as data
from PySide2 import QtWidgets
from PySide2.QtCore import Signal, Slot

from activity_browser import log
from activity_browser.mod import bw2data as bd
from ..threading import ABThread


class BiosphereUpdater(QtWidgets.QProgressDialog):
    def __init__(self, ei_versions, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Updating '{}' database".format(bd.config.biosphere))
        self.setLabelText("Adding new flows to biosphere database")
        self.setRange(0, 0)
        self.show()

        self.thread = UpdateBiosphereThread(ei_versions, self)
        self.setMaximum(self.thread.total_patches)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished.connect(self.thread_finished)
        self.thread.start()

    def thread_finished(self, result: int = None) -> None:
        # outcome = result or 0
        # self.thread.exit(outcome)
        self.setMaximum(1)
        self.setValue(1)
        self.done(result or 0)

    @Slot(int)
    def update_progress(self, current: int):
        self.setValue(current)


class UpdateBiosphereThread(ABThread):
    PATCHES = [patch for patch in dir(data) if patch.startswith('add_ecoinvent') and patch.endswith('biosphere_flows')]
    progress = Signal(int)
    def __init__(self, ei_versions, parent=None):
        super().__init__(parent)

        # reduce the patches list to only compatible versions for this AB version
        self.PATCHES = [p for p in self.PATCHES if any(v.replace('.', '') in p for v in ei_versions)]

        self.total_patches = len(self.PATCHES)

    def run_safely(self):
        try:
            for i, patch in enumerate(self.PATCHES):
                self.progress.emit(i)
                log.debug(f'Applying biosphere patch: {patch}')
                update_bio = getattr(data, patch)
                update_bio()
        except bd.errors.ValidityError as e:
            log.error(f'Could not patch biosphere: {str(e)}')
            self.exit(1)
