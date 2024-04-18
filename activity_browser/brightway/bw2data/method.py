from bw2data.method import *

from ..patching import patch_superclass, patched
from activity_browser.signals import qmethod_list


@patch_superclass
class Method(Method):

    @property
    def changed(self):
        return qmethod_list.get_or_create(self).changed

    @property
    def deleted(self):
        return qmethod_list.get_or_create(self).deleted

    def write(self, data, process=True):
        patched().write(data, process)
        [qmthd.emitLater("changed", self) for qmthd in qmethod_list if qmthd["name"] == self.name]

    def deregister(self):
        patched().deregister()

        [qmthd.emitLater("deleted", self) for qmthd in qmethod_list if qmthd["name"] == self.name]
        [qmthd.emitLater("changed", self) for qmthd in qmethod_list if qmthd["name"] == self.name]


    # extending Brightway Functionality
    def load_dict(self) -> dict:
        return {cf[0]: cf[1] for cf in self.load()}

    def write_dict(self, data: dict, process=True):
        self.write(list(data.items()), process)

