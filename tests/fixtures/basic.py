DATABASE = {
    ("basic", "elementary"): {
        "name": "elementary",
        "code": "elementary",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    ("basic", "process"): {
        "name": "process",
        "code": "process",
        "location": "first",
        "type": "multifunctional",
        "exchanges": [
            {
                "type": "production",
                "amount": 4,
                "input": ("basic", "product_1")
            },
            {
                "type": "production",
                "amount": 6,
                "input": ("basic", "product_2")
            },
            {
                "type": "biosphere",
                "amount": 10,
                "input": ("basic", "elementary"),
            },
        ],
    },
    ("basic", "product_1"): {
            "name": "product - 1",
            "code": "product_1",
            "location": "first",
            "type": "product",
            "unit": "kg",
            "processor": ("basic", "process"),
            "properties": {
                "price": {"amount": 15, "unit": "EUR"},
                "mass": {"amount": 5, "unit": "kg"},
                "manual_allocation": {"amount": 10, "unit": "undefined", "normalized": False},
            },
        },
    ("basic", "product_2"): {
            "name": "product - 2",
            "code": "product_2",
            "location": "first",
            "type": "product",
            "unit": "megajoule",
            "processor": ("basic", "process"),
            "properties": {
                "price": {"amount": 5, "unit": "EUR"},
                "mass": {"amount": 15, "unit": "kg"},
                "manual_allocation": {"amount": 90, "unit": "undefined", "normalized": False},
            },
        },
}

METHOD = [(('basic', 'elementary'), 1.0)]

CALCULATION_SETUP = {'inv': [{('basic', 'product_1'): 1.0}], 'ia': [('METHOD',)]}

