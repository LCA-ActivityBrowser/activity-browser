from bw2data.method import Method
from PySide2.QtCore import SignalInstance

import activity_browser.controllers as ctrl


class ABMethod(Method):

    def __hash__(self):
        return hash(self.name)

    @property
    def changed(self) -> SignalInstance:
        return ctrl.ic_controller.get_virtual(self, create=True).changed

    @property
    def deleted(self) -> SignalInstance:
        return ctrl.ic_controller.get_virtual(self, create=True).deleted

    def write(self, data, process=True):
        super().write(data, process)

        ctrl.ic_controller.changed(self)
        ctrl.ic_controller.sync()

    def copy(self, name=None) -> "ABMethod":
        new_method = super().copy(name)

        ctrl.ic_controller.sync()

        return new_method

    def deregister(self):
        super().deregister()

        ctrl.ic_controller.changed(self)
        ctrl.ic_controller.deleted(self)
        ctrl.ic_controller.sync()

    # extending Brightway Functionality

    def load_dict(self) -> dict:
        return {cf[0]: cf[1] for cf in self.load()}

    def write_dict(self, data: dict, process=True):
        self.write(list(data.items()), process)
