# tests

Test suite for Activity Browser.

## Overview

This directory contains the test suite for Activity Browser using pytest. Tests verify functionality, catch regressions, and ensure code quality across the application.

## Test Framework

**pytest** is used as the test runner with extensions:
- **pytest-qt** - Testing Qt applications
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities

## Directory Structure

- **`actions/`** - Tests for action classes
- **`fixtures/`** - Test fixtures and mock data
- **`widgets/`** - Tests for UI widgets
- Additional test files for various modules

## Key Files

- **`conftest.py`** - Pytest configuration and shared fixtures
- **`test_search.py`** - Search engine tests

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_search.py
```

### Run Specific Test
```bash
pytest tests/test_search.py::test_search_basic
```

### Run with Coverage
```bash
pytest --cov=activity_browser --cov-report=html
```

### Run in Parallel
```bash
pytest -n auto
```

## Test Categories

### Unit Tests
Test individual functions and classes in isolation:
```python
def test_function():
    result = my_function(input_data)
    assert result == expected_output
```

### Integration Tests
Test interaction between components:
```python
def test_database_import():
    # Test full import workflow
    importer.load_file(test_file)
    assert database_exists("test_db")
```

### UI Tests
Test Qt widgets and interactions:
```python
def test_button_click(qtbot):
    widget = MyWidget()
    qtbot.addWidget(widget)
    qtbot.mouseClick(widget.button, Qt.LeftButton)
    assert widget.clicked is True
```

### Action Tests
Test action classes:
```python
def test_delete_action():
    DeleteAction.run(item_key)
    assert not item_exists(item_key)
```

## Fixtures

Fixtures provide test data and setup (see `conftest.py` and `fixtures/`):

### Common Fixtures
```python
@pytest.fixture
def sample_activity():
    """Provide a sample activity for testing."""
    return {
        "name": "Test Activity",
        "unit": "kg",
        "location": "GLO"
    }

def test_with_fixture(sample_activity):
    # Use fixture
    assert sample_activity["unit"] == "kg"
```

### Brightway Fixtures
```python
@pytest.fixture
def bw_project(tmp_path):
    """Create temporary Brightway project."""
    bd.projects.set_current("test_project")
    yield
    bd.projects.delete_project("test_project", delete_dir=True)
```

### Qt Fixtures
```python
@pytest.fixture
def qtbot(qtbot):
    """Pytest-qt bot for widget testing."""
    return qtbot
```

## Writing Tests

### Test Naming
- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Test Structure
```python
def test_something():
    # Arrange - Set up test data
    data = prepare_test_data()
    
    # Act - Execute the code being tested
    result = function_under_test(data)
    
    # Assert - Verify the result
    assert result == expected_value
```

### UI Test Example
```python
def test_widget_interaction(qtbot):
    # Create widget
    widget = MyWidget()
    qtbot.addWidget(widget)
    
    # Simulate user input
    qtbot.keyClicks(widget.input_field, "test text")
    qtbot.mouseClick(widget.submit_button, Qt.LeftButton)
    
    # Verify result
    assert widget.result_label.text() == "Success"
```

### Action Test Example
```python
def test_create_database_action(bw_project):
    # Setup
    db_name = "test_database"
    
    # Execute action
    CreateDatabaseAction.run(db_name)
    
    # Verify
    assert db_name in bd.databases
```

## Mocking

Use mocks to isolate tests:

```python
from unittest.mock import Mock, patch

def test_with_mock(mocker):
    # Mock external dependency
    mock_api = mocker.patch("module.api_call")
    mock_api.return_value = {"status": "success"}
    
    # Test code
    result = my_function()
    
    # Verify mock was called
    mock_api.assert_called_once()
    assert result["status"] == "success"
```

## Testing Signals

Test Qt signals and slots:

```python
def test_signal_emission(qtbot):
    widget = MyWidget()
    
    # Use signal spy
    with qtbot.waitSignal(widget.data_changed, timeout=1000):
        widget.modify_data()
    
    # Signal was emitted
```

## Testing Threads

Test background operations:

```python
def test_threaded_operation(qtbot):
    widget = MyWidget()
    
    # Wait for thread to complete
    with qtbot.waitSignal(widget.operation_complete, timeout=5000):
        widget.start_operation()
    
    assert widget.result is not None
```

## Test Coverage

Aim for high coverage:
- **Critical paths** - 100% coverage
- **Business logic** - >90% coverage
- **UI code** - >70% coverage
- **Utilities** - >80% coverage

View coverage report:
```bash
pytest --cov=activity_browser --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Scheduled runs

See `.github/workflows/main.yaml` for CI configuration.

## Development Guidelines

When writing tests:

1. **Test behavior, not implementation** - Test what, not how
2. **One assertion per test** - Or at least one logical check
3. **Descriptive names** - Test names should explain what they test
4. **Independent tests** - Tests should not depend on each other
5. **Fast tests** - Keep tests quick (mock slow operations)
6. **Readable tests** - Tests are documentation
7. **Test edge cases** - Not just happy paths
8. **Use fixtures** - Reuse common setup
9. **Mock external dependencies** - Don't rely on network, files, etc.
10. **Clean up** - Use fixtures or teardown to clean up

## Debugging Tests

### Run with output
```bash
pytest -s  # Show print statements
pytest -v  # Verbose output
pytest -vv  # Very verbose
```

### Run single test with debugger
```bash
pytest --pdb tests/test_file.py::test_function
```

### Show test durations
```bash
pytest --durations=10  # Slowest 10 tests
```

## Test Organization

Group related tests:

```python
class TestDatabaseOperations:
    def test_create_database(self):
        pass
    
    def test_delete_database(self):
        pass
    
    def test_copy_database(self):
        pass
```

Use parametrize for similar tests:

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected
```

## Best Practices

- **Test first** - Write tests before or alongside code
- **Small tests** - Each test should verify one thing
- **Clear assertions** - Make expected values obvious
- **No logic in tests** - Tests should be straightforward
- **Fail fast** - Catch issues early in the test
- **Document complex tests** - Add comments for clarity
- **Keep tests updated** - Refactor tests with code
- **Review test failures** - Don't ignore failing tests
