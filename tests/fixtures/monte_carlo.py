"""
Minimal product system for Monte Carlo uncertainty tests.

Linear chain: main (FU) → supplier. Each uncertainty layer is controlled independently
via ``MonteCarloLCA.calculate(technosphere=..., biosphere=..., cf=..., parameters=...)``.

Expected deterministic score (all uncertainties off, parameters at default): 11.0
  = 10 (main biosphere) + 1 (supplier biosphere) × CF 1.0
"""

from __future__ import annotations

from copy import deepcopy

from stats_arrays.distributions import NoUncertainty, UniformUncertainty

DATABASE_NAME = "mc"
METHOD_NAME = "mc_method"
CALCULATION_SETUP_NAME = "mc_calculation_setup"

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

DATABASE = {
    (DATABASE_NAME, "elementary"): {
        "name": "elementary",
        "code": "elementary",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    (DATABASE_NAME, "supplier_product"): {
        "name": "supplier product",
        "code": "supplier_product",
        "location": "GLO",
        "type": "product",
        "unit": "kg",
        "processor": (DATABASE_NAME, "supplier"),
    },
    (DATABASE_NAME, "main_product"): {
        "name": "main product",
        "code": "main_product",
        "location": "GLO",
        "type": "product",
        "unit": "kg",
        "processor": (DATABASE_NAME, "main"),
    },
    (DATABASE_NAME, "supplier"): {
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
                "input": (DATABASE_NAME, "elementary"),
                **UNIFORM_UNCERTAINTY,
            },
        ],
    },
    (DATABASE_NAME, "main"): {
        "name": "main process",
        "code": "main",
        "location": "GLO",
        "type": "process",
        "exchanges": [
            {
                "type": "production",
                "amount": 1,
                "input": (DATABASE_NAME, "main_product"),
            },
            {
                "type": "technosphere",
                "amount": 1.0,
                "input": (DATABASE_NAME, "supplier_product"),
                **UNIFORM_UNCERTAINTY,
            },
            {
                "type": "biosphere",
                "amount": 10.0,
                "input": (DATABASE_NAME, "elementary"),
                **NO_UNCERTAINTY,
            },
        ],
    },
}

DATABASE_WITH_PARAMETER_FORMULA = deepcopy(DATABASE)
DATABASE_WITH_PARAMETER_FORMULA[(DATABASE_NAME, "main")]["exchanges"][-1]["formula"] = (
    "bio_amount"
)

METHOD = [
    (
        (DATABASE_NAME, "elementary"),
        {"amount": 1.0, **UNIFORM_UNCERTAINTY},
    )
]

CALCULATION_SETUP = {
    "inv": [{(DATABASE_NAME, "main_product"): 1.0}],
    "ia": [(METHOD_NAME,)],
}

BASELINE_SCORE = 11.0

PARAMETER_SETUP = {
    "activity_parameters": [
        {
            "name": "bio_amount",
            "amount": 10.0,
            "formula": "",
            "database": DATABASE_NAME,
            "code": "main",
            **PARAMETER_UNCERTAINTY,
        }
    ],
    "parameterized_exchanges": [
        {
            "process_code": "main",
            "exchange_type": "biosphere",
            "formula": "bio_amount",
        }
    ],
}
