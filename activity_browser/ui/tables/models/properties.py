# -*- coding: utf-8 -*-
from copy import copy
from dataclasses import dataclass
from math import nan
from numbers import Number
from typing import Any, Optional, Union
from logging import getLogger

from qtpy import QtCore, QtGui

from activity_browser.ui.style import style_item

log = getLogger(__name__)


class PropertyModel(QtCore.QAbstractTableModel):
    """
    Model for the property editor table
    The data is (str, float, bool):
        - property key
        - property value
        - to be deleted - if this flag is set, the property will not be reported in 
            get_properties
    """
    # Reports the property and the offending type and value
    value_error = QtCore.Signal(str, str, str)

    @dataclass
    class PropertyData:
        """Dataclass to represent one row with correct typehints"""
        key: str = ""
        value: float = 0
        to_be_deleted: bool = False

        def __getitem__(self, index: int) -> Union[str, float]:
            """x[k] operator for easier usage"""
            if index == 0:
                return self.key
            elif index == 1:
                return self.value
            raise IndexError

        def __setitem__(self, index: int, value: Union[str, float]):
            """x[k]=v operator for easier usage"""
            if index == 0:
                if not isinstance(value, str):
                    raise TypeError
                self.key = value
            elif index == 1:
                if not isinstance(value, float):
                    raise TypeError
                self.value = value
            else:
                raise IndexError
            
        def __hash__(self) -> int:
            return hash((self.key, self.value))


    def __init__(self, read_only: bool):
        """Model created with the read-only flag will not be editable."""
        super().__init__()
        self._data: list[PropertyModel.PropertyData] = []
        self._original_data: dict[str, float] = {}
        self._read_only = read_only

    def populate(self, data: Optional[dict[str, float]]) -> None:
        """Converts the dict to the internal data format of the model."""
        self._data.clear()
        log.info(f"Input data for property table: {data}")
        if data is not None:
            self._original_data = copy(data)
            for key in data:
                value = data[key]
                if not isinstance(data[key], Number) or isinstance(data[key], bool):
                    self.value_error.emit(key, str(type(value)), str(value))
                    value = 0
                self._data.append(PropertyModel.PropertyData(key, value))
        else:
            self._original_data = dict()
        self._data.append(PropertyModel.PropertyData())
        self.layoutChanged.emit()

    def data(self, index: QtCore.QModelIndex,
             role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
        """
        Implementation of the model.data() interface. Handles EditRole, 

        DisplayRole, ToolTipRole, FontRole, ForegroundRole:
            - rows with empty key are returned as empty
            - items to be deleted are returned with a strikethrough font
            - new items are green, rows with modified values are blue,
            - duplicate key rows are red, deleted rows are gray
        """
        if index.isValid() and index.column() < 2:
            if role == QtCore.Qt.ItemDataRole.EditRole:
                return self._data[index.row()][index.column()]
            elif (role == QtCore.Qt.ItemDataRole.DisplayRole
                    or role == QtCore.Qt.ItemDataRole.ToolTipRole):
                # Show values for properties which have no name as deleted
                # Do not show value for the last row
                if (index.column() == 1 and index.row() == len(self._data) - 1):
                    return nan
                return self._data[index.row()][index.column()]
            elif role == QtCore.Qt.ItemDataRole.FontRole:
                font = QtGui.QFont()
                # Show rows with empty key as deleted ones
                if (self._data[index.row()].to_be_deleted 
                        or self._data[index.row()].key == ""):
                    font.setStrikeOut(True)
                return font
            elif role == QtCore.Qt.ItemDataRole.ForegroundRole:
                current_key = self._data[index.row()].key
                # Show rows with empty key as deleted ones
                if (self._data[index.row()].to_be_deleted 
                        or self._data[index.row()].key == ""):
                    return style_item.brushes.get("deleted")
                elif current_key in self._duplicate_keys():
                    return style_item.brushes.get("duplicate")
                elif self._original_data.get(current_key) == None:
                    return style_item.brushes.get("new")
                elif self._original_data.get(current_key) != self._data[index.row()].value:
                    return style_item.brushes.get("modified")
                return None
        if (index.isValid() and index.column() == 2 
                and (role == QtCore.Qt.ItemDataRole.DisplayRole 
                     or role == QtCore.Qt.ItemDataRole.EditRole)):
            return ""
        return None

    def setData(self, index: QtCore.QModelIndex, value: Any,
             role: int = QtCore.Qt.ItemDataRole.DisplayRole) -> bool:
        """
        Implementation of the model.setData() interface.

        Insert an empty row at the end of the model, if there is no row
        with an empty key at the end.
        """
        if (index.isValid() and role == QtCore.Qt.ItemDataRole.EditRole 
                and index.column() < 2):
            if self._data[index.row()][index.column()] != value:
                self._data[index.row()][index.column()] = value
                self.dataChanged.emit(index, index, [])
            # Make sure there is an empty row at the end
            if self._data[-1][0] != "":
                self.beginInsertRows(QtCore.QModelIndex(), 
                                     len(self._data), 
                                     len(self._data))
                self._data.append(PropertyModel.PropertyData())
                self.endInsertRows()
            return True
        return False

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        """
        Implementation of the model.data() interface. 

        Handles the read-only flag.
        """
        if index.isValid() and index.column() < 2:
            result = (QtCore.Qt.ItemFlag.ItemIsSelectable
                    | QtCore.Qt.ItemFlag.ItemIsEnabled) 
            if not self._read_only:
                result |= QtCore.Qt.ItemFlag.ItemIsEditable
            return result
        # Do not allow editing the last column in the last row
        # Editing it shows the delete button then hides it
        if (index.isValid() and index.row() < len(self._data) - 1 
                and index.column() == 2):
            return (QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsEditable) 
        return QtCore.Qt.ItemFlag.NoItemFlags
    
    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """ Implementation of the model.rowCount() interface. """
        return len(self._data)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        """ Implementation of the model.columnCount() interface. """
        if self._read_only:
            return 2
        return 3

    def headerData(self, section:int, orientation:QtCore.Qt.Orientation,
                   role: int=QtCore.Qt.ItemDataRole.DisplayRole) -> Any:
        """ Implementation of the model.headerData() interface. """
        
        if (section < 3 and 
                orientation == QtCore.Qt.Orientation.Horizontal
                and role == QtCore.Qt.ItemDataRole.DisplayRole):
            return ("Name", "Value", "")[section]
        return None

    def get_properties(self) -> dict[str, float]:
        """
        Returns the result of the property editing.

        Items with an empty key or marked as to be deleted are not reported.
        """
        result = { item.key:item.value for item in self._data 
                        if item.key != "" and not item.to_be_deleted}
        return result

    def _duplicate_keys(self) -> list[str]:
        """Creates a list of the duplicate keys"""
        duplicates:list[str] = []
        key_set: set[str] = set()
        for item in self._data:
            # Do not count the empty keys as duplicates, they will
            # be dropped on export
            if not item.to_be_deleted and item.key != "":            
                if item.key in key_set:
                    duplicates.append(item.key)
                else:
                    key_set.add(item.key)
        return duplicates

    def has_duplicate_key(self) -> bool:
        """Returns True if the model has duplicate keys"""
        return len(self._duplicate_keys()) > 0
    
    def handle_delete_request(self, index: QtCore.QModelIndex):
        """Marks items to be deleted."""
        if index.isValid() and self._data[index.row()].key != "":
            self._data[index.row()].to_be_deleted = not self._data[index.row()].to_be_deleted
            start_index = self.index(index.row(), 0)
            end_index = self.index(index.row(), 1)
            self.dataChanged.emit(start_index, end_index, [])

    def is_modified(self) -> bool:
        return self.get_properties() != self._original_data