from enum import Enum
from math import isnan, nan
from pytest import mark
from pytestqt.qtbot import QtBot
from qtpy import QtCore

from activity_browser.ui.widgets.property_editor import PropertyEditor
from activity_browser.ui.style import style_item


class RowState(Enum):
    NORMAL = 0
    MODIFIED = 1
    NEW = 2
    DELETED = 3 
    DUPLICATED = 4
    LAST = 5

STATE_COLORS = {
    RowState.NORMAL: None,
    RowState.MODIFIED: style_item.brushes.get("modified"),
    RowState.NEW: style_item.brushes.get("new"),
    RowState.DELETED: style_item.brushes.get("deleted"),
    RowState.DUPLICATED: style_item.brushes.get("duplicate"),
    RowState.LAST: style_item.brushes.get("deleted"),
}

def _check_row(ped: PropertyEditor, read_only: bool, row: int, key: str, value: float, state: RowState):
    key_idx = ped._editor_table.model().index(row, 0) # Key
    val_idx = ped._editor_table.model().index(row, 1) # Value
    del_idx = ped._editor_table.model().index(row, 2) # Delete button
    # check values
    assert ped._editor_table.model().data(key_idx) == key
    if isnan(value):
        assert isnan(ped._editor_table.model().data(val_idx))
    else:
        assert ped._editor_table.model().data(val_idx) == value
    # check the delete button
    assert del_idx.isValid() == (not read_only)
    if del_idx.isValid():
        assert ped._editor_table.isPersistentEditorOpen(del_idx) == (state != RowState.LAST)
    # check deleted strikthrough
    font_key = ped._editor_table.model().data(key_idx, QtCore.Qt.ItemDataRole.FontRole)
    font_val = ped._editor_table.model().data(val_idx, QtCore.Qt.ItemDataRole.FontRole)
    if state == RowState.DELETED or key == "":
        assert font_key.strikeOut()
        assert font_val.strikeOut()
    # check colors
    key_color = ped._editor_table.model().data(key_idx, QtCore.Qt.ItemDataRole.ForegroundRole)
    val_color = ped._editor_table.model().data(val_idx, QtCore.Qt.ItemDataRole.ForegroundRole)
    if key != "":
        assert key_color == val_color == STATE_COLORS[state]
    else:
        assert key_color == val_color == STATE_COLORS[RowState.DELETED]
   

def _check_last_row(ped: PropertyEditor, read_only: bool) -> bool:
    last_row = ped._editor_table.model().rowCount() - 1
    _check_row(ped, read_only, last_row, "", nan, RowState.LAST)

def _check_values(ped: PropertyEditor, read_only: bool, rows: list[tuple[str, float]], 
                  state: list[RowState]):
    assert len(rows) == len(state)
    assert ped._editor_table.model().rowCount() == len(rows) + 1
    for i in range(len(rows)):
        _check_row(ped, read_only, i, rows[i][0], rows[i][1], state[i])

@mark.parametrize("read_only", [(True,), (False,)])
def test_show_empty(qtbot: QtBot, read_only: bool):
    ped = PropertyEditor({}, read_only)
    qtbot.add_widget(ped)
    ped.show()
    if read_only:
        assert ped._message_label.text() == PropertyEditor.MESSAGE_READ_ONLY
    else:
        assert ped._message_label.text() == PropertyEditor.MESSAGE_NO_CHANGES_YET
    assert ped._editor_table.model().rowCount() == 1

    assert ped._save_button.isEnabled() == False
    assert ped._cancel_button.isEnabled() == True
    _check_last_row(ped, read_only)

@mark.parametrize("values, read_only", [
    ({"one": 1, "two": 2.2, "three": 3.331}, True), 
    ({"one": 1, "two": 2.2, "three": 3.331}, False)
    ])
def test_show_with_values(qtbot: QtBot, values: dict[str, float], read_only: bool):
    ped = PropertyEditor(values, read_only)
    qtbot.add_widget(ped)
    ped.show()
    if read_only:
        assert ped._message_label.text() == PropertyEditor.MESSAGE_READ_ONLY
    else:
        assert ped._message_label.text() == PropertyEditor.MESSAGE_NO_CHANGES_YET

    assert ped._editor_table.model().rowCount() == len(values) + 1
    _check_values(ped, read_only, list(values.items()), [RowState.NORMAL, RowState.NORMAL, RowState.NORMAL])

    assert ped._save_button.isEnabled() == False
    assert ped._cancel_button.isEnabled() == True
    _check_last_row(ped, read_only)

def test_delete(qtbot: QtBot):
    ped = PropertyEditor({"one": 1, "two": 2.2, "three": 3.331}, read_only = False)
    table = ped._editor_table
    qtbot.add_widget(ped)
    ped.show()
    # Can not click on the delete button using QtBot, as the clicks are received 
    # by the viewport
    # Delete one item
    two_btn_idx = table.model().index(1, 2)
    table._model.handle_delete_request(two_btn_idx)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331)], 
                  [RowState.NORMAL, RowState.DELETED, RowState.NORMAL])
    assert ped.properties() == {"one": 1, "three": 3.331}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

    # Delete one more item
    one_btn_idx = table.model().index(0, 2)
    table._model.handle_delete_request(one_btn_idx)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331)], 
                  [RowState.DELETED, RowState.DELETED, RowState.NORMAL])
    assert ped.properties() == {"three": 3.331}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

    # Delete the last item
    three_btn_idx = table.model().index(2, 2)
    table._model.handle_delete_request(three_btn_idx)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331)], 
                  [RowState.DELETED, RowState.DELETED, RowState.DELETED])
    assert ped.properties() == {}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

    # Undelete one item
    two_btn_idx = table.model().index(1, 2)
    table._model.handle_delete_request(two_btn_idx)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331)], 
                  [RowState.DELETED, RowState.NORMAL, RowState.DELETED])
    assert ped.properties() == {"two": 2.2}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

def test_modify(qtbot: QtBot):
    ped = PropertyEditor({"one": 1, "two": 2.2, "three": 3.331}, read_only = False)
    table = ped._editor_table
    qtbot.add_widget(ped)
    ped.show()
    mod_val_idx = table.model().index(1, 1)
    # Can not do proper UI testing because of the delegates
    table._model.setData(mod_val_idx, 5.7, QtCore.Qt.ItemDataRole.EditRole)
    _check_values(ped, False, [("one", 1), ("two", 5.7), ("three", 3.331)], 
                  [RowState.NORMAL, RowState.MODIFIED, RowState.NORMAL])
    assert ped.properties() == {"one": 1, "two": 5.7, "three": 3.331}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

def test_new(qtbot: QtBot):
    ped = PropertyEditor({"one": 1, "two": 2.2, "three": 3.331}, read_only = False)
    table = ped._editor_table
    qtbot.add_widget(ped)
    ped.show()
    new_key_idx = table.model().index(3, 0)
    # Can not do proper UI testing because of the delegates
    table._model.setData(new_key_idx, "new", QtCore.Qt.ItemDataRole.EditRole)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331), ("new", 0)], 
                  [RowState.NORMAL, RowState.NORMAL, RowState.NORMAL, RowState.NEW])
    assert ped.properties() == {"one": 1, "two": 2.2, "three": 3.331, "new": 0,}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

    new_val_idx = table.model().index(3, 1)
    table._model.setData(new_val_idx, 5.2, QtCore.Qt.ItemDataRole.EditRole)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331), ("new", 5.2)], 
                  [RowState.NORMAL, RowState.NORMAL, RowState.NORMAL, RowState.NEW])
    assert ped.properties() == {"one": 1, "two": 2.2, "three": 3.331, "new": 5.2,}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

def test_duplicates(qtbot: QtBot):
    ped = PropertyEditor({"one": 1, "two": 2.2, "three": 3.331}, read_only = False)
    table = ped._editor_table
    qtbot.add_widget(ped)
    ped.show()
    new_key_idx = table.model().index(3, 0)
    # Can not do proper UI testing because of the delegates
    # Create one duplicate
    table._model.setData(new_key_idx, "one", QtCore.Qt.ItemDataRole.EditRole)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331), ("one", 0)], 
                  [RowState.DUPLICATED, RowState.NORMAL, RowState.NORMAL, RowState.DUPLICATED])
    assert ped.properties() == {"one": 0, "two": 2.2, "three": 3.331}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_DUPLICATES
    assert ped._save_button.isEnabled() == False
    # Create one more duplicate
    two_key_idx = table.model().index(1, 0)
    table._model.setData(two_key_idx, "one", QtCore.Qt.ItemDataRole.EditRole)
    _check_values(ped, False, [("one", 1), ("one", 2.2), ("three", 3.331), ("one", 0)], 
                  [RowState.DUPLICATED, RowState.DUPLICATED, RowState.NORMAL, RowState.DUPLICATED])
    assert ped.properties() == {"one": 0, "three": 3.331, }
    assert ped._message_label.text() == PropertyEditor.MESSAGE_DUPLICATES
    assert ped._save_button.isEnabled() == False
    # Delete two duplicates
    one_btn_idx = table.model().index(0, 2)
    table._model.handle_delete_request(one_btn_idx)
    new_btn_idx = table.model().index(3, 2)
    table._model.handle_delete_request(new_btn_idx)
    _check_values(ped, False, [("one", 1), ("one", 2.2), ("three", 3.331), ("one", 0)], 
                  [RowState.DELETED, RowState.MODIFIED, RowState.NORMAL, RowState.DELETED])
    assert ped.properties() == {"one": 2.2, "three": 3.331, }
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True

def test_read_only_no_edit(qtbot: QtBot):
    ped = PropertyEditor({"one": 1, "two": 2.2, "three": 3.331}, read_only = True)
    table = ped._editor_table
    qtbot.add_widget(ped)
    ped.show()

    # Can not do proper UI testing because of the delegates
    # The model itself is editable, but the UI is not

    two_key_idx = table.model().index(1, 0)
    assert table._model.flags(two_key_idx) & QtCore.Qt.ItemFlag.ItemIsEditable == 0

    three_val_idx = table.model().index(2, 1)
    assert table._model.flags(three_val_idx) & QtCore.Qt.ItemFlag.ItemIsEditable == 0

    assert ped._message_label.text() == PropertyEditor.MESSAGE_READ_ONLY
    assert ped._save_button.isEnabled() == False

def test_modify_undo(qtbot: QtBot):
    ped = PropertyEditor({"one": 1, "two": 2.2, "three": 3.331}, read_only = False)
    table = ped._editor_table
    qtbot.add_widget(ped)
    ped.show()
    assert ped._message_label.text() == PropertyEditor.MESSAGE_NO_CHANGES_YET
    # Can not do proper UI testing because of the delegates
    # Modify a value
    mod_val_idx = table.model().index(1, 1)
    table._model.setData(mod_val_idx, 5.7, QtCore.Qt.ItemDataRole.EditRole)
    _check_values(ped, False, [("one", 1), ("two", 5.7), ("three", 3.331)], 
                  [RowState.NORMAL, RowState.MODIFIED, RowState.NORMAL])
    assert ped.properties() == {"one": 1, "two": 5.7, "three": 3.331}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_MODIFIED
    assert ped._save_button.isEnabled() == True
    # Undo the change
    table._model.setData(mod_val_idx, 2.2, QtCore.Qt.ItemDataRole.EditRole)
    _check_values(ped, False, [("one", 1), ("two", 2.2), ("three", 3.331)], 
                  [RowState.NORMAL, RowState.NORMAL, RowState.NORMAL])
    assert ped.properties() == {"one": 1, "two": 2.2, "three": 3.331}
    assert ped._message_label.text() == PropertyEditor.MESSAGE_NO_CHANGES
    assert ped._save_button.isEnabled() == False
