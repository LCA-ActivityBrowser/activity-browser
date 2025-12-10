# mod

Monkey-patches and modifications to third-party libraries used by Activity Browser.

## Overview

This module contains patches and modifications to external libraries to fix bugs, add features, or adapt functionality for Activity Browser's specific needs. These modifications are applied at import time.

## Directory Structure

- **`bw2analyzer/`** - Patches for brightway2-analyzer
- **`bw2io/`** - Patches for brightway2-io
- **`ecoinvent_interface/`** - Patches for ecoinvent-interface
- **`peewee/`** - Patches for peewee ORM
- **`pyprind/`** - Patches for pyprind progress bars
- **`tqdm/`** - Patches for tqdm progress bars

## Key Files

- **`__init__.py`** - Imports all patched modules, replacing the original imports
- **`patching.py`** - Core patching utilities and helpers

## How It Works

When Activity Browser imports this module, it automatically imports the patched versions of external libraries. These patches are typically applied to:

1. **Fix bugs** that haven't been addressed upstream
2. **Add Qt integration** for progress bars and UI elements
3. **Adapt functionality** to work better within a GUI context
4. **Add features** needed by Activity Browser but not available in the base libraries

## Import Pattern

The module is imported early in Activity Browser's initialization:

```python
import activity_browser.mod.bw2analyzer as bw2analyzer
import activity_browser.mod.bw2io as bw2io
```

This ensures that the patched versions are used throughout the application.

## Development Notes

- Patches should be minimally invasive
- Document why each patch is needed
- Consider contributing fixes upstream when appropriate
- Test patches thoroughly as they modify external library behavior
- Keep patches up-to-date with upstream library versions

## Warning

Modifying third-party libraries can lead to maintenance challenges. Use this approach sparingly and only when:
- The issue can't be solved in Activity Browser code
- Upstream changes are not accepted or released
- The modification is essential for Activity Browser functionality

Always prefer upstream contributions over local patches when possible.
