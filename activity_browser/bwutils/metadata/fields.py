primary_types = {
    "key": object,
    "id": "int64",
    "code": str,
    "database": "category",
    "location": "category",
    "name": str,
    "product": str,
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
}
all_types = {**primary_types, **secondary_types}

primary = list(primary_types.keys())
secondary = list(secondary_types.keys())
all = primary + secondary
