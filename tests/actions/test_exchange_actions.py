import pytest
from stats_arrays.distributions import NoUncertainty, UndefinedUncertainty

from activity_browser import actions, application
from activity_browser.ui.wizards import UncertaintyWizard


# def test_exchange_copy_sdf(basic_database):
#     # this test will always fail on the linux automated test because it doesn't have a clipboard
#     if platform.system() == "Linux":
#         return
#
#     process = basic_database.get("process")
#     elementary = basic_database.get("elementary")
#
#     exchange = [
#         exchange
#         for exchange in process.exchanges()
#         if exchange.input == elementary
#     ]
#
#     clipboard = QtGui.QClipboard()
#     clipboard.setText("FAILED")
#
#     assert projects.current == "default"
#     assert len(exchange) == 1
#     assert clipboard.text() == "FAILED"
#
#     actions.ExchangeCopySDF.run(exchange)
#
#     assert clipboard.text() != "FAILED"
#
#     return


def test_exchange_delete(basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")

    exchange = [
        exchange
        for exchange in process.exchanges()
        if exchange.input == elementary
    ]

    assert len(exchange) == 1
    num_exchanges = len(process.exchanges())

    actions.ExchangeDelete.run(exchange)

    assert len(process.exchanges()) == num_exchanges - 1


def test_exchange_formula_remove(basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")

    exchange = [
        exchange
        for exchange in process.exchanges()
        if exchange.input == elementary
    ]

    assert len(exchange) == 1
    assert exchange[0].as_dict().get("formula") == "5+5"

    actions.ExchangeFormulaRemove.run(exchange)

    with pytest.raises(KeyError):
        assert exchange[0].as_dict()["formula"]


def test_exchange_modify(basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")

    exchange = [
        exchange
        for exchange in process.exchanges()
        if exchange.input == elementary
    ]

    new_data = {"amount": 200}

    assert len(exchange) == 1
    assert exchange[0].amount == 10.0

    actions.ExchangeModify.run(exchange[0], new_data)

    assert exchange[0].amount == 200.0


def test_exchange_new(basic_database):
    basic_database.new_node("other", type="processwithreferenceproduct", name="other_process").save()

    process = basic_database.get("process")
    other = basic_database.get("other")

    assert not [
        exchange
        for exchange in process.exchanges()
        if exchange.input == other
    ]

    actions.ExchangeNew.run([other.key], process.key, "technosphere")

    assert (
        len(
            [
                exchange
                for exchange in process.exchanges()
                if exchange.input == other
            ]
        )
        == 1
    )


def test_exchange_uncertainty_modify(basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")

    exchange = [
        exchange
        for exchange in process.exchanges()
        if exchange.input == elementary
    ]
    assert len(exchange) == 1

    actions.ExchangeUncertaintyModify.run(exchange)

    wizard = application.main_window.findChild(UncertaintyWizard)

    assert wizard.isVisible()

    wizard.destroy()


def test_exchange_uncertainty_remove(basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")

    exchange = [
        exchange
        for exchange in process.exchanges()
        if exchange.input == elementary
    ]
    assert len(exchange) == 1

    assert exchange[0].uncertainty_type == NoUncertainty

    actions.ExchangeUncertaintyRemove.run(exchange)

    assert exchange[0].uncertainty_type == UndefinedUncertainty
