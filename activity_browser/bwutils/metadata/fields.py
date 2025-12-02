primary_types = {
    "key": object,
    "id": "int64",
    "code": str,
    "database": "category",
    "location": "category",
    "name": str,
    "product": object,
    "type": "category",
}
secondary_types = {
    "synonyms": object,
    "unit": "category",
    "CAS number": "category",
    "categories": object,
    "processor": object,
    "allocation": "category",
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
all = primary + secondary
