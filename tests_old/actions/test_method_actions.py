from bw2data import methods
from bw2data.method import Method
from bw2data.project import projects

from qtpy import QtWidgets
from stats_arrays.distributions import (
    NormalUncertainty,
    UndefinedUncertainty,
    UniformUncertainty,
)

from activity_browser import actions, application
from activity_browser.ui.widgets.dialog import TupleNameDialog
from activity_browser.ui.wizards import UncertaintyWizard


def test_cf_amount_modify(ab_app):
    method = ("A_methods", "methods", "method")
    key = ("biosphere3", "595f08d9-6304-497e-bb7d-48b6d2d8bff3")
    act_id = 2192
    cf = [cf for cf in Method(method).load() if cf[0] == act_id]

    assert projects.current == "default"
    assert len(cf) == 1
    assert cf[0][1] == 1.0 or cf[0][1]["amount"] == 1.0

    actions.CFAmountModify.run(method, cf, 200)

    cf = [cf for cf in Method(method).load() if cf[0] == act_id]
    assert cf[0][1] == 200.0 or cf[0][1]["amount"] == 200.0


def test_cf_new(ab_app):
    method = ("A_methods", "methods", "method")
    key = ("biosphere3", "0d9f52b2-f2d5-46a3-90a3-e22ef252cc37")
    act_id = 2084
    cf = [cf for cf in Method(method).load() if cf[0] == act_id]

    assert projects.current == "default"
    assert len(cf) == 0

    actions.CFNew.run(method, [key])

    cf = [cf for cf in Method(method).load() if cf[0] == act_id]

    assert len(cf) == 1
    assert cf[0][1] == 0.0


def test_cf_remove(ab_app, monkeypatch):
    method = ("A_methods", "methods", "method")
    key = ("biosphere3", "075e433b-4be4-448e-9510-9a5029c1ce94")
    act_id = 3772
    cf = [cf for cf in Method(method).load() if cf[0] == act_id]

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )

    assert projects.current == "default"
    assert len(cf) == 1

    actions.CFRemove.run(method, cf)

    cf = [cf for cf in Method(method).load() if cf[0] == act_id]
    assert len(cf) == 0


def test_cf_uncertainty_modify(ab_app):
    method = ("A_methods", "methods", "method")
    key = ("biosphere3", "da5e6be3-ed71-48ac-9397-25bac666c7b7")
    act_id = 2188
    cf = [cf for cf in Method(method).load() if cf[0] == act_id]
    new_cf_tuple = (
        act_id,
        {"amount": 5.5},
    )
    uncertainty = {
        "loc": float("nan"),
        "maximum": 10.0,
        "minimum": 1.0,
        "negative": False,
        "scale": float("nan"),
        "shape": float("nan"),
        "uncertainty type": UniformUncertainty.id,
    }

    assert projects.current == "default"
    assert len(cf) == 1
    assert cf[0][1].get("uncertainty type") == NormalUncertainty.id

    actions.CFUncertaintyModify.run(method, cf)

    wizard = application.main_window.findChild(UncertaintyWizard)

    assert wizard.isVisible()

    wizard.destroy()
    actions.CFUncertaintyModify.wizard_done(method, new_cf_tuple, uncertainty)

    cf = [cf for cf in Method(method).load() if cf[0] == act_id]

    assert cf[0][1].get("uncertainty type") == UniformUncertainty.id
    assert cf[0][1].get("amount") == 5.5


def test_cf_uncertainty_remove(ab_app):
    method = ("A_methods", "methods", "method")
    key = ("biosphere3", "2a7b68ff-f12a-44c6-8b31-71ec91d29889")
    act_id = 2164
    cf = [cf for cf in Method(method).load() if cf[0] == act_id]

    assert projects.current == "default"
    assert len(cf) == 1
    assert cf[0][1].get("uncertainty type") == NormalUncertainty.id

    actions.CFUncertaintyRemove.run(method, cf)

    cf = [cf for cf in Method(method).load() if cf[0] == act_id]
    assert (
        cf[0][1] == 1.0 or cf[0][1].get("uncertainty type") == UndefinedUncertainty.id
    )


def test_method_delete(ab_app, monkeypatch):
    method = ("A_methods", "methods", "method_to_delete")
    dual_method_1 = ("A_methods", "methods_to_delete", "method_to_delete_one")
    dual_method_2 = ("A_methods", "methods_to_delete", "method_to_delete_two")

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes),
    )

    assert projects.current == "default"
    assert method in methods
    assert dual_method_1 in methods
    assert dual_method_2 in methods

    actions.MethodDelete.run([method])
    actions.MethodDelete.run([dual_method_1, dual_method_2])

    assert method not in methods
    assert dual_method_1 not in methods
    assert dual_method_2 not in methods


def test_method_duplicate(ab_app, monkeypatch):
    method = ("A_methods", "methods", "method_to_duplicate")
    result = ("A_methods", "duplicated_methods")
    duplicated_method = ("A_methods", "duplicated_methods", "method_to_duplicate")

    monkeypatch.setattr(
        TupleNameDialog,
        "exec_",
        staticmethod(lambda *args, **kwargs: TupleNameDialog.Accepted),
    )

    monkeypatch.setattr(TupleNameDialog, "result_tuple", result)

    assert method in methods
    assert duplicated_method not in methods

    actions.MethodDuplicate.run([method], "leaf")

    assert method in methods
    assert duplicated_method in methods
