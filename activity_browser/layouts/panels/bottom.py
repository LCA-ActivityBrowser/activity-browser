
from .panel import ABTab
from ..tabs import DebugTab


class BottomPanel(ABTab):
    side = "bottom"

    def __init__(self, *args):
        super(BottomPanel, self).__init__(*args)

        self.tabs = {
            "Debug": DebugTab(self)
        }
        for tab_name, tab in self.tabs.items():
            self.addTab(tab, tab_name)

        self.setVisible(False)

    def show_debug_window(self, toggle: bool = False):
        self.setVisible(toggle)
        self.tabs["Debug"].setVisible(toggle)
