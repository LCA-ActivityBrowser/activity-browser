# static

Static resources for the Activity Browser application.

## Overview

This directory contains all static assets used by Activity Browser including HTML templates, stylesheets, icons, fonts, JavaScript libraries, and other non-code resources.

## Directory Structure

- **`css/`** - Cascading Style Sheets for HTML views
- **`database_classifications/`** - Database classification mappings and schemas
- **`fonts/`** - Font files used in the application
- **`icons/`** - Application icons in various formats and sizes
- **`javascript/`** - JavaScript libraries and scripts for web views
- **`startscreen/`** - Start screen assets and templates

## HTML Templates

- **`activity_graph.html`** - Template for activity relationship graph visualization
- **`navigator.html`** - Base navigator template
- **`sankey_navigator.html`** - Sankey diagram visualization template
- **`spinner.html`** - Loading spinner template
- **`tree_navigator.html`** - Tree structure navigator template

## Purpose

These static resources support:

1. **Visualization** - Interactive graphs, Sankey diagrams, and charts
2. **Branding** - Application icons and logo
3. **Styling** - Consistent look and feel across web views
4. **Classification** - Database and activity classification systems
5. **User Experience** - Welcome screens, loading indicators, navigation

## Web Views

Activity Browser embeds web views (Qt WebEngine) for rich interactive visualizations. These HTML templates use JavaScript libraries to render:

- Force-directed graphs showing activity relationships
- Sankey diagrams for flow visualization
- Tree navigators for hierarchical data exploration
- Interactive charts and plots

## Resource Loading

Static resources are accessed via:

```python
from pathlib import Path

static_dir = Path(__file__).parent.resolve() / "static"
icon_path = static_dir / "icons" / "main_icon.png"
```

## Maintenance

When adding new static resources:
- Place files in the appropriate subdirectory
- Ensure proper licensing for third-party assets
- Optimize file sizes (compress images, minify CSS/JS)
- Document dependencies and versions for JavaScript libraries
- Include resources in `MANIFEST.in` for packaging
