# bwutils

Utility functions and helpers that extend and build upon Brightway2 functionality.

## Overview

This module provides a collection of generic methods and utilities that wrap and extend Brightway2 operations. These utilities are used throughout the Activity Browser to avoid code duplication and provide consistent interfaces to Brightway2 functionality.

## Directory Structure

- **`ecoinvent_biosphere_versions/`** - Ecoinvent biosphere database version mappings
- **`io/`** - Import/export operations for data interchange
- **`metadata/`** - Metadata loading and caching for quick access
- **`searchengine/`** - Fuzzy search functionality for dataframes
- **`superstructure/`** - Superstructure scenario analysis tools

## Key Files

- **`commontasks.py`** - Common Brightway2 operations (database management, activity operations)
- **`errors.py`** - Custom exception classes for Brightway2 operations
- **`exporters.py`** - Export functionality for databases and activities
- **`importers.py`** - Import functionality for various LCA data formats
- **`filesystem.py`** - File system operations for Brightway2 data directories
- **`parameters/`** - Parameter recalculation, Monte Carlo matrix hook, functional_sqlite identity (see `parameters/README.md`)
- **`montecarlo.py`** - Monte Carlo simulation; stores per-iteration matrix snapshots for GSA
- **`multilca.py`** - Multi-functional LCA calculation utilities
- **`pedigree.py`** - Pedigree matrix uncertainty handling
- **`sensitivity_analysis.py`** - SALib delta GSA on ``MonteCarloLCA``; ``df_final`` columns in ``GSA_COLUMNS``; runnable via ``if __name__ == "__main__"``
- **`settings.py`** - Settings specific to bwutils operations
- **`strategies.py`** - Import strategies and data transformation functions
- **`uncertainty.py`** - Uncertainty dialog interfaces; ``uncertainty_type_name`` / ``uncertainty_parameters_summary`` for GSA tables
- **`utils.py`** - General utility functions

## Purpose

The bwutils module serves as an abstraction layer between the Activity Browser UI and Brightway2, providing:

1. **Consistency** - Standardized interfaces for common operations
2. **Error Handling** - Graceful handling of Brightway2 exceptions
3. **Extensions** - Additional functionality not provided by Brightway2
4. **Integration** - Bridging between Qt UI and Brightway2 data structures

## Usage Pattern

Import utilities as needed throughout the application:

```python
from activity_browser.bwutils import commontasks
```

## Design Principle

Keep utilities generic and reusable. These functions should:
- Work with Brightway2 data structures
- Be independent of UI components
- Be testable without requiring a GUI
