import brightway2 as bw
from PySide2 import QtWidgets

from activity_browser import actions


def test_cs_delete(ab_app, monkeypatch):
    cs = "cs_to_delete"

    monkeypatch.setattr(
        QtWidgets.QMessageBox, "warning", staticmethod(lambda *args, **kwargs: True)
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox, "information", staticmethod(lambda *args, **kwargs: True)
    )

    assert bw.projects.current == "default"
    assert cs in bw.calculation_setups

    actions.CSDelete.run(cs)

    assert cs not in bw.calculation_setups


def test_cs_duplicate(ab_app, monkeypatch):
    cs = "cs_to_duplicate"
    dup_cs = "cs_that_is_duplicated"

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("cs_that_is_duplicated", True)),
    )

    assert bw.projects.current == "default"
    assert cs in bw.calculation_setups
    assert dup_cs not in bw.calculation_setups

    actions.CSDuplicate.run(cs)

    assert cs in bw.calculation_setups
    assert dup_cs in bw.calculation_setups


def test_cs_new(ab_app, monkeypatch):
    new_cs = "cs_that_is_new"

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("cs_that_is_new", True)),
    )

    assert bw.projects.current == "default"
    assert new_cs not in bw.calculation_setups

    actions.CSNew.run()

    assert new_cs in bw.calculation_setups

    return


def test_cs_rename(ab_app, monkeypatch):
    cs = "cs_to_rename"
    renamed_cs = "cs_that_is_renamed"

    monkeypatch.setattr(
        QtWidgets.QInputDialog,
        "getText",
        staticmethod(lambda *args, **kwargs: ("cs_that_is_renamed", True)),
    )

    assert bw.projects.current == "default"
    assert cs in bw.calculation_setups
    assert renamed_cs not in bw.calculation_setups

    actions.CSRename.run(cs)

    assert cs not in bw.calculation_setups
    assert renamed_cs in bw.calculation_setups
