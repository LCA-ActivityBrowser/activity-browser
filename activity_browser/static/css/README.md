# css

Cascading Style Sheets for Activity Browser's HTML views.

## Overview

This directory contains CSS files that style the HTML-based visualizations and web views in Activity Browser. These stylesheets control the appearance of graphs, Sankey diagrams, tree navigators, and other interactive visualizations.

## Files

- **`navigator.common.css`** - Common styles shared across navigators
- **`navigator.css`** - Base navigator styles
- **`activity_graph.css`** - Activity relationship graph styles
- **`sankey_navigator.css`** - Sankey diagram visualization styles
- **`tree_navigator.css`** - Tree structure navigator styles

## Purpose

These stylesheets provide:
- **Consistent appearance** - Unified look across all visualizations
- **Responsive design** - Adapt to different window sizes
- **Interactive styling** - Hover effects, selections, highlights
- **Theme support** - Match Activity Browser's overall design
- **Accessibility** - Readable colors, proper contrast

## Common Patterns

### Node Styling
```css
.node {
    fill: #4a90e2;
    stroke: #2c5aa0;
    stroke-width: 2px;
    cursor: pointer;
}

.node:hover {
    fill: #5da5ff;
    stroke-width: 3px;
}

.node.selected {
    stroke: #ff6b6b;
    stroke-width: 4px;
}
```

### Edge/Link Styling
```css
.link {
    stroke: #999;
    stroke-opacity: 0.6;
    fill: none;
}

.link:hover {
    stroke-opacity: 1;
    stroke-width: 3px;
}
```

### Text Styling
```css
.label {
    font-family: Arial, sans-serif;
    font-size: 12px;
    fill: #333;
    pointer-events: none;
}
```

## navigator.common.css

Shared styles for all navigators:
- Layout and positioning
- Controls and buttons
- Tooltips
- Loading indicators
- Error messages

## activity_graph.css

Styles for activity relationship graphs:
- Node appearance (activities)
- Edge appearance (exchanges/relationships)
- Labels and annotations
- Graph controls (zoom, pan)
- Legend styling

## sankey_navigator.css

Styles for Sankey diagrams:
- Flow paths (width proportional to amount)
- Node boxes
- Flow colors (by category)
- Tooltips showing values
- Legend and scale

## tree_navigator.css

Styles for tree structures:
- Tree nodes (collapsible)
- Branches/connections
- Expand/collapse icons
- Indentation levels
- Selection highlighting

## Color Schemes

### Default Colors
- **Primary**: Blue (#4a90e2)
- **Secondary**: Green (#2ecc71)
- **Warning**: Orange (#f39c12)
- **Error**: Red (#e74c3c)
- **Neutral**: Gray (#95a5a6)

### Category Colors
Different colors for flow types:
- **Technosphere**: Blue
- **Biosphere**: Green
- **Production**: Orange
- **Substitution**: Purple

## Responsive Design

Stylesheets adapt to window size:

```css
@media (max-width: 768px) {
    .node {
        /* Smaller nodes on small screens */
        r: 4px;
    }
    
    .label {
        /* Smaller text on small screens */
        font-size: 10px;
    }
}
```

## Interactive States

### Hover States
Visual feedback when hovering:
```css
.interactive:hover {
    opacity: 0.8;
    cursor: pointer;
}
```

### Selection States
Highlight selected items:
```css
.selected {
    stroke: #ff6b6b;
    stroke-width: 3px;
    filter: drop-shadow(0 0 5px rgba(255, 107, 107, 0.5));
}
```

### Disabled States
Gray out disabled elements:
```css
.disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
```

## Animations

Smooth transitions:
```css
.node {
    transition: all 0.3s ease;
}

.link {
    transition: stroke-width 0.2s ease, stroke-opacity 0.2s ease;
}
```

## Tooltips

Styled tooltips for data display:
```css
.tooltip {
    position: absolute;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    pointer-events: none;
    z-index: 1000;
}
```

## Development Guidelines

When modifying CSS:

1. **Test in web view** - Not just browser (Qt WebEngine may differ)
2. **Use CSS variables** - For easy theme changes
3. **Mobile-first** - Design for smallest screens first
4. **Performance** - Avoid expensive effects on many elements
5. **Accessibility** - Maintain contrast ratios (WCAG AA)
6. **Cross-browser** - Test in different rendering engines
7. **Documentation** - Comment complex selectors
8. **Organization** - Group related styles
9. **Naming** - Use clear, descriptive class names
10. **Validation** - Run through CSS validator

## CSS Variables

Use CSS custom properties for theming:
```css
:root {
    --primary-color: #4a90e2;
    --text-color: #333;
    --background-color: #fff;
    --hover-opacity: 0.8;
}

.node {
    fill: var(--primary-color);
}
```

## Browser Compatibility

Ensure compatibility with Qt WebEngine:
- Test rendering in actual application
- Check vendor prefixes
- Verify CSS feature support
- Test on all platforms (Windows, macOS, Linux)

## Resources

- [MDN CSS Reference](https://developer.mozilla.org/en-US/docs/Web/CSS)
- [CSS-Tricks](https://css-tricks.com/)
- [Can I Use](https://caniuse.com/) - Feature compatibility
- [D3.js Styling](https://d3js.org/) - SVG styling patterns
