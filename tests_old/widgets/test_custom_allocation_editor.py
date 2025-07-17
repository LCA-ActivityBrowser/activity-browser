from typing import Union
from unittest.mock import patch
from uuid import uuid4
from pytestqt.qtbot import QtBot
from pytest import fixture, mark
from qtpy.QtCore import Qt

from activity_browser.ui.widgets.custom_allocation_editor import CustomAllocationEditor
from activity_browser.mod import bw2data as bd
from bw_functional import allocation_strategies
from bw_functional.custom_allocation import MessageType, PropertyMessage

TEST_PROPERTIES =[
            ("prop1", MessageType.ALL_VALID),
            ("second prop", MessageType.NONNUMERIC_PROPERTY),
            ("prop3", MessageType.MISSING_PROPERTY),
            ("mass", MessageType.ALL_VALID),
            ("fifth prop", MessageType.NONNUMERIC_PROPERTY),
            ("prop5", MessageType.MISSING_PROPERTY)
        ]

PROPERTY_CHECK_VALUE1 = [
    PropertyMessage(1, 1, 1, MessageType.ALL_VALID, "Very good property")
]

PROPERTY_CHECK_VALUE2 = [
    PropertyMessage(1, 1, 1, MessageType.MISSING_PROPERTY, "One missing property"),
    PropertyMessage(1, 1, 1, MessageType.NONNUMERIC_PROPERTY, "One bad property"),
    PropertyMessage(1, 1, 1, MessageType.MISSING_PROPERTY, "Other missing")
]

PROPERTY_CHECK_VALUE3 = True
#
#
# def test_fill_empty(qtbot: QtBot):
#     # Test the startup with empty property list
#     with patch("activity_browser.ui.widgets.custom_allocation_editor.list_available_properties") as mock_list_prop:
#         mock_list_prop.return_value = []
#         ed = CustomAllocationEditor("", "test_db")
#         qtbot.add_widget(ed)
#         ed.show()
#
#         assert ed._property_table.rowCount() == 0
#         assert ed._save_button.isEnabled() == False
#
# def _check_property_list(ed: CustomAllocationEditor,
#                          properties: list[tuple[str, MessageType]]):
#     sorted_props = sorted(properties)
#     for i in range(ed._property_table.rowCount()):
#         assert (ed._property_table.item(i, 0).data(Qt.ItemDataRole.DisplayRole)
#                     == sorted_props[i][0])
#         assert (ed._property_table.item(i, 1).data(Qt.ItemDataRole.DisplayRole)
#                     == sorted_props[i][1].value)
#
# @mark.parametrize("old_value, check_value", [
#     ("", []),
#     ("prop3", PROPERTY_CHECK_VALUE1)
#     ])
# def test_fill_for_db(qtbot: QtBot, old_value: str, check_value: list[PropertyMessage]):
#     # Test the filling of the table for a database
#     with (patch("activity_browser.ui.widgets.custom_allocation_editor.list_available_properties") as mock_list_prop,
#           patch("activity_browser.ui.widgets.custom_allocation_editor.check_property_for_allocation") as mock_check
#           ):
#         mock_list_prop.return_value = TEST_PROPERTIES
#         mock_check.return_value = PROPERTY_CHECK_VALUE1
#         ed = CustomAllocationEditor(old_value, "test_db")
#         qtbot.add_widget(ed)
#         ed.show()
#
#         mock_list_prop.assert_called_with("test_db", None)
#         assert ed._property_table.rowCount() == len(TEST_PROPERTIES)
#         assert ed._save_button.isEnabled() == (old_value != "")
#         if old_value != "":
#             mock_check.assert_called_with("test_db", old_value)
#             for prop_message in check_value:
#                 assert prop_message.message in ed._status_text.toPlainText()
#         else:
#             assert ed._status_text.toPlainText() == ""
#             mock_check.assert_not_called()
#         assert ed.selected_property() == old_value
#         _check_property_list(ed, TEST_PROPERTIES)
#
# @fixture
# def new_db(bw2test):
#     db = bd.Database("test_db")
#     db.register()
#     return db
#
# @fixture
# def new_act(new_db):
#     data = {
#         "name": "new act",
#         "unit": "unit",
#         "type": "process",
#     }
#     act = new_db.new_activity(code=uuid4().hex, **data)
#     act.save()
#     return act
#
# @mark.parametrize("old_value, check_value", [
#     ("", []),
#     ("prop3", PROPERTY_CHECK_VALUE1)
#     ])
# def test_fill_for_process(qtbot, new_act,
#             old_value: str, check_value: list[PropertyMessage]):
#     # Test the filling of the table for a specific activity
#     with (patch("activity_browser.ui.widgets.custom_allocation_editor.list_available_properties") as mock_list_prop,
#           patch("activity_browser.ui.widgets.custom_allocation_editor.check_property_for_process_allocation") as mock_check
#           ):
#         mock_list_prop.return_value = TEST_PROPERTIES
#         mock_check.return_value = PROPERTY_CHECK_VALUE1
#         ed = CustomAllocationEditor(old_value, new_act)
#         qtbot.add_widget(ed)
#         ed.show()
#         mock_list_prop.assert_called_with("test_db", new_act)
#         assert ed._property_table.rowCount() == len(TEST_PROPERTIES)
#         assert ed._save_button.isEnabled() == (old_value != "")
#         if old_value != "":
#             mock_check.assert_called_with(new_act, old_value)
#             for prop_message in check_value:
#                 assert prop_message.message in ed._status_text.toPlainText()
#         else:
#             assert ed._status_text.toPlainText() == ""
#             mock_check.assert_not_called()
#         assert ed.selected_property() == old_value
#         _check_property_list(ed, TEST_PROPERTIES)
#
# @mark.parametrize("old_value, check_old, click_row, check_new", [
#     ("", [], 4, PROPERTY_CHECK_VALUE2),
#     ("prop3", PROPERTY_CHECK_VALUE1, 5, PROPERTY_CHECK_VALUE3)
#     ])
# def test_click_property(qtbot: QtBot,
#                          old_value: str, check_old: list[PropertyMessage],
#                          click_row: int, check_new: Union[bool, list[PropertyMessage]]):
#     # Test that clicking a property updates the status text with the detailed analyses
#     # of the respective property
#     with (patch("activity_browser.ui.widgets.custom_allocation_editor.list_available_properties") as mock_list_prop,
#           patch("activity_browser.ui.widgets.custom_allocation_editor.check_property_for_allocation") as mock_check
#           ):
#         mock_list_prop.return_value = TEST_PROPERTIES
#         mock_check.return_value = check_old
#         ed = CustomAllocationEditor(old_value, "test_db")
#         qtbot.add_widget(ed)
#         ed.show()
#
#         mock_check.return_value = check_new
#         click_index = ed._property_table.model().index(click_row, 0)
#         assert click_index.isValid()
#         item_rect = ed._property_table.visualRect(click_index)
#         qtbot.mouseClick(ed._property_table.viewport(), Qt.MouseButton.LeftButton, pos = item_rect.center())
#
#         sorted_properties = sorted(TEST_PROPERTIES)
#         assert ed._get_current_property() == sorted_properties[click_row][0]
#         mock_check.assert_called_with("test_db", sorted_properties[click_row][0])
#         if isinstance(check_new, bool):
#             assert ed._status_text.toPlainText() == "All good!"
#         else:
#             for prop_message in check_new:
#                 assert prop_message.message in ed._status_text.toPlainText()
#
# @mark.parametrize("old_value, click_rows, cancel", [
#     ("", [2, 4], False),
#     ("prop3", [3, 1], False), # Make sure that 'mass' (index 1 after sort) is also selected once
#     ("", [0, 5], True),
#     ("prop3", [2, 2], True),
#     ("", [], False), # No clicks, no previous selection
#     ("prop3", [], False), # No clicks, only selection
#     ])
# def test_select_property(qtbot: QtBot, old_value: str, click_rows: list[int], cancel: bool):
#     # Test the saving of the selected property
#     with (patch("activity_browser.ui.widgets.custom_allocation_editor.list_available_properties") as mock_list_prop,
#           patch("activity_browser.ui.widgets.custom_allocation_editor.check_property_for_allocation") as mock_check,
#           patch("activity_browser.ui.widgets.custom_allocation_editor.add_custom_property_allocation_to_project") as mock_add_alloc
#           ):
#         mock_list_prop.return_value = TEST_PROPERTIES
#         mock_check.return_value = []
#         ed = CustomAllocationEditor(old_value, "test_db")
#         qtbot.add_widget(ed)
#         ed.show()
#
#         sorted_properties = sorted(TEST_PROPERTIES)
#
#         # Click a couple of rows
#         for row in click_rows:
#             click_index = ed._property_table.model().index(row, 0)
#             assert click_index.isValid()
#             item_rect = ed._property_table.visualRect(click_index)
#             qtbot.mouseClick(ed._property_table.viewport(), Qt.MouseButton.LeftButton, pos = item_rect.center())
#
#             assert ed._get_current_property() == sorted_properties[row][0]
#
#         if cancel:
#             # If the dialog is cancelled, it should return the old value
#             qtbot.mouseClick(ed._cancel_button, Qt.MouseButton.LeftButton)
#             assert ed.selected_property() == old_value
#             mock_add_alloc.assert_not_called()
#         else:
#             qtbot.mouseClick(ed._save_button, Qt.MouseButton.LeftButton)
#             selected = sorted_properties[click_rows[-1]][0] if click_rows else old_value
#             # If there is anything selected
#             if selected:
#                 assert not ed.isVisible()
#                 # If the dialog is closed with select, it should return the new value
#                 already_defined = selected in allocation_strategies
#                 assert ed.selected_property() == selected
#                 if already_defined:
#                     # add_custom_property_allocation_to_project should not be called for
#                     # existing properties
#                     mock_add_alloc.assert_not_called()
#                 else:
#                     mock_add_alloc.assert_called_with(selected)
#             else:
#                 # No selection, dialog should be still open
#                 assert ed.isVisible()
