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
- **`metadatastore.py`** - Metadata management page

## Page Architecture

Pages inherit from `AbstractPage` (in `ui/widgets/abstract_page.py`) which provides:
- Consistent layout structure
- Signal connections
- Toolbar integration
- State management

## Page Lifecycle

1. **Creation** - Page is instantiated and added to the main window
2. **Display** - User navigates to the page (shown in central widget)
3. **Updates** - Page responds to signals and refreshes data
4. **Interaction** - User performs actions within the page
5. **Persistence** - Page state may be saved when switching away

## Common Page Features

### Toolbars
Most pages include a toolbar with actions:
```python
self.toolbar = QToolBar()
self.toolbar.addAction(MyAction.get_QAction())
```

### Data Display
Pages typically contain:
- Tables showing lists of items
- Tree views for hierarchical data
- Charts and plots for visualizations
- Forms for data entry

### Signal Handling
Pages connect to global signals:
```python
from activity_browser import app

app.signals.database_changed.connect(self.update_content)
```

## Page Navigation

Users navigate between pages via:
- Menu bar (View menu)
- Toolbar buttons
- Context menus
- Actions triggered by events (e.g., double-click activity → show details)

## Development Guidelines

When creating new pages:

1. **Inherit from AbstractPage** - Use the base class for consistency
2. **Set page title** - Provide a clear, descriptive title
3. **Create toolbar** - Add relevant actions for the page
4. **Connect signals** - Listen for relevant application events
5. **Handle updates** - Refresh data when underlying state changes
6. **Manage state** - Save/restore page state when appropriate
7. **Use threading** - Long operations should not block the UI

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
Manage parameters and scenarios:
- Project parameters
- Database parameters
- Activity parameters
- Parameter formulas
- Scenario management

### `settings/`
Application configuration:
- General preferences
- Project settings
- Plugin configuration
- Import/export settings
