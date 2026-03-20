# widgets

Reusable custom widget components for the Activity Browser interface.

## Overview

This directory contains a collection of custom Qt widgets used throughout Activity Browser. These widgets extend Qt's base widgets with application-specific functionality, styling, and behavior.

## Key Files

### Abstract Base Classes
- **`abstract_page.py`** - Base class for main content area pages
- **`abstract_pane.py`** - Base class for dock-able side panels

### Layout and Container Widgets
- **`central.py`** - Central widget that holds the main content area
- **`dock_widget.py`** - Custom dock widget with additional features
- **`tab_widget.py`** - Enhanced tab widget with custom styling

### Input Widgets
- **`line_edit.py`** - Enhanced single-line text input
- **`text_edit.py`** - Multi-line text editor with additional features
- **`combobox.py`** - Drop-down selection with search and filtering
- **`formula_edit.py`** - Specialized editor for parameter formulas
- **`database_name_edit.py`** - Input widget for database names with validation

### Display Widgets
- **`label.py`** - Custom labels with additional styling options
- **`tree_view.py`** - Enhanced tree view for hierarchical data
- **`plot.py`** - Plotting widgets for charts and graphs

### Interactive Widgets
- **`buttons.py`** - Custom button variations (icon buttons, toggle buttons)
- **`button_collapser.py`** - Collapsible sections with expand/collapse buttons
- **`comparison_switch.py`** - Switch between different comparison views
- **`cutoff_menu.py`** - Menu for selecting cutoff thresholds
- **`menu.py`** - Enhanced context and popup menus

### Utility Widgets
- **`file_selector.py`** - File/directory selection with browse button
- **`drop_overlay.py`** - Visual overlay for drag-and-drop operations
- **`line.py`** - Visual separator lines

### Wizards
- **`wizard.py`** - Base wizard dialog for multi-step workflows
- **`wizard_page.py`** - Individual pages within wizards

## Widget Categories

### Page Widgets (AbstractPage)
Main content pages inherit from `AbstractPage`:
- Consistent toolbar integration
- Signal connection handling
- State management
- Layout conventions

```python
from activity_browser.ui.widgets import AbstractPage

class MyPage(AbstractPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
```

### Pane Widgets (AbstractPane)
Dock-able panes inherit from `AbstractPane`:
- Dock widget functionality
- Visibility persistence
- Resize handling
- Title bar customization

```python
from activity_browser.ui.widgets import AbstractPane

class MyPane(AbstractPane):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_content()
```

### Input Widgets
Enhanced input widgets with:
- Validation
- Placeholder text
- Clear buttons
- Auto-completion
- Format enforcement

### Display Widgets
Specialized display widgets:
- Custom rendering
- Context menus
- Copy/export functionality
- Sorting and filtering

## Common Patterns

### Signal Connections
Widgets connect to global signals:
```python
from activity_browser import app

app.signals.data_changed.connect(self.refresh)
```

### Validation
Input widgets validate data:
```python
class MyLineEdit(QLineEdit):
    def validate_input(self):
        if not self.text().strip():
            self.setStyleSheet("border: 1px solid red")
            return False
        return True
```

### Context Menus
Many widgets provide context menus:
```python
def contextMenuEvent(self, event):
    menu = QMenu(self)
    menu.addAction("Copy", self.copy_selection)
    menu.addAction("Export", self.export_data)
    menu.exec_(event.globalPos())
```

## Styling

Widgets use Qt stylesheets for consistent appearance:

```python
self.setStyleSheet("""
    QWidget {
        background-color: #ffffff;
        color: #000000;
    }
    QPushButton {
        border: 1px solid #cccccc;
        border-radius: 3px;
        padding: 5px;
    }
""")
```

## Development Guidelines

When creating custom widgets:

1. **Inherit from appropriate base class** - Use AbstractPage/AbstractPane when applicable
2. **Emit signals for state changes** - Enable other components to react
3. **Support keyboard navigation** - Implement tab order and shortcuts
4. **Provide context menus** - Right-click actions for common operations
5. **Validate input** - Check data before accepting
6. **Handle errors gracefully** - Show user-friendly error messages
7. **Use consistent styling** - Follow application design patterns
8. **Document public API** - Docstrings for public methods and signals
9. **Make widgets reusable** - Avoid hard-coding application logic
10. **Test widgets independently** - Unit tests for widget behavior

## Reusability

Widgets should be:
- **Self-contained** - Minimal external dependencies
- **Configurable** - Properties for customization
- **Composable** - Can be combined into complex UIs
- **Generic** - Not tied to specific data models

## Accessibility

Consider accessibility:
- Keyboard navigation
- Screen reader compatibility
- High contrast support
- Focus indicators
- Logical tab order

## Performance

Optimize widget performance:
- Lazy loading of data
- Virtual scrolling for large lists
- Efficient repainting
- Debounced event handlers
- Cache computed values

## Testing

Widget tests should verify:
- Initial state and defaults
- User interactions (clicks, text entry)
- Signal emission
- Validation logic
- Edge cases and error handling

Use pytest-qt for testing:
```python
def test_my_widget(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    # Test widget behavior
```
