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
