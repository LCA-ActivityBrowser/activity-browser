"""
Product system and calculation setups for LCIA overview / scenario / MC / GSA tests.

Database ``LCIA_overview_test`` in project ``testing`` (via setup script).

Deterministic scores (no scenario, uncertainties off):
  prod_i primary biosphere on elem_i with amount ``biosphere_amount(i)``;
  optional shared supplier biosphere on elem_0.
  method_j CF on elem_j with ``cf_amount(j)``.

Edge cases:
  - 1×1, 3×3, 10×10 calculation setups
  - Mixed-sign columns (prod_1 negative biosphere on elem_1)
  - All-negative column (method_neg: negative CF on elem_0)
  - Scenario CS (import bundled scenario file at calculate time)
  - MC CS with technosphere, biosphere, CF, and parameter uncertainties
"""

from __future__ import annotations

from stats_arrays.distributions import NoUncertainty, UniformUncertainty

DATABASE_NAME = "LCIA_overview_test"
PROJECT_NAME = "testing"

N_PRODUCTS = 10
N_METHODS = 10

UNIFORM_UNCERTAINTY = {
    "uncertainty type": UniformUncertainty.id,
    "loc": float("nan"),
    "scale": float("nan"),
    "shape": float("nan"),
    "minimum": 0.8,
    "maximum": 1.2,
    "negative": False,
}

NO_UNCERTAINTY = {"uncertainty type": NoUncertainty.id}

PARAMETER_UNCERTAINTY = {
    "uncertainty type": UniformUncertainty.id,
    "loc": float("nan"),
    "scale": float("nan"),
    "shape": float("nan"),
    "minimum": 8.0,
    "maximum": 12.0,
    "negative": False,
}


def method_name(index: int) -> str:
    return f"lcia_method_{index}"


def product_key(index: int) -> tuple[str, str]:
    return (DATABASE_NAME, f"prod_{index}")


def biosphere_amount(index: int) -> float:
    """Primary biosphere emission; prod_1 is negative for mixed-sign tests."""
    base = float(index + 1) * 10.0
    return -base if index == 1 else base


def cf_amount(index: int) -> float:
    return 1.0 + 0.1 * index


def _elementary_key(index: int) -> tuple[str, str]:
    return (DATABASE_NAME, f"elem_{index}")


def _product_data_key(index: int) -> tuple[str, str]:
    return (DATABASE_NAME, f"prod_{index}")


def _main_process_key(index: int) -> tuple[str, str]:
    return (DATABASE_NAME, f"main_{index}")


def build_database(*, parameterize_prod_0_biosphere: bool = False) -> dict:
    data: dict = {}

    for i in range(N_PRODUCTS):
        data[_elementary_key(i)] = {
            "name": f"elementary flow {i}",
            "code": f"elem_{i}",
            "unit": "kg",
            "type": "emission",
            "categories": ("air", f"elem_{i}"),
        }

    data[(DATABASE_NAME, "supplier_product")] = {
        "name": "supplier product",
        "code": "supplier_product",
        "location": "GLO",
        "type": "product",
        "unit": "kg",
        "processor": (DATABASE_NAME, "supplier"),
    }

    data[(DATABASE_NAME, "supplier")] = {
        "name": "supplier process",
        "code": "supplier",
        "location": "GLO",
        "type": "process",
        "exchanges": [
            {
                "type": "production",
                "amount": 1,
                "input": (DATABASE_NAME, "supplier_product"),
            },
            {
                "type": "biosphere",
                "amount": 1.0,
                "input": _elementary_key(0),
                **UNIFORM_UNCERTAINTY,
            },
        ],
    }

    for i in range(N_PRODUCTS):
        pk = _product_data_key(i)
        mk = _main_process_key(i)
        data[pk] = {
            "name": f"product {i}",
            "reference product": f"product {i}",
            "code": f"prod_{i}",
            "location": "GLO",
            "type": "product",
            "unit": "kg",
            "processor": mk,
        }
        exchanges = [
            {
                "type": "production",
                "amount": 1,
                "input": pk,
            },
            {
                "type": "technosphere",
                "amount": 1.0,
                "input": (DATABASE_NAME, "supplier_product"),
                **(UNIFORM_UNCERTAINTY if i == 0 else NO_UNCERTAINTY),
            },
            {
                "type": "biosphere",
                "amount": biosphere_amount(i),
                "input": _elementary_key(i),
                **(NO_UNCERTAINTY if i != 0 else UNIFORM_UNCERTAINTY),
            },
        ]
        if parameterize_prod_0_biosphere and i == 0:
            exchanges[-1]["formula"] = "bio_amount"
        data[mk] = {
            "name": f"main process {i}",
            "code": f"main_{i}",
            "location": "GLO",
            "type": "process",
            "exchanges": exchanges,
        }

    return data


DATABASE = build_database()
DATABASE_WITH_PARAMETER_FORMULA = build_database(parameterize_prod_0_biosphere=True)


def build_methods() -> dict[str, list]:
    methods = {}
    for j in range(N_METHODS):
        methods[method_name(j)] = [
            (
                _elementary_key(j),
                {"amount": cf_amount(j), **(UNIFORM_UNCERTAINTY if j == 0 else NO_UNCERTAINTY)},
            )
        ]
    methods["lcia_method_neg"] = [
        (
            _elementary_key(0),
            {"amount": -1.0, **NO_UNCERTAINTY},
        )
    ]
    return methods


METHODS = build_methods()


def _inv(indices: range) -> list[dict]:
    return [{product_key(i): 1.0} for i in indices]


def _ia(indices: range) -> list[tuple[str, ...]]:
    return [(method_name(i),) for i in indices]


CALCULATION_SETUPS = {
    "lcia_1x1": {"inv": _inv(range(1)), "ia": _ia(range(1))},
    "lcia_3x3": {"inv": _inv(range(3)), "ia": _ia(range(3))},
    "lcia_10x10": {"inv": _inv(range(10)), "ia": _ia(range(10))},
    "lcia_3x3_neg": {
        "inv": _inv(range(3)),
        "ia": [("lcia_method_0",), ("lcia_method_neg",), ("lcia_method_2",)],
    },
    "lcia_10x10_scenario": {"inv": _inv(range(10)), "ia": _ia(range(10))},
    "lcia_mc": {"inv": _inv(range(3)), "ia": _ia(range(3))},
}

SCENARIO_FILENAME = "lcia_overview_scenarios.csv"

PARAMETER_SETUP = {
    "activity_parameters": [
        {
            "name": "bio_amount",
            "amount": biosphere_amount(0),
            "formula": "",
            "database": DATABASE_NAME,
            "code": "main_0",
            **PARAMETER_UNCERTAINTY,
        }
    ],
    "parameterized_exchanges": [
        {
            "process_code": "main_0",
            "exchange_type": "biosphere",
            "formula": "bio_amount",
        }
    ],
}


def build_scenario_dataframe():
    """Flow scenario varying technosphere amount on main_0 → supplier."""
    import pandas as pd

    from activity_browser.bwutils.superstructure import SUPERSTRUCTURE
    from activity_browser.bwutils.superstructure.activities import data_from_index

    index = (
        (DATABASE_NAME, "supplier_product"),
        (DATABASE_NAME, "main_0"),
    )
    row = data_from_index(index)
    row["flow type"] = "technosphere"
    df = pd.DataFrame([row], columns=SUPERSTRUCTURE.tolist())
    df["baseline"] = 1.0
    df["high_demand"] = 1.5
    df["low_demand"] = 0.5
    return df
