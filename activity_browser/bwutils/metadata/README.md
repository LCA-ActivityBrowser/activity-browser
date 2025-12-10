# metadata

Metadata management for activities, databases, and methods.

## Overview

This directory handles storage, retrieval, and management of metadata associated with LCA data in Activity Browser. Metadata provides additional context and information beyond what Brightway2 stores natively.

## Purpose

Metadata management provides:
- **Extended information** - Additional fields beyond Brightway2 schema
- **User annotations** - Comments, tags, custom fields
- **Workflow tracking** - Modification history, authorship
- **Search enhancement** - Additional searchable attributes
- **Classification** - Custom categorization schemes

## Metadata Types

### Activity Metadata
- Custom descriptions
- Data quality assessments
- Pedigree matrices
- User comments
- Modification timestamps
- Authorship information

### Database Metadata
- Database descriptions
- Source information
- Version tracking
- Import history
- Licensing information

### Method Metadata
- Method descriptions
- Methodological choices
- References and sources
- Uncertainty information

## Storage

Metadata is stored separately from Brightway2's native storage:
- JSON files in user data directory
- Keyed by activity/database/method identifiers
- Persisted across sessions
- Backed up with projects

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
meta = metadata.get_metadata(item_key)
comment = meta.get("comment", "")
```

### Writing Metadata
```python
metadata.update_metadata(item_key, {
    "comment": "Updated description",
    "modified": datetime.now().isoformat(),
    "author": "user@example.com"
})
```

### Searching Metadata
```python
results = metadata.search(query="renewable energy")
```

## Signal Integration

Metadata changes emit signals:

```python
from activity_browser import app

app.signals.metadata_changed.emit(item_key)
```

Other components can listen and update their displays accordingly.

## Development Guidelines

When working with metadata:

1. **Use the MetaDataStore** - Don't create separate storage
2. **Emit signals** - Notify when metadata changes
3. **Validate schemas** - Ensure metadata structure is consistent
4. **Handle missing data** - Provide sensible defaults
5. **Consider performance** - Cache frequently accessed metadata
6. **Backup regularly** - Metadata is user-created content
7. **Version metadata format** - Support migration if schema changes

## Data Structure

Typical metadata structure:

```json
{
  "comment": "User-provided description",
  "tags": ["renewable", "electricity"],
  "data_quality": {
    "reliability": 3,
    "completeness": 4,
    "temporal_correlation": 2
  },
  "modified": "2025-12-10T10:30:00",
  "author": "user@example.com",
  "custom_fields": {
    "project_code": "ABC123"
  }
}
```

## Integration with UI

Metadata is displayed and edited through:
- Activity details page
- Database properties dialog
- Method information panel
- Custom metadata editor dialogs

Users can add, edit, and delete metadata through these interfaces.
