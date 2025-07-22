DATA = {
    ("product_properties", "a"): {
        "name": "flow - a",
        "code": "a",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    ("product_properties", "product"): {
        "type": "product",
        "name": "first product",
        "unit": "kg",
        "exchanges": [],
        "properties": {
            "price": 7,
            "mass": 6,
        },
    },
    ("product_properties", "1"): {
        "name": "process - 1",
        "code": "1",
        "location": "first",
        "type": "multifunctional",
        "exchanges": [
            {
                "functional": True,
                "type": "production",
                "input": ("product_properties", "product"),
                "amount": 4,
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
                "input": ("product_properties", "a"),
            },
        ],
    },
}
