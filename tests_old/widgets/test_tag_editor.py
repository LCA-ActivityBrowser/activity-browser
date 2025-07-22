from unittest.mock import MagicMock

import pytest
from qtpy import QtWidgets, QtCore, QtGui
from pytestqt.qtbot import QtBot

from activity_browser.ui.delegates import JSONDelegate, ComboBoxDelegate
from activity_browser.ui.tables.tags import TagTable, TagDelegate
from activity_browser.ui.widgets import TagEditor


@pytest.fixture
def tag_table(request, qtbot: QtBot):
    """Fixture for initializing TagTable"""
    tags = {"tag1": "value1", "tag2": "value2"}
    read_only = getattr(request, "param", False)
    tag_table = TagTable(tags, "test_database", read_only=read_only)
    qtbot.addWidget(tag_table)
    return tag_table


@pytest.fixture
def tag_editor(request, qtbot):
    """Fixture for creating the TagEditor dialog"""
    target = {"database": "test_db", "tags": {"tag1": "value1"}}
    read_only = getattr(request, "param", False)
    tag_editor = TagEditor(target=target, read_only=read_only)
    qtbot.addWidget(tag_editor)
    return tag_editor


def test_add_tag(tag_table, qtbot):
    """Test adding a new tag to the model."""
    initial_row_count = tag_table.model.rowCount()

    # Simulate clicking the 'Add Tag' button
    with qtbot.waitSignal(tag_table.model.rowsInserted, timeout=10):
        tag_table.add_tag_button.trigger()

    # Check if the row count has increased
    assert tag_table.model.rowCount() == initial_row_count + 1


def test_remove_tag(tag_table, qtbot):
    """Test removing a tag from the model."""
    initial_row_count = tag_table.model.rowCount()

    # Select the first tag
    index = tag_table.proxy_model.index(0, 0)
    tag_table.setCurrentIndex(index)

    # Simulate clicking the 'Remove Tag' button
    with qtbot.waitSignal(tag_table.model.rowsRemoved, timeout=10):
        tag_table.remove_tag_button.trigger()

    # Check if the row count has decreased
    assert tag_table.model.rowCount() == initial_row_count - 1


@pytest.mark.parametrize(
    "tag_table, read_only, on_element",
    [
        pytest.param(True, True, True, id="read_only on element"),
        pytest.param(True, True, False, id="read_only off element"),
        pytest.param(False, False, True, id="editable on element"),
        pytest.param(False, False, False, id="editable on element"),
    ],
    indirect=["tag_table"],
)
def test_context_menu(tag_table, read_only, on_element, qtbot: QtBot):
    """Test that the context menu is shown and contains the correct actions."""
    index = tag_table.proxy_model.index(0, 0)
    tag_table.setCurrentIndex(index)

    if on_element:
        position = tag_table.visualRect(index).center()
        expected_actions = [tag_table.remove_tag_button, tag_table.add_tag_button]
    else:
        position = tag_table.viewport().rect().center()
        expected_actions = [tag_table.add_tag_button]
    if read_only:
        expected_actions = list(
            filter(lambda x: x is not tag_table.add_tag_button, expected_actions)
        )
    # The context menu is shown using QtWidgets.QMenu.exec_, and this method
    # does not return, so the test gets blocked. Patching it did not work,
    # probably due to the same named static method.
    def hide_menu():
        menu = None
        def check_menu():
            nonlocal menu
            assert (menu := tag_table.findChild(QtWidgets.QMenu)) is not None
        qtbot.waitUntil(check_menu)
        # close the menu before the assertions, as a failing assertion will
        # prevent the menu from closing, thus failing further test execution
        menu.close()
        assert isinstance(menu, QtWidgets.QMenu)
        actions = menu.actions()
        assert set(actions) == set(expected_actions)

    # Use a timer to execute code after the menu is shown
    QtCore.QTimer.singleShot(200, hide_menu)

    # Simulate a right-click to open the context menu
    tag_table.contextMenuEvent(
        QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse, position)
    )

    # Checks are done in the hide_menu, which will block until the menu
    # is created


def test_update_proxy_model(tag_table):
    """Test if the proxy model is set up and sorting works."""
    tag_table.update_proxy_model()

    assert isinstance(tag_table.proxy_model, QtCore.QSortFilterProxyModel)

    # Check sorting by the first column
    tag_table.sortByColumn(0, QtCore.Qt.AscendingOrder)
    first_tag = tag_table.proxy_model.index(0, 0).data()
    assert first_tag == "tag1"

    tag_table.sortByColumn(0, QtCore.Qt.DescendingOrder)
    first_tag = tag_table.proxy_model.index(0, 0).data()
    assert first_tag == "tag2"


@pytest.mark.parametrize(
    "tag_table",
    [
        pytest.param(False, id="editable"),
        pytest.param(True, id="read_only"),
    ],
    indirect=["tag_table"],
)
def test_delegate_for_columns(tag_table):
    """Test if the correct delegates are set for each column."""
    delegate_col_0 = tag_table.itemDelegateForColumn(0)
    delegate_col_1 = tag_table.itemDelegateForColumn(1)
    delegate_col_2 = tag_table.itemDelegateForColumn(2)

    if not tag_table.read_only:
        assert isinstance(delegate_col_0, TagDelegate)
        assert isinstance(delegate_col_1, JSONDelegate)
        assert isinstance(delegate_col_2, ComboBoxDelegate)
    else:
        assert all(
            [x is None for x in [delegate_col_0, delegate_col_1, delegate_col_2]]
        )


def test_initialization(tag_editor):
    """Test that the TagEditor initializes correctly."""
    assert tag_editor.windowTitle() == "Tag Editor"
    assert tag_editor._save_button.isEnabled() is False
    assert tag_editor._message_label.text() == "No changes yet"
    assert isinstance(tag_editor._tag_table, QtWidgets.QTableView)


def test_read_only_mode(qtbot):
    """Test the TagEditor in read-only mode."""
    target = {"database": "test_db", "tags": {"tag1": "value1"}}
    tag_editor = TagEditor(target=target, read_only=True)

    assert tag_editor._save_button.isEnabled() is False
    assert tag_editor._message_label.text() == "Read only"


def test_save_button_enabled_on_change(tag_editor, qtbot):
    """Test that the save button is enabled when the tag data changes."""
    tag_editor._tag_table.add_tag_button.trigger()

    assert tag_editor._message_label.text() == "Modified"
    assert tag_editor._save_button.isEnabled() is True


def test_save_button_disabled_on_duplicate_keys(tag_editor, qtbot):
    """Test that the save button is disabled if there are duplicate keys."""
    tag_editor._tag_table.add_tag_button.trigger()
    tag_editor._tag_table.add_tag_button.trigger()

    assert tag_editor._message_label.text() == "Error: there are duplicate tag names"
    assert tag_editor._save_button.isEnabled() is False


def test_static_edit_method(qtbot):
    """Test the static edit method behavior."""
    target = {"database": "test_db", "tags": {"tag1": "value1"}}

    # Mock the dialog exec_ method to simulate user accepting the changes
    TagEditor.exec_ = MagicMock(return_value=QtWidgets.QDialog.Accepted)
    TagEditor.tags = MagicMock(return_value={"tag1": "new_value"})

    result = TagEditor.edit(target, read_only=False)

    assert result is True
    assert target["tags"] == {"tag1": "new_value"}

    # Now simulate the user cancelling the dialog
    TagEditor.exec_ = MagicMock(return_value=QtWidgets.QDialog.Rejected)

    result = TagEditor.edit(target, read_only=False)

    assert result is False
    assert target["tags"] == {"tag1": "new_value"}  # No changes after cancel
