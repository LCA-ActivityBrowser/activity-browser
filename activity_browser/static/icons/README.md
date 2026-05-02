# icons

Application icons and graphical assets.

## Overview

This directory contains all icon files used throughout Activity Browser, including the application icon, toolbar icons, menu icons, and node type indicators.

## Directory Structure

- **`main/`** - Main application icon in various sizes and formats
- **`context/`** - Context menu icons
- **`nodes/`** - Node type icons (for graph visualizations)
- **`metaprocess/`** - Meta-process related icons

## File Formats

Icons are typically provided in multiple formats:
- **PNG** - Raster format with transparency (various sizes: 16x16, 24x24, 32x32, 48x48, 256x256)
- **SVG** - Vector format (scalable without quality loss)
- **ICO** - Windows icon format (contains multiple sizes)
- **ICNS** - macOS icon format

## main/

Main application icon used for:
- Application window icon
- Taskbar/dock icon
- Desktop shortcut icon
- About dialog
- Installer icon

Sizes provided:
- 16x16 - Taskbar, title bar
- 24x24 - Small toolbar buttons
- 32x32 - Medium toolbar buttons, list views
- 48x48 - Large icons
- 256x256 - High DPI displays, splash screen
- 512x512 - macOS Retina displays

## context/

Icons for context menu actions:
- Copy
- Paste
- Delete
- Edit
- Open
- Save
- Export
- Import
- Search
- Refresh
- Settings

## nodes/

Icons representing different node types in graphs:
- Activity nodes
- Product nodes
- Biosphere flow nodes
- Technosphere flow nodes
- Waste flow nodes
- Substitution nodes

## metaprocess/

Icons for meta-process operations:
- Aggregation
- Disaggregation
- Grouping
- Filtering

## Icon Loading

Icons are loaded via `activity_browser/ui/icons.py`:

```python
from activity_browser.ui.icons import get_icon

# Load icon by name
icon = get_icon("save")

# Use in action
action = QAction(get_icon("open"), "Open", parent)

# Use in button
button = QPushButton(get_icon("delete"), "Delete")
```

## Icon Themes

Activity Browser may support multiple icon themes:
- Light theme (dark icons on light background)
- Dark theme (light icons on dark background)
- High contrast theme (for accessibility)

## Icon Design Guidelines

When creating or modifying icons:

### Size and Resolution
- Provide multiple sizes (16, 24, 32, 48, 256)
- Ensure clarity at smallest size (16x16)
- Use even dimensions for pixel-perfect rendering
- Support high DPI (2x, 3x scales)

### Style Consistency
- Match existing icon style
- Use consistent line weights
- Maintain similar level of detail
- Use the same color palette

### Visual Clarity
- Simple, recognizable shapes
- Clear at small sizes
- Sufficient contrast
- Not too much detail

### Accessibility
- Work in light and dark themes
- Sufficient contrast ratios
- Distinct shapes (not just color differences)
- Test with colorblindness simulators

### File Optimization
- Optimize PNG files (use tools like pngcrush)
- Clean up SVG files (remove unnecessary elements)
- Use transparency appropriately
- Keep file sizes small

## Color Palette

Standard colors used in Activity Browser icons:
- **Primary**: Blue (#4a90e2)
- **Success**: Green (#2ecc71)
- **Warning**: Orange (#f39c12)
- **Error**: Red (#e74c3c)
- **Info**: Cyan (#3498db)
- **Neutral**: Gray (#95a5a6)

## Platform-Specific Icons

### Windows
- Use ICO format for application icon
- Provide 16, 32, 48, 256 sizes in single ICO file
- Follow Windows icon guidelines

### macOS
- Use ICNS format for application icon
- Provide 16, 32, 128, 256, 512, 1024 sizes
- Follow macOS icon guidelines
- Support Retina displays

### Linux
- Use PNG for application icon
- Provide standard sizes: 16, 24, 32, 48, 64, 128, 256
- Follow freedesktop.org icon naming spec
- Install to appropriate directories

## Icon Attribution

If using third-party icons:
- Check license compatibility (LGPL-compatible)
- Provide attribution if required
- Document source and license
- Consider creating custom icons instead

## Tools for Icon Creation

Recommended tools:
- **Inkscape** - Free vector graphics editor (SVG)
- **GIMP** - Free raster graphics editor (PNG)
- **ImageMagick** - Batch processing and conversion
- **icon-resizer** - Generate multiple sizes from SVG

## Updating Icons

When updating icons:
1. Edit source SVG file
2. Export to required PNG sizes
3. Optimize files
4. Generate platform-specific formats (ICO, ICNS)
5. Update icons in all directories
6. Test in application on all platforms
7. Verify high DPI rendering
8. Check light and dark themes

## Icon Resources

Free icon sources (check licenses):
- [Font Awesome](https://fontawesome.com/)
- [Material Icons](https://material.io/icons/)
- [Feather Icons](https://feathericons.com/)
- [Heroicons](https://heroicons.com/)

## Testing Icons

Test icons:
- At all sizes (16px to 256px)
- On different backgrounds
- With different themes
- On high DPI displays
- On all platforms
- In actual UI contexts

## Maintenance

Keep icons:
- Up-to-date with design trends
- Consistent with application style
- Optimized for performance
- Properly licensed
- Version controlled
