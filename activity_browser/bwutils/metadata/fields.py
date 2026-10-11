primary_types = {
    "key": object,
    "id": "Int64",
    "code": "str",
    "database": "str",
    "location": "str",
    "name": "str",
    "product": "str",
    "type": "str",
}
secondary_types = {
    "synonyms": object,
    "unit": "str",
    "CAS number": "str",
    "categories": object,
    "processor": object,
    "allocation": "str",
    "allocation_factor": float,
    "properties": object,
}

search_engine_whitelist = [
            "id", "name", "synonyms", "unit", "key", "database",  # generic
            "CAS number", "categories",  # biosphere specific
            "product", "reference product", "classifications", "location", "properties"  # activity specific
        ]

all_types = {**primary_types, **secondary_types}

primary = list(primary_types.keys())
secondary = list(secondary_types.keys())
all_fields = primary + secondary
