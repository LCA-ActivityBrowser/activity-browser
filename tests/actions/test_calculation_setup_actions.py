import pytest
import bw2data as bd
from bw2data.errors import BW2Exception
from qtpy import QtWidgets

from activity_browser import actions



def test_cs_delete(monkeypatch, basic_database):
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", staticmethod(lambda *args, **kwargs: True)
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    cs_name = "basic_calculation_setup"

    assert cs_name in bd.calculation_setups

    actions.CSDelete.run(cs_name)

    assert cs_name not in bd.calculation_setups


def test_cs_duplicate(monkeypatch, basic_database):
    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("duplicated", True)),
    )

    cs_name = "basic_calculation_setup"
    duplicated = "duplicated"

    assert cs_name in bd.calculation_setups
    assert duplicated not in bd.calculation_setups

    actions.CSDuplicate.run(cs_name)

    assert cs_name in bd.calculation_setups
    assert duplicated in bd.calculation_setups


def test_cs_new(monkeypatch, basic_database):
    new_cs = "cs_that_is_new"

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: (new_cs, True)),
    )

    assert new_cs not in bd.calculation_setups

    actions.CSNew.run()

    assert new_cs in bd.calculation_setups


def test_cs_rename(monkeypatch, basic_database):
    cs_name = "basic_calculation_setup"
    renamed_cs = "cs_that_is_renamed"

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: (renamed_cs, True)),
    )

    assert cs_name in bd.calculation_setups
    assert renamed_cs not in bd.calculation_setups

    actions.CSRename.run(cs_name)

    assert cs_name not in bd.calculation_setups
    assert renamed_cs in bd.calculation_setups


def test_cs_new_retry_on_duplicate(monkeypatch, basic_database):
    """Test that CSNew retries with the same name when a duplicate is entered."""
    cs_name = "basic_calculation_setup"
    new_cs = "cs_that_is_new"
    
    # Simulate user first entering an existing name, then a new name
    call_count = [0]
    def mock_getText(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return (cs_name, True)  # First attempt - duplicate
        else:
            return (new_cs, True)  # Second attempt - unique name
    
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(mock_getText))
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(lambda *args, **kwargs: True))
    
    assert cs_name in bd.calculation_setups
    assert new_cs not in bd.calculation_setups
    
    actions.CSNew.run()
    
    assert cs_name in bd.calculation_setups
    assert new_cs in bd.calculation_setups
    assert call_count[0] == 2  # Dialog should have been shown twice


def test_cs_new_cancel_on_retry(monkeypatch, basic_database):
    """Test that CSNew cancels properly when user cancels after duplicate error."""
    cs_name = "basic_calculation_setup"
    
    # Simulate user first entering an existing name, then canceling
    call_count = [0]
    def mock_getText(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return (cs_name, True)  # First attempt - duplicate
        else:
            return ("", False)  # Second attempt - cancel
    
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(mock_getText))
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(lambda *args, **kwargs: True))
    
    initial_setups = set(bd.calculation_setups.keys())
    
    actions.CSNew.run()
    
    # No new setup should be created
    assert set(bd.calculation_setups.keys()) == initial_setups
    assert call_count[0] == 2  # Dialog should have been shown twice


def test_cs_duplicate_retry_on_duplicate(monkeypatch, basic_database):
    """Test that CSDuplicate retries with the same name when a duplicate is entered."""
    cs_name = "basic_calculation_setup"
    duplicate_name = "cs_duplicate"
    
    # Simulate user first entering an existing name, then a new name
    call_count = [0]
    def mock_getText(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return (cs_name, True)  # First attempt - duplicate
        else:
            return (duplicate_name, True)  # Second attempt - unique name
    
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(mock_getText))
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(lambda *args, **kwargs: True))
    
    assert cs_name in bd.calculation_setups
    assert duplicate_name not in bd.calculation_setups
    
    actions.CSDuplicate.run(cs_name)
    
    assert cs_name in bd.calculation_setups
    assert duplicate_name in bd.calculation_setups
    assert call_count[0] == 2  # Dialog should have been shown twice


def test_cs_rename_retry_on_duplicate(monkeypatch, basic_database):
    """Test that CSRename retries with the same name when a duplicate is entered."""
    cs_name = "basic_calculation_setup"
    existing_name = "another_setup"
    renamed_cs = "cs_renamed"
    
    # Create another setup to test duplicate detection
    bd.calculation_setups[existing_name] = {"inv": [], "ia": []}
    
    # Simulate user first entering an existing name, then a new name
    call_count = [0]
    def mock_getText(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return (existing_name, True)  # First attempt - duplicate
        else:
            return (renamed_cs, True)  # Second attempt - unique name
    
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(mock_getText))
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(lambda *args, **kwargs: True))
    
    assert cs_name in bd.calculation_setups
    assert existing_name in bd.calculation_setups
    assert renamed_cs not in bd.calculation_setups
    
    actions.CSRename.run(cs_name)
    
    assert cs_name not in bd.calculation_setups
    assert existing_name in bd.calculation_setups
    assert renamed_cs in bd.calculation_setups
    assert call_count[0] == 2  # Dialog should have been shown twice


def test_cs_rename_prepopulates_old_name(monkeypatch, basic_database):
    """Test that CSRename pre-populates the dialog with the old name."""
    cs_name = "basic_calculation_setup"
    renamed_cs = "cs_renamed"
    
    captured_kwargs = []
    def mock_getText(*args, **kwargs):
        captured_kwargs.append(kwargs)
        return (renamed_cs, True)
    
    monkeypatch.setattr(QtWidgets.QInputDialog, "getText", staticmethod(mock_getText))
    
    actions.CSRename.run(cs_name)
    
    # Check that the text parameter was set to the old name
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0].get('text') == cs_name
