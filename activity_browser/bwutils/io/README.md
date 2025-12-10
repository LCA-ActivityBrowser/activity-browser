# io

Import and export operations for LCA data interchange.

## Overview

This directory handles import and export operations for various LCA data formats, enabling data exchange between Activity Browser, Brightway2, and other LCA tools.

## Purpose

The io module provides:
- **Import** - Bring data from external sources into Brightway2
- **Export** - Save Brightway2 data to various formats
- **Conversion** - Transform between different LCA data formats
- **Validation** - Check data integrity during import/export

## Supported Formats

### Import Formats
- **ecospold1/2** - Ecoinvent XML formats
- **SimaPro CSV** - SimaPro export format
- **Excel** - Custom Excel templates
- **JSON-LD** - Linked data format
- **ILCD** - International Reference Life Cycle Data System
- **Brightway2 packages** - BW2Package format

### Export Formats
- **Excel** - Various Excel export templates
- **CSV** - Comma-separated values
- **Brightway2 packages** - For backup and sharing
- **SimaPro CSV** - For use in SimaPro

## Architecture

Import/export operations typically follow this pattern:

1. **Selection** - User selects file(s) to import or export location
2. **Configuration** - Set options (database name, linking strategies, etc.)
3. **Processing** - Parse/transform data (often in a worker thread)
4. **Validation** - Check for errors or warnings
5. **Completion** - Write to database or save to file
6. **Feedback** - Report success, errors, or warnings to user

## Threading

Import/export operations use worker threads to avoid blocking the UI:

```python
from activity_browser.ui.core.threading import ABThread

worker = ABThread(import_function, args)
worker.finished.connect(on_complete)
worker.start()
```

## Error Handling

Robust error handling is critical:
- Validate data before processing
- Provide clear error messages
- Allow partial success when possible
- Log errors for debugging
- Don't lose user data on failure

## Usage Pattern

```python
from activity_browser.bwutils.io import import_ecospold2

# Import with progress tracking
result = import_ecospold2(
    filepath="data.ecospold",
    database_name="my_database",
    progress_callback=update_progress
)
```

## Integration with Actions

Import/export is typically triggered via actions:

```python
from activity_browser.app.actions.base import ABAction

class ImportEcospold(ABAction):
    @staticmethod
    def run():
        # File selection dialog
        filepath = get_file_path()
        # Import in background thread
        import_data(filepath)
```

## Development Guidelines

When adding new import/export functionality:

1. **Use worker threads** - Don't block the UI
2. **Provide progress updates** - Keep user informed
3. **Validate data** - Check before committing
4. **Handle errors gracefully** - Give helpful error messages
5. **Support cancellation** - Allow user to abort long operations
6. **Log operations** - Help with debugging
7. **Test with real data** - Use actual LCA databases for testing
8. **Document format specifics** - Note any format peculiarities or limitations

## Strategies

Import operations often use strategies to link exchanges:
- Match by name and location
- Match by code/UUID
- Match by CAS number
- Fuzzy matching
- Manual linking fallback

See `bwutils/strategies.py` for strategy implementations.
