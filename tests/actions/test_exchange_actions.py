import pytest
import platform
import bw2data as bd
from activity_browser import actions, application
from activity_browser.ui.wizards import UncertaintyWizard
from PySide2 import QtGui
from stats_arrays.distributions import NormalUncertainty, UndefinedUncertainty


def test_exchange_copy_sdf(ab_app):
    # this test will always fail on the linux automated test because it doesn't have a clipboard
    if platform.system() == "Linux": return

    key = ('exchange_tests', '186cdea4c3214479b931428591ab2021')
    from_key = ('exchange_tests', '77780c6ab87d4e8785172f107877d6ed')
    exchange = [exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]

    clipboard = QtGui.QClipboard()
    clipboard.setText("FAILED")

    assert bd.projects.current == "default"
    assert len(exchange) == 1
    assert clipboard.text() == "FAILED"

    actions.ExchangeCopySDF.run(exchange)

    assert clipboard.text() != "FAILED"

    return


def test_exchange_delete(ab_app):
    key = ('exchange_tests', '186cdea4c3214479b931428591ab2021')
    from_key = ('exchange_tests', '3b86eaea74ff40d69e9e6bec137a8f0c')
    exchange = [exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]

    assert bd.projects.current == "default"
    assert len(exchange) == 1
    assert exchange[0].as_dict() in [exchange.as_dict() for exchange in bd.get_activity(key).exchanges()]

    actions.ExchangeDelete.run(exchange)

    assert exchange[0].as_dict() not in [exchange.as_dict() for exchange in bd.get_activity(key).exchanges()]


def test_exchange_formula_remove(ab_app):
    key = ('exchange_tests', '186cdea4c3214479b931428591ab2021')
    from_key = ('exchange_tests', '19437c81de6545ad8d017ee2e2fa32e6')
    exchange = [exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]

    assert bd.projects.current == "default"
    assert len(exchange) == 1
    assert exchange[0].as_dict()["formula"]

    actions.ExchangeFormulaRemove.run(exchange)

    with pytest.raises(KeyError): assert exchange[0].as_dict()["formula"]


def test_exchange_modify(ab_app):
    key = ('exchange_tests', '186cdea4c3214479b931428591ab2021')
    from_key = ('exchange_tests', '0e1dc99927284e45af17d546414a3ccd')
    exchange = [exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]

    new_data = {"amount": 200}

    assert bd.projects.current == "default"
    assert len(exchange) == 1
    assert exchange[0].amount == 1.0

    actions.ExchangeModify.run(exchange[0], new_data)

    assert exchange[0].amount == 200.0


def test_exchange_new(ab_app):
    key = ('exchange_tests', '186cdea4c3214479b931428591ab2021')
    from_key = ('activity_tests', 'be8fb2776c354aa7ad61d8348828f3af')

    assert bd.projects.current == "default"
    assert not [exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]

    actions.ExchangeNew.run([from_key], key)

    assert len([exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]) == 1


def test_exchange_uncertainty_modify(ab_app):
    key = ('exchange_tests', '186cdea4c3214479b931428591ab2021')
    from_key = ('exchange_tests', '5ad223731bd244e997623b0958744017')
    exchange = [exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]

    assert bd.projects.current == "default"
    assert len(exchange) == 1

    actions.ExchangeUncertaintyModify.run(exchange)

    wizard = application.main_window.findChild(UncertaintyWizard)

    assert wizard.isVisible()

    wizard.destroy()


def test_exchange_uncertainty_remove(ab_app):
    key = ('exchange_tests', '186cdea4c3214479b931428591ab2021')
    from_key = ('exchange_tests', '4e28577e29a346e3aef6aeafb6d5eb65')
    exchange = [exchange for exchange in bd.get_activity(key).exchanges() if exchange.input.key == from_key]

    assert bd.projects.current == "default"
    assert len(exchange) == 1
    assert exchange[0].uncertainty_type == NormalUncertainty

    actions.ExchangeUncertaintyRemove.run(exchange)

    assert exchange[0].uncertainty_type == UndefinedUncertainty
