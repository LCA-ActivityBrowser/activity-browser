import pytest
from stats_arrays.distributions import NoUncertainty, UndefinedUncertainty, UniformUncertainty

from activity_browser import app
from activity_browser.ui.dialogs import UncertaintyDialog


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
#     app.actions.ExchangeCopySDF.run(exchange)
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

    app.actions.ExchangeDelete.run(exchange)

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

    app.actions.ExchangeFormulaRemove.run(exchange)

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

    app.actions.ExchangeModify.run(exchange[0], new_data)

    assert exchange[0].amount == 200.0


def test_exchange_modify_formula_indexes_process(basic_database):
    from bw2data.parameters import ParameterizedExchange

    process = basic_database.get("process")
    elementary = basic_database.get("elementary")
    exchange = next(
        exc for exc in process.exchanges() if exc.input == elementary
    )

    app.actions.ExchangeModify.run(exchange, {"formula": "6+6"})

    from activity_browser.bwutils.commontasks import refresh_edge

    exchange = refresh_edge(exchange)
    assert exchange["formula"] == "6+6"
    assert exchange["amount"] == 12
    assert ParameterizedExchange.select().count() == 1


def test_exchange_new(basic_database):
    basic_database.new_node("other", type="processwithreferenceproduct", name="other_process").save()

    process = basic_database.get("process")
    other = basic_database.get("other")

    assert not [
        exchange
        for exchange in process.exchanges()
        if exchange.input == other
    ]

    app.actions.ExchangeNew.run([other.key], process.key, "technosphere")

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


def test_exchange_uncertainty_modify(monkeypatch, basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")

    exchange = [
        exchange
        for exchange in process.exchanges()
        if exchange.input == elementary
    ]
    assert len(exchange) == 1
    
    # Initial state: should have NoUncertainty
    assert exchange[0].uncertainty_type == NoUncertainty
    
    # Create mock uncertainty data to be returned by the dialog
    mock_uncertainty = {
        "uncertainty type": UniformUncertainty.id,
        "loc": float("nan"),
        "scale": float("nan"),
        "shape": float("nan"),
        "minimum": 5.0,
        "maximum": 15.0,
        "negative": False,
    }
    
    # Monkeypatch the dialog to return our mock data
    monkeypatch.setattr(
        UncertaintyDialog,
        "get_uncertainty_dict",
        lambda *args, **kwargs: (True, mock_uncertainty),
    )

    app.actions.ExchangeUncertaintyModify.run(exchange)

    # Verify the exchange was updated with the new uncertainty values
    assert exchange[0].uncertainty_type == UniformUncertainty
    assert exchange[0]["minimum"] == 5.0
    assert exchange[0]["maximum"] == 15.0
    assert exchange[0]["negative"] == False


def test_exchange_uncertainty_modify_writes_pedigree(monkeypatch, basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")
    exchange = [
        exc for exc in process.exchanges() if exc.input == elementary
    ]
    recipe = {
        "reliability": 2,
        "completeness": 1,
        "temporal correlation": 1,
        "geographical correlation": 1,
        "further technological correlation": 1,
        "basic uncertainty": 1.05,
    }
    mock_uncertainty = {
        "uncertainty type": UniformUncertainty.id,
        "loc": float("nan"),
        "scale": float("nan"),
        "shape": float("nan"),
        "minimum": 5.0,
        "maximum": 15.0,
        "negative": False,
        "pedigree": recipe,
    }
    monkeypatch.setattr(
        UncertaintyDialog,
        "get_uncertainty_dict",
        lambda *args, **kwargs: (True, mock_uncertainty),
    )
    app.actions.ExchangeUncertaintyModify.run(exchange)
    assert exchange[0]["pedigree"]["reliability"] == 2
    assert exchange[0]["pedigree"]["basic uncertainty"] == 1.05


def test_exchange_uncertainty_modify_without_pedigree_keeps_recipe(monkeypatch, basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")
    exchange = [
        exc for exc in process.exchanges() if exc.input == elementary
    ]
    exchange[0]["pedigree"] = {
        "reliability": 2,
        "completeness": 1,
        "temporal correlation": 1,
        "geographical correlation": 1,
        "further technological correlation": 1,
    }
    exchange[0].save()
    mock_uncertainty = {
        "uncertainty type": UniformUncertainty.id,
        "loc": float("nan"),
        "scale": float("nan"),
        "shape": float("nan"),
        "minimum": 5.0,
        "maximum": 15.0,
        "negative": False,
    }
    monkeypatch.setattr(
        UncertaintyDialog,
        "get_uncertainty_dict",
        lambda *args, **kwargs: (True, mock_uncertainty),
    )
    app.actions.ExchangeUncertaintyModify.run(exchange)
    assert exchange[0]["pedigree"]["reliability"] == 2
    assert exchange[0]["minimum"] == 5.0


def test_exchange_uncertainty_modify_clears_pedigree(monkeypatch, basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")
    exchange = [
        exc for exc in process.exchanges() if exc.input == elementary
    ]
    exchange[0]["pedigree"] = {
        "reliability": 3,
        "completeness": 1,
        "temporal correlation": 1,
        "geographical correlation": 1,
        "further technological correlation": 1,
    }
    exchange[0].save()
    mock_uncertainty = {
        "uncertainty type": UndefinedUncertainty.id,
        "pedigree": None,
    }
    monkeypatch.setattr(
        UncertaintyDialog,
        "get_uncertainty_dict",
        lambda *args, **kwargs: (True, mock_uncertainty),
    )
    app.actions.ExchangeUncertaintyModify.run(exchange)
    assert "pedigree" not in exchange[0]


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

    app.actions.ExchangeUncertaintyRemove.run(exchange)

    assert exchange[0].uncertainty_type == UndefinedUncertainty


def test_exchange_uncertainty_remove_keeps_pedigree(basic_database):
    process = basic_database.get("process")
    elementary = basic_database.get("elementary")
    exchange = [
        exc for exc in process.exchanges() if exc.input == elementary
    ]
    exchange[0]["pedigree"] = {
        "reliability": 2,
        "completeness": 1,
        "temporal correlation": 1,
        "geographical correlation": 1,
        "further technological correlation": 1,
    }
    exchange[0].save()
    app.actions.ExchangeUncertaintyRemove.run(exchange)
    assert exchange[0]["pedigree"]["reliability"] == 2
    assert exchange[0].uncertainty_type == UndefinedUncertainty
