DATA = {
    ("errors", "a"): {
        "name": "product a",
        "unit": "kg",
        "type": "product",
        "properties": {
            "price": 7.7,
        },
    },
    ("errors", "b"): {
        "name": "product b",
        "unit": "kg",
        "type": "product",
        "properties": {
            "price": 8.1,
            "mass": True,
        },
    },
    ("errors", "c"): {
        "name": "product c",
        "unit": "kg",
        "type": "product",
        "properties": {
            "price": 7,
            "mass": 8,
        },
    },
    ("errors", "1"): {
        "name": "process - 1",
        "type": "multifunctional",
        "exchanges": [
            {
                "type": "production",
                "input": ("errors", "a"),
                "amount": 4,
            },
            {
                "type": "production",
                "input": ("errors", "b"),
                "amount": 4,
            },
            {
                "type": "production",
                "input": ("errors", "c"),
                "amount": 4,
            },
            {
                "type": "biosphere",
                "amount": 12,
                "input": ("errors", "2"),
            },
        ],
    },
    ("errors", "2"): {
        "name": "flow",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
}
