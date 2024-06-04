from bw2data.method import *

from activity_browser.signals import qmethod_list

from ..patching import patch_superclass, patched


@patch_superclass
class Method(Method):
    @property
    def changed(self):
        """
        Shorthand for connecting to the method QUpdater. Developers can instantiate a Method from bw2data and connect
        directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qmethod_list.get_or_create(self).changed

    @property
    def deleted(self):
        """
        Shorthand for connecting to the method QUpdater. Developers can instantiate a Method from bw2data and connect
        directly, instead of importing the related QUpdater via activity_browser.signals
        """
        return qmethod_list.get_or_create(self).deleted

    def write(self, data, process=True):
        # execute the patched function for standard functionality
        patched[Method]["write"](self, data, process)

        # emit for any corresponding qmethod that exists in qmethod_list (each method that has widgets connected to it)
        [
            qmthd.emitLater("changed", self)
            for qmthd in qmethod_list
            if qmthd["name"] == self.name
        ]

    def deregister(self):
        # execute the patched function for standard functionality
        patched[Method]["deregister"](self)

        # emit for any corresponding qmethod that exists in qmethod_list (each method that has widgets connected to it)
        [
            qmthd.emitLater("deleted", self)
            for qmthd in qmethod_list
            if qmthd["name"] == self.name
        ]
        [
            qmthd.emitLater("changed", self)
            for qmthd in qmethod_list
            if qmthd["name"] == self.name
        ]

    # extending Brightway Functionality
    def load_dict(self) -> dict:
        """
        Extending Brightway functionality by enabling users to get a method dictionary with elementary flow keys as keys
        instead of a list. This makes it easier to find characterization factors.
        """
        return {cf[0]: cf[1] for cf in self.load()}

    def write_dict(self, data: dict, process=True):
        """
        Extending Brightway functionality by enabling users to write a method dictionary with elementary flow keys as
        keys instead of a list. This makes it easier to edit characterization factors.
        """
        self.write(list(data.items()), process)
