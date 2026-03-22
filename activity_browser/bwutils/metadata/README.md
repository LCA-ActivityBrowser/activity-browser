# metadata

Metadata management for activities, databases, and methods.

## Overview

This directory handles storage, retrieval, and management of metadata associated with LCI data in Activity Browser. The MetaDataStore provides quick access to reading node data.

## Purpose

Metadata management provides:
- **In memory** - Quicker access to ranges of nodes
- **Unpacked data blob** - Unpack the data blob from the sqlite for quick access
- **Search enhancement** - Fuzzy search capabilities on metadata fields

## Metadata Types

See `fields.py` for defined metadata fields and schemas. Common types include:
- **code** - Activity codes
- **name** - Activity names
- **synonyms** - Alternative names

## Storage
Metadata is cached separately from Brightway2's native storage to allow faster access and searching. It is stored as a pickle on each flush.

## MetaDataStore

The `MetaDataStore` class (see `bwutils/metadata/`) provides centralized metadata access:

```python
from activity_browser import app

# Access metadata store
metadata = app.metadata

# Get activity metadata
meta = metadata.get_activity_metadata(activity_key)

# Update metadata
metadata.update_activity_metadata(activity_key, {"comment": "..."})
```

## Usage Pattern

### Reading Metadata
```python
meta = metadata.get_metadata(activity_key, fields=["name", "comment"])
meta = metadata.get_database_metadata(database_name, fields=["description"])
```

### Searching Metadata
```python
results = metadata.search(query="renewable energy")
```
