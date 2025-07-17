DATA = {
    ("products", "a"): {
        "name": "flow - a",
        "code": "a",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    ("products", "p1"): {
        "type": "product",
        "name": "first product",
        "unit": "kg",
        "exchanges": [],
    },
    ("products", "p2"): {
        "type": "product",
        "name": "first product",
        "unit": "kg",
        "exchanges": [],
    },
    ("products", "p3"): {
        "type": "product",
        "name": "first product",
        "unit": "kg",
        "exchanges": [],
    },
    ("products", "1"): {
        "name": "process - 1",
        "code": "1",
        "location": "first",
        "type": "multifunctional",
        "exchanges": [
            {
                "functional": True,
                "type": "production",
                "input": ("products", "p1"),
                "amount": 4,
                "properties": {
                    "price": 7,
                    "mass": 6,
                },
            },
            {
                "functional": True,
                "type": "production",
                "input": ("products", "p2"),
                "amount": 4,
                "properties": {
                    "price": 7,
                    "mass": 6,
                },
            },
            {
                "functional": True,
                "type": "production",
                "input": ("products", "p3"),
                "amount": 4,
                "properties": {
                    "price": 7,
                    "mass": 6,
                },
            },
            {
                "type": "biosphere",
                "name": "flow - a",
                "amount": 10,
                "input": ("products", "a"),
            },
        ],
    },
}
