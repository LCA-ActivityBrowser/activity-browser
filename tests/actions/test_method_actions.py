import bw2data as bd
from stats_arrays.distributions import NormalUncertainty, UndefinedUncertainty, UniformUncertainty
from PySide2 import QtWidgets

from activity_browser import actions, application
from activity_browser.ui.widgets.dialog import TupleNameDialog
from activity_browser.ui.wizards import UncertaintyWizard


def test_cf_amount_modify(ab_app):
    method = ("A_methods", "methods", "method")
    key = ('biosphere3', '595f08d9-6304-497e-bb7d-48b6d2d8bff3')
    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]

    assert bd.projects.current == "default"
    assert len(cf) == 1
    assert cf[0][1] == 1.0 or cf[0][1]['amount'] == 1.0

    actions.CFAmountModify.run(method, cf, 200)

    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]
    assert cf[0][1] == 200.0 or cf[0][1]['amount'] == 200.0


def test_cf_new(ab_app):
    method = ("A_methods", "methods", "method")
    key = ('biosphere3', '0d9f52b2-f2d5-46a3-90a3-e22ef252cc37')
    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]

    assert bd.projects.current == "default"
    assert len(cf) == 0

    actions.CFNew.run(method, [key])

    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]

    assert len(cf) == 1
    assert cf[0][1] == 0.0


def test_cf_remove(ab_app, monkeypatch):
    method = ("A_methods", "methods", "method")
    key = ('biosphere3', '075e433b-4be4-448e-9510-9a5029c1ce94')
    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'warning',
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)
    )

    assert bd.projects.current == "default"
    assert len(cf) == 1

    actions.CFRemove.run(method, cf)

    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]
    assert len(cf) == 0


def test_cf_uncertainty_modify(ab_app):
    method = ("A_methods", "methods", "method")
    key = ('biosphere3', 'da5e6be3-ed71-48ac-9397-25bac666c7b7')
    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]
    new_cf_tuple = (('biosphere3', 'da5e6be3-ed71-48ac-9397-25bac666c7b7'), {'amount': 5.5})
    uncertainty = {'loc': float('nan'), 'maximum': 10.0, 'minimum': 1.0, 'negative': False, 'scale': float('nan'),
                   'shape': float('nan'), 'uncertainty type': 4}

    assert bd.projects.current == "default"
    assert len(cf) == 1
    assert cf[0][1].get("uncertainty type") == NormalUncertainty.id

    actions.CFUncertaintyModify.run(method, cf)

    wizard = application.main_window.findChild(UncertaintyWizard)

    assert wizard.isVisible()

    wizard.destroy()
    actions.CFUncertaintyModify.wizard_done(method, new_cf_tuple, uncertainty)

    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]

    assert cf[0][1].get("uncertainty type") == UniformUncertainty.id
    assert cf[0][1].get("amount") == 5.5


def test_cf_uncertainty_remove(ab_app):
    method = ("A_methods", "methods", "method")
    key = ('biosphere3', '2a7b68ff-f12a-44c6-8b31-71ec91d29889')
    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]

    assert bd.projects.current == "default"
    assert len(cf) == 1
    assert cf[0][1].get("uncertainty type") == NormalUncertainty.id

    actions.CFUncertaintyRemove.run(method, cf)

    cf = [cf for cf in bd.Method(method).load() if cf[0] == key]
    assert cf[0][1] == 1.0 or cf[0][1].get("uncertainty type") == UndefinedUncertainty.id


def test_method_delete(ab_app, monkeypatch):
    method = ("A_methods", "methods", "method_to_delete")
    branch = ("A_methods", "methods_to_delete")
    branched_method = ("A_methods", "methods_to_delete", "method_to_delete")

    monkeypatch.setattr(
        QtWidgets.QMessageBox, 'warning',
        staticmethod(lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)
    )

    assert bd.projects.current == "default"
    assert method in bd.methods
    assert branched_method in bd.methods

    actions.MethodDelete.run([method], 'leaf')
    actions.MethodDelete.run([branch], 'branch')

    assert method not in bd.methods
    assert branched_method not in bd.methods


def test_method_duplicate(ab_app, monkeypatch):
    method = ("A_methods", "methods", "method_to_duplicate")
    result = ("A_methods", "duplicated_methods")
    duplicated_method = ("A_methods", "duplicated_methods", "method_to_duplicate")

    monkeypatch.setattr(
        TupleNameDialog, 'exec_',
        staticmethod(lambda *args, **kwargs: TupleNameDialog.Accepted)
    )

    monkeypatch.setattr(
        TupleNameDialog, 'result_tuple',
        result
    )

    assert method in bd.methods
    assert duplicated_method not in bd.methods

    actions.MethodDuplicate.run([method], 'leaf')

    assert method in bd.methods
    assert duplicated_method in bd.methods

