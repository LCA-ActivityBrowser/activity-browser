primary_types = {
    "key": object,
    "id": "Int64",
    # object (not str): under pandas 3, builtin str → StringDtype, which rejects
    # non-strings and skips NaN→None coercion (ADR-0014 keeps object/pickle hybrid).
    "code": object,
    "database": object,
    "location": object,
    "name": object,
    "product": object,
    "type": object,
}
secondary_types = {
    "synonyms": object,
    "unit": object,
    "CAS number": object,
    "categories": object,
    "processor": object,
    "allocation": object,
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
