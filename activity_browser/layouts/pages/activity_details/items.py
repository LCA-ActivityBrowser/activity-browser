import pandas as pd
from qtpy import QtGui
from qtpy.QtCore import Qt

import bw2data as bd

from activity_browser import actions, bwutils
from activity_browser.ui.widgets import ABDataItem
from activity_browser.ui import icons





class ConsumersItem(ABDataItem):
    def decorationData(self, col, key):
        if key not in ["producer", "consumer"]:
            return

        if key == "producer":
            activity_type = self["_producer_type"]
        else:  # key is "consumer"
            activity_type = self["_consumer_type"]

        if activity_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        if activity_type == "processwithreferenceproduct":
            return icons.qicons.processproduct
        if activity_type == "product":
            return icons.qicons.product
        if activity_type in ["process", "multifunctional", "nonfunctional"]:
            return icons.qicons.process
        if activity_type == "waste":
            return icons.qicons.waste

