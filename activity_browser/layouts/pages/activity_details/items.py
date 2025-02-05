import pandas as pd
from qtpy import QtGui
from qtpy.QtCore import Qt

import pandas as pd

import bw2data as bd

from activity_browser import actions
from activity_browser.ui.widgets import ABDataItem
from activity_browser.ui import icons


class ExchangeItem(ABDataItem):
    background_color = None

    @property
    def exchange(self):
        return self["_exchange"]

    @property
    def functional(self):
        return self["_exchange"].get("type") == "production"

    def flags(self, col: int, key: str):
        flags = super().flags(col, key)
        if key in ["amount", "formula"]:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key in ["unit", "name", "location", "substitution_factor"] and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key.startswith("property_") and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key == "allocation_factor" and self.exchange.output.get("allocation") == "manual" and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable
        return flags

    def displayData(self, col: int, key: str):
        if key in ["allocation_factor", "substitute", "substitution_factor"] and not self.functional:
            return None

        if key.startswith("property_") and not self.functional:
            return None

        if key.startswith("property_") and isinstance(self[key], float):
            return {
                "amount": self[key],
                "unit": "undefined",
                "normalize": False,
            }

        if key.startswith("property_") and self[key]["normalize"]:
            prop = self[key].copy()
            prop["unit"] = prop['unit'] + f" / {self['unit']}"
            return prop

        return super().displayData(col, key)

    def decorationData(self, col, key):
        if key not in ["name", "substitute_name"] or not self.displayData(col, key):
            return

        if key == "name":
            activity_type = self.exchange.input.get("type")
        else:  # key is "substitute_name"
            activity_type = bd.get_node(key=self["_substitute_key"])["type"]

        if activity_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        if activity_type in ["product", "processwithreferenceproduct"]:
            return icons.qicons.product
        if activity_type == "waste":
            return icons.qicons.waste

    def fontData(self, col: int, key: str):
        font = super().fontData(col, key)

        # set the font to bold if it's a production/functional exchange
        if self.functional:
            font.setBold(True)
        return font

    def backgroundData(self, col: int, key: str):
        if self.background_color:
            return QtGui.QBrush(QtGui.QColor(self.background_color))

        if key == f"property_{self['_allocate_by']}":
            return QtGui.QBrush(Qt.GlobalColor.lightGray)

    def setData(self, col: int, key: str, value) -> bool:
        if key in ["amount", "formula"]:
            if key == "formula" and not str(value).strip():
                actions.ExchangeFormulaRemove.run([self.exchange])
                return True

            actions.ExchangeModify.run(self.exchange, {key.lower(): value})
            return True

        if key in ["unit", "name", "location", "substitution_factor", "allocation_factor"]:
            act = self.exchange.input
            actions.ActivityModify.run(act.key, key.lower(), value)

        if key.startswith("property_"):
            act = self.exchange.input
            prop_key = key[9:]
            props = act["properties"]
            props[prop_key].update({"amount": value})

            actions.ActivityModify.run(act.key, "properties", props)

        return False

    def acceptsDragDrop(self, event) -> bool:
        if not self.functional:
            return False

        if not event.mimeData().hasFormat("application/bw-nodekeylist"):
            return False

        keys = set(event.mimeData().retrievePickleData("application/bw-nodekeylist"))
        acts = [bd.get_node(key=key) for key in keys]
        acts = [act for act in acts if act["type"] in ["product", "waste", "processwithreferenceproduct"]]

        if len(acts) != 1:
            return False

        act = acts[0]

        if act["unit"] != self["unit"] or act.key == self.exchange.input.key:
            return False

        return True

    def onDrop(self, event):
        keys = set(event.mimeData().retrievePickleData("application/bw-nodekeylist"))
        acts = [bd.get_node(key=key) for key in keys]
        act = [act for act in acts if act["type"] in ["product", "waste", "processwithreferenceproduct"]][0]
        actions.FunctionSubstitute.run(self.exchange.input, act)
