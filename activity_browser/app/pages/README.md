# pages

Main content pages displayed in the Activity Browser application.

## Overview

This directory contains the primary content pages that users interact with in Activity Browser. Each page represents a major functional area and is displayed in the central widget of the main window.

## Directory Structure

- **`activity_details/`** - Activity information display and editing
- **`calculation_setup/`** - Calculation setup configuration and management
- **`impact_category_details/`** - Impact category information and visualization
- **`lca_results/`** - LCA calculation results display and analysis
- **`parameters/`** - Parameter management and scenario configuration
- **`settings/`** - Application settings and preferences

## Key Files

- **`welcome.py`** - Welcome page shown when no project is open or on first launch
- **`metadatastore.py`** - Metadata view page (DEBUG only)

## Two types of pages

1. **Base pages** - Pages that are initialized once and remain in memory (e.g., Welcome Screen, Parameters, Settings).
   - They maintain their state and reload data on project switches.
   - Hidden/shown based on user actions or preferences in the settings.
   - Defined in `__init__.py`.
2. **Dynamic pages** - Pages that show specific data and are opened as such by the user (e.g. Activity Details, LCA results).
    - Created on demand and closed when no longer needed.
    - Multiple instances can exist (e.g., multiple activity detail pages) and will be grouped.

## Development Guidelines

When creating new pages:

- Should follow the `PageNamePage` naming convention.
- Set a unique ObjectName for identification.
- Set appropriate tab titles using `setWindowTitle()`.

## Subdirectory Details

### `activity_details/`
Display and edit activity information including:
- Basic activity data (name, location, unit, etc.)
- Exchanges (inputs/outputs)
- Parameters and formulas
- Metadata and classifications

### `calculation_setup/`
Configure and manage calculation setups:
- Reference flows (functional units)
- Impact assessment methods
- Scenario selections
- Calculation execution

### `impact_category_details/`
Show impact category information:
- Characterization factors
- Method hierarchy
- Method metadata

### `lca_results/`
Display LCA calculation results:
- Impact scores
- Contribution analyses
- Sankey diagrams
- Graph visualizations
- Export options

### `parameters/`
[BASE PAGE]

Manage parameters and scenarios:
- Project parameters
- Database parameters
- Activity parameters
- Parameter formulas
- Scenario management

### `settings/`
[BASE PAGE]

Application configuration:
- General preferences
- Project settings
- Plugin configuration
- Import/export settings
