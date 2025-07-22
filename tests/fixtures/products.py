DATA = {
    ("products", "a"): {
        "name": "flow - a",
        "code": "a",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    ("products", "product"): {
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
                "input": ("products", "product"),
                "amount": 4,
                "properties": {
                    "price": 7,
                    "mass": 6,
                },
            },
            {
                "functional": True,
                "type": "production",
                "name": "second product - 1",
                "unit": "megajoule",
                "amount": 6,
                "properties": {
                    "price": 12,
                    "mass": 4,
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
