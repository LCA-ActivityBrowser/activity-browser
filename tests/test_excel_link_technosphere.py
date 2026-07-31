"""Excel import: internal technosphere linking must respect exchange database."""
from copy import deepcopy

from activity_browser.bwutils.strategies import link_technosphere_same_database


def _ev_case_like_dataset():
    """Local market plus a same-named technosphere input from another database."""
    return [
        {
            "database": "EV case",
            "code": "local_market",
            "name": "market for electricity, low voltage",
            "location": "NL",
            "unit": "kilowatt hour",
            "reference product": "electricity, low voltage",
            "exchanges": [
                {
                    "type": "production",
                    "amount": 1,
                    "name": "market for electricity, low voltage",
                    "database": "EV case",
                    "location": "NL",
                    "unit": "kilowatt hour",
                    "reference product": "electricity, low voltage",
                },
                {
                    "type": "technosphere",
                    "amount": 1,
                    "name": "market for electricity, low voltage",
                    "database": "ei3.11-REMIND",
                    "location": "NL",
                    "unit": "kilowatt hour",
                    "reference product": "electricity, low voltage",
                },
                {
                    "type": "technosphere",
                    "amount": 0.25,
                    "name": "market for electricity, low voltage",
                    "database": "EV case",
                    "location": "NL",
                    "unit": "kilowatt hour",
                    "reference product": "electricity, low voltage",
                },
            ],
        }
    ]


def test_foreign_database_technosphere_not_self_linked():
    data = link_technosphere_same_database(deepcopy(_ev_case_like_dataset()))
    exchanges = data[0]["exchanges"]
    production = next(e for e in exchanges if e["type"] == "production")
    foreign = next(e for e in exchanges if e.get("database") == "ei3.11-REMIND")
    local = next(
        e
        for e in exchanges
        if e["type"] == "technosphere" and e.get("database") == "EV case"
    )

    assert production.get("input") == ("EV case", "local_market")
    assert local.get("input") == ("EV case", "local_market")
    assert "input" not in foreign
