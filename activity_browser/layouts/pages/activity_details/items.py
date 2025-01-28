from qtpy import QtGui
from qtpy.QtCore import Qt

from activity_browser.ui.widgets import ABDataItem
from activity_browser.ui import icons


class ExchangeItem(ABDataItem):
    @property
    def exchange(self):
        return self["_exchange"]

    @property
    def functional(self):
        return self["Exchange Type"] == "production"

    def flags(self, col: int, key: str):
        from .views import ExchangeView

        flags = super().flags(col, key)
        if key in ExchangeView.column_delegates:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key.startswith("Property: "):
            return flags | Qt.ItemFlag.ItemIsEditable
        return flags

    def displayData(self, col: int, key: str):
        if key == "Allocation Factor" and not self.functional:
            return None

        if key.startswith("Property: "):
            if not self.functional:
                return ()
            if not isinstance(self[key], list):
                return ("Undefined", )

            prop = self[key][0]

            amount = prop.get("amount")
            unit = prop.get("unit")
            norm = f" / {self.exchange.input["unit"]}" if prop.get("normalize") else ""
            return (amount, unit, norm, )
        return super().displayData(col, key)

    def decorationData(self, col, key):
        if key != "Name":
            return

        if self["Activity Type"] in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        if self["Activity Type"] in ["product", "processwithreferenceproduct"]:
            return icons.qicons.product
        if self["Activity Type"] == "waste":
            return icons.qicons.waste

    def fontData(self, col: int, key: str):
        font = super().fontData(col, key)

        # set the font to bold if it's a production/functional exchange
        if self.functional:
            font.setBold(True)
        return font

    def backgroundData(self, col: int, key: str):
        if key == f"Property: {self['_allocate_by']}":
            return QtGui.QBrush(Qt.GlobalColor.lightGray)

    def setData(self, col: int, key: str, value) -> bool:
        if key in ["Amount"]:
            actions.ExchangeModify.run(self.exchange, {"amount": value})
            return True

        if key in ["Unit", "Name", "Location"]:
            act = self.exchange.input

            actions.ActivityModify.run(act.key, key.lower(), value)

        if key.startswith("Property: "):
            act = self.exchange.input
            prop_key = key[10:]
            props = act["properties"]
            props[prop_key].update({"amount": value})

            actions.ActivityModify.run(act.key, "properties", props)

        return False
