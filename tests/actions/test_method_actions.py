from bw2data import methods
from bw2data.method import Method

from qtpy import QtWidgets
from stats_arrays.distributions import (
    NoUncertainty,
    UndefinedUncertainty,
    UniformUncertainty,
)

from activity_browser import actions
from activity_browser.ui.wizards import UncertaintyWizard


def test_cf_amount_modify(basic_database):
    method = ("basic_method",)
    elementary = basic_database.get("elementary")

    cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]

    assert len(cf) == 1
    assert cf[0][1] == 1.0 or cf[0][1]["amount"] == 1.0

    actions.CFAmountModify.run(method, elementary.id, 200)

    cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]
    assert cf[0][1] == 200.0 or cf[0][1]["amount"] == 200.0


def test_cf_new(basic_database):
    basic_database.new_node("new_elementary", type="emission", name="new_elementary").save()

    method = ("basic_method",)
    new_elementary = basic_database.get("new_elementary")

    cf = [cf for cf in Method(method).load() if cf[0] == new_elementary.id]
    assert len(cf) == 0

    actions.CFNew.run(method, [new_elementary.key])

    cf = [cf for cf in Method(method).load() if cf[0] == new_elementary.id]

    assert len(cf) == 1
    assert cf[0][1] == 0.0


def test_cf_remove(monkeypatch, basic_database):
    method = ("basic_method",)
    elementary = basic_database.get("elementary")
    cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )

    assert len(cf) == 1

    actions.CFRemove.run(method, cf)

    cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]
    assert len(cf) == 0


# def test_cf_uncertainty_modify(basic_database, application_instance):
#     method = ("basic_method",)
#     elementary = basic_database.get("elementary")
#     cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]
#     new_cf_tuple = (
#         elementary.id,
#         {"amount": 5.5},
#     )
#     uncertainty = {
#         "loc": float("nan"),
#         "maximum": 10.0,
#         "minimum": 1.0,
#         "negative": False,
#         "scale": float("nan"),
#         "shape": float("nan"),
#         "uncertainty type": UniformUncertainty.id,
#     }
#
#     assert len(cf) == 1
#     assert cf[0][1].get("uncertainty type") == NoUncertainty.id
#
#     actions.CFUncertaintyModify.run(method, cf)
#
#     wizard = application_instance.main_window.findChild(UncertaintyWizard)
#
#     assert wizard.isVisible()
#
#     wizard.destroy()
#     actions.CFUncertaintyModify.wizard_done(method, new_cf_tuple, uncertainty)
#
#     cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]
#
#     assert cf[0][1].get("uncertainty type") == UniformUncertainty.id
#     assert cf[0][1].get("amount") == 5.5


def test_cf_uncertainty_remove(basic_database):
    method = ("basic_method",)
    elementary = basic_database.get("elementary")
    cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]
    assert len(cf) == 1

    assert cf[0][1].get("uncertainty type") == NoUncertainty.id

    actions.CFUncertaintyRemove.run(method, cf)

    cf = [cf for cf in Method(method).load() if cf[0] == elementary.id]
    assert (
        cf[0][1] == 1.0 or cf[0][1].get("uncertainty type") == UndefinedUncertainty.id
    )


def test_method_delete(monkeypatch, basic_database):
    method = ("basic_method",)

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )

    assert method in methods

    actions.MethodDelete.run([method])

    assert method not in methods


def test_method_duplicate(monkeypatch, basic_database):
    from activity_browser.actions.method.method_duplicate import TupleNameDialog

    method = ("basic_method",)
    duplicated_method = ("basic_method - Copy",)

    monkeypatch.setattr(
        TupleNameDialog,
        "exec_",
        staticmethod(lambda *args, **kwargs: TupleNameDialog.Accepted),
    )

    monkeypatch.setattr(TupleNameDialog, "result_tuple", duplicated_method)

    assert method in methods
    assert duplicated_method not in methods

    actions.MethodDuplicate.run([method], "leaf")

    assert method in methods
    assert duplicated_method in methods
