import pandas as pd
from qtpy import QtGui, QtCore


class ABAbstractItem:

    def __init__(self, key, parent=None):
        self._key = key
        self._child_keys = []
        self._child_items = {}
        self._parent = None

        if parent:
            self.set_parent(parent)

    def __getitem__(self, item):
        raise NotImplementedError

    def parent(self) -> "ABAbstractItem":
        return self._parent

    def key(self):
        return self._key

    def children(self):
        return self._child_items

    def path(self) -> [str]:
        return self.parent().path() + [self.key()] if self.parent() else []

    def rank(self) -> int:
        """Return the rank of the ABItem within the parent. Returns -1 if there is no parent."""
        if self.parent is None:
            return -1
        return self.parent()._child_keys.index(self.key())

    def has_children(self) -> bool:
        return bool(self._child_keys)

    def set_parent(self, parent: "ABAbstractItem"):
        if self.key() in parent.children():
            raise KeyError(f"Item {self.key()} is already a child of {parent.key()}")

        if self.parent():
            self.parent()._child_keys.remove(self.key())
            del self.parent()._child_items[self.key()]

        parent._child_items[self.key()] = self
        parent._child_keys.append(self.key())
        self._parent = parent

    def loc(self, key_or_path: object | list[object], default=None):
        key = key_or_path.pop(0) if isinstance(key_or_path, list) else key_or_path

        if isinstance(key_or_path, list) and len(key_or_path) > 0:
            return self._child_items[key].loc(key_or_path, default)

        return self._child_items.get(key, default)

    def iloc(self, index: int, default=None):
        return self.loc(self._child_keys[index], default)

    def displayData(self, col: int, key: str):
        return None

    def decorationData(self, col: int, key: str):
        return None

    def fontData(self, col: int, key: str):
        return None

    def backgroundData(self, col: int, key: str):
        return None

    def foregroundData(self, col: int, key: str):
        return None

    def flags(self, col: int, key: str):
        return QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable

    def setData(self, col: int, key: str, value):
        return False


class ABBranchItem(ABAbstractItem):

    def __getitem__(self, item):
        return None

    def put(self, item: ABAbstractItem, path):
        key = path.pop(0)
        if path:
            sub = self.loc(key)
            sub = sub if sub else self.__class__(key, self)
            sub.put(item, path)
        else:
            item.set_parent(self)

    def set_parent(self, parent: "ABAbstractItem"):
        if self.key() in parent._child_items:
            twin = parent.loc(self.key())
            for child in twin.child_items.values():
                child.set_parent(self)

        if self.parent():
            self.parent()._child_keys.remove(self.key())
            del self.parent()._child_items[self.key()]

        parent._child_items[self.key()] = self

        branches = [isinstance(parent._child_items[key], ABBranchItem) for key in parent._child_keys]
        i = branches.index(False) if False in branches else len(branches)
        parent._child_keys.insert(i, self.key())
        self._parent = parent

    def displayData(self, col: int, key: str):
        if col == 0:
            return self.key()
        else:
            return None


class ABDataItem(ABAbstractItem):
    def __init__(self, key, data, parent=None):
        super().__init__(key, parent)
        self.data = data

    def __getitem__(self, item):
        return self.data.get(item)

    def displayData(self, col: int, key: str):
        data = self[key]

        if isinstance(data, (list, tuple)):
            # skip isna check for lists/tuples
            pass
        elif data is None or pd.isna(data):
            return None

        if isinstance(data, str):
            # clean up the data to a table-readable format
            data = data.replace("\n", " ")

        return data

    def fontData(self, col: int, key: str):
        font = QtGui.QFont()

        # set the font to italic if the display value is Undefined
        if self.displayData(col, key) == "Undefined":
            font.setItalic(True)

        return font
