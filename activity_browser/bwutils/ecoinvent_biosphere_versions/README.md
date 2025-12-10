# ecoinvent_biosphere_versions

Ecoinvent biosphere database version mappings and compatibility information.

## Overview

This directory manages compatibility between different versions of ecoinvent databases and their corresponding biosphere flows. It ensures that biosphere flows are correctly linked when importing ecoinvent databases.

## Key Files

- **`compatible_ei_versions.txt`** - List of compatible ecoinvent versions
- **`ecospold2biosphereimporter.py`** - Custom importer for ecospold2 biosphere flows
- **`legacy_biosphere/`** - Legacy biosphere flow definitions for older ecoinvent versions

## Purpose

Ecoinvent databases come in different versions (e.g., 3.6, 3.7, 3.8, 3.9), and each version may have:
- Different biosphere flow definitions
- Updated flow names or properties
- New or deprecated flows
- Different CAS numbers or UUIDs

This module ensures:
- **Correct linking** - Activities link to the right biosphere flows
- **Version compatibility** - Handle differences between ecoinvent versions
- **Migration support** - Update flows when upgrading ecoinvent versions
- **Legacy support** - Work with older databases

## Compatible Versions

The `compatible_ei_versions.txt` file lists ecoinvent versions that Activity Browser supports. Typically includes:
- ecoinvent 3.5
- ecoinvent 3.6
- ecoinvent 3.7
- ecoinvent 3.8
- ecoinvent 3.9
- ecoinvent 3.10

## Biosphere Flow Linking

When importing an ecoinvent database:

1. **Detect version** - Identify ecoinvent version from metadata
2. **Load biosphere** - Use appropriate biosphere flow set
3. **Link flows** - Match elementary flows to biosphere database
4. **Handle mismatches** - Resolve or report linking issues

## ecospold2biosphereimporter.py

Custom importer that:
- Extends brightway2-io's ecospold2 importer
- Handles version-specific biosphere flows
- Applies migration strategies
- Fixes known issues in ecoinvent data

## Legacy Biosphere

The `legacy_biosphere/` directory contains:
- Flow definitions from older ecoinvent versions
- Migration mappings between versions
- Deprecated flow information
- Compatibility patches

## Usage Pattern

Typically used automatically during import:

```python
from activity_browser.bwutils.importers import import_ecoinvent

# Import will automatically handle biosphere version
import_ecoinvent(
    filepath="ecoinvent_38_cutoff.ecospold",
    database_name="ecoinvent 3.8"
)
```

## Version Detection

Ecoinvent version is detected from:
- File metadata in ecospold files
- Database description field
- Version field in activity metadata
- Directory/file naming patterns

## Handling Version Mismatches

When biosphere versions don't match:

1. **Automatic migration** - Update flow references
2. **Manual linking** - User selects correct flows
3. **Warning messages** - Inform user of issues
4. **Fallback matching** - Use fuzzy matching as last resort

## Development Guidelines

When adding support for new ecoinvent versions:

1. **Update compatible versions** - Add to `compatible_ei_versions.txt`
2. **Test import** - Verify all flows link correctly
3. **Document changes** - Note any flow changes from previous version
4. **Add migrations** - If flows changed, add migration strategies
5. **Update tests** - Add test for new version

## Common Issues

### Unlinked Flows
If flows don't link:
- Check ecoinvent version detection
- Verify biosphere database version
- Review flow names for changes
- Check for typos or encoding issues

### Wrong Flow Versions
If using wrong flow set:
- Verify version detection logic
- Check metadata parsing
- Update version mapping

### Missing Flows
If flows are missing:
- Check if flows were added in newer ecoinvent version
- Verify biosphere database is up-to-date
- Add manual definitions if needed

## Maintenance

Keep up-to-date with:
- New ecoinvent releases
- Biosphere flow changes
- Brightway2 updates
- User-reported issues

## Resources

- [ecoinvent website](https://ecoinvent.org/)
- [ecoinvent version history](https://ecoinvent.org/the-ecoinvent-database/data-releases/)
- [brightway2-io documentation](https://docs.brightway.dev/projects/brightway2-io/)
