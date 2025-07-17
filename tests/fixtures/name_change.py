DATA = {
    ("name_change", "a"): {
        "name": "flow - a",
        "code": "a",
        "unit": "kg",
        "type": "emission",
        "categories": ("air",),
    },
    ("name_change", "1"): {
        "name": "MFP: Longer name because like⧺Long name look here wut",
        "code": "1",
        "location": "first",
        "type": "multifunctional",
        "exchanges": [
            {
                "functional": True,
                "type": "production",
                "name": "Longer name because like reasons",
                "desired_code": "first - generated",
                "amount": 4,
                "properties": {
                    "price": 7,
                    "mass": 6,
                },
            },
            {
                "functional": True,
                "type": "production",
                "name": "Long name look here wut, wut",
                "desired_code": "second - generated",
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
                "input": ("name_change", "a"),
            },
        ],
    },
}
