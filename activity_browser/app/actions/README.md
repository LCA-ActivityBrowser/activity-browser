# actions

Encapsulated UI operations and commands following the action pattern.

## Overview

This directory contains all user-triggered actions in Activity Browser. Each action represents a discrete operation that can be invoked from menus, toolbars, or keyboard shortcuts.

## Directory Structure

- **`activity/`** - Actions related to activities (create, edit, delete, duplicate, etc.)
- **`calculation_setup/`** - Actions for calculation setup management
- **`database/`** - Database operations (import, export, delete, backup, etc.)
- **`exchange/`** - Actions for exchanges between activities
- **`method/`** - Impact assessment method management
- **`parameter/`** - Parameter management actions
- **`project/`** - Project-level operations
- **`tools/`** - Various tools and utilities accessible via actions

## Action Pattern

All actions follow a consistent pattern defined in `base.py`:

```python
class MyAction(ABAction):
    icon = QtGui.QIcon(...)  # Action icon
    text = "My Action"        # Display text
    tooltip = "Description"   # Tooltip text
    
    @staticmethod
    def run(*args, **kwargs):
        # Action implementation
        pass
```

### Key Features:

1. **Declarative** - Icon, text, and tooltip defined as class attributes
2. **Callable arguments** - Arguments can be functions (evaluated at runtime)
3. **Qt integration** - Can be converted to QAction or QPushButton
4. **Exception handling** - Always add `@exception_dialogs` decorator for user-facing errors
5. **Flexible invocation** - Triggered from menus, buttons, shortcuts

## Usage

Actions can be used in multiple ways:

### As Menu Items
```python
action = MyAction.get_QAction(parent=menu)
menu.addAction(action)
```

### As Buttons
```python
button = MyAction.get_QButton()
layout.addWidget(button)
```

### Direct Invocation
```python
MyAction.run(arg1, arg2)
```

## Subdirectory Organization

Each subdirectory groups related actions:

- **`activity/`** - Activity CRUD operations, navigation, graph viewing
- **`calculation_setup/`** - Setup creation, modification, calculation execution
- **`database/`** - Import from various sources, export, deletion, backup/restore
- **`exchange/`** - Add/remove/modify exchanges, uncertainty, formulas
- **`method/`** - Method import, export, modification, deletion
- **`parameter/`** - Parameter creation, editing, scenarios
- **`project/`** - Project creation, switching, deletion, settings
- **`tools/`** - Monte Carlo, sensitivity analysis, superstructure tools

## Development Guidelines

When adding new actions:

1. Inherit from `ABAction` base class
2. Define icon, text, and tooltip class attributes
3. Implement the `run()` static method with the action logic
4. Place in the appropriate subdirectory by functionality
5. Use `@exception_dialogs` decorator for user-facing error handling
6. Import and register in the parent `__init__.py`
7. Connect to global signals when state changes

## Signal Integration

**Actions should not emit signals themselves** That being said, actions should only emit signals when they modify state in a way that Brightway2 does not automatically notify the UI about. See e.g. parameter_group_delete.py for an example of emitting a signal after deleting a parameter group.
