# metadata

Metadata management for activities, databases, and methods.

## Overview

This directory handles storage, retrieval, and management of metadata associated with LCI data in Activity Browser. The MetaDataStore provides quick access to reading node data.

## Design principle

**Prefer the MetaDataStore for activity metadata reads.** `app.metadata` is already loaded in memory. Do not query Brightway SQLite (`ActivityDataset`) or `bd.get_node` for display labels (name, product, location, unit, database, …) when the store has the row.

- **Reads:** `app.metadata.get_metadata(keys, columns)` by `(database, code)`, or filter `app.metadata.dataframe` on the `id` column (Brightway datapackage id).
- **Writes:** mutate via Brightway APIs (actions). The store updates from bw signals.
- **Fallback:** Brightway only if the row or field is missing from the store, or you need a live activity proxy (exchanges, save).
- **`bwutils/`:** pass `app.metadata.dataframe` (or a lookup callback) into helpers. Do not import the `app` singleton from `bwutils/`.

See `docs/adr/0005-metadata-from-metadatastore.md`.

## Purpose

Metadata management provides:
- **In memory** - Quicker access to ranges of nodes
- **Unpacked data blob** - Unpack the data blob from the sqlite for quick access
- **Search enhancement** - Fuzzy search capabilities on metadata fields

## Metadata Types

See `fields.py` for defined metadata fields and schemas. Common types include:
- **id** - Brightway datapackage id
- **code** - Activity codes
- **name** - Activity names
- **product** - Reference product
- **synonyms** - Alternative names

## Storage
Metadata is cached separately from Brightway2's native storage to allow faster access and searching. It is stored as a pickle on each flush.

## MetaDataStore

The `MetaDataStore` class provides centralized metadata access. Index is `(database, code)`.

```python
from activity_browser import app

metadata = app.metadata

# By activity key (database, code)
meta = metadata.get_metadata([("db", "code")], ["name", "product", "location", "unit"])

# By datapackage id (contribution tree, graph traversal, …)
row = metadata.dataframe.loc[metadata.dataframe["id"] == activity_id]
```

## Usage Pattern

### Reading Metadata
```python
meta = metadata.get_metadata(activity_keys, columns=["name", "product", "location"])
meta = metadata.get_database_metadata(database_name, columns=["name", "product"])
```

### Searching Metadata
```python
results = metadata.search(query="renewable energy")
```
