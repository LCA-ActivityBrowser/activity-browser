DATA = {
    ("internal", "a"): {
        "name": "flow - a",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    ("internal", "😼"): {
        "type": "product",
        "name": "meow",
        "unit": "kg",
    },
    ("internal", "🐶"): {
        "type": "product",
        "name": "woof",
        "unit": "kg",
    },
    ("internal", "1"): {
        "name": "process - 1",
        "location": "first",
        "type": "multifunctional",
        "exchanges": [
            {
                "functional": True,
                "type": "production",
                "input": ("internal", "😼"),
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
                "desired_code": "first - generated",
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
                "input": ("internal", "a"),
            },
        ],
    },
    ("internal", "2"): {
        "name": "process - 2",
        "code": "2",
        "location": "second",
        "type": "multifunctional",
        "exchanges": [
            {
                "functional": True,
                "type": "production",
                "input": ("internal", "🐶"),
                "amount": 40,
                "properties": {
                    "price": 2.5,
                    "mass": 6,
                },
            },
            {
                "functional": True,
                "type": "production",
                "name": "second product - 1",
                "desired_code": "second - generated",
                "unit": "megajoule",
                "amount": 50,
                "properties": {
                    "price": 2,
                    "mass": 4,
                },
            },
            {
                "type": "technosphere",
                "amount": 10,
                "input": ("internal", "first - generated"),
            },
            {
                "type": "technosphere",
                "amount": 100,
                "input": ("internal", "😼"),
            },
        ],
    },
}
