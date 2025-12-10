# bw2analyzer

Monkey-patches for brightway2-analyzer library.

## Overview

This directory contains modifications and patches to the brightway2-analyzer library. These patches fix bugs, add features, or adapt functionality specifically for Activity Browser's needs.

## Key Files

- **`contribution.py`** - Patches for contribution analysis functions
- **`__init__.py`** - Module initialization and patch application

## Purpose

Brightway2-analyzer provides LCA analysis tools including:
- Contribution analysis
- Graph traversal
- Tagged exchanges
- Monte Carlo analysis helpers

Activity Browser patches this library to:
- Fix issues not yet addressed upstream
- Add GUI-specific functionality
- Improve performance for interactive use
- Handle edge cases

## Contribution Analysis Patches

The `contribution.py` file likely patches contribution analysis to:
- Handle large result sets more efficiently
- Provide progress callbacks for GUI
- Fix calculation edge cases
- Add sorting and filtering options
- Improve memory usage

## Common Patches

### Progress Callbacks
Add callbacks for long-running operations:
```python
def contribution_analysis(lca, progress_callback=None):
    # Original function doesn't support callbacks
    # Patch adds progress updates for GUI
    for i, item in enumerate(items):
        if progress_callback:
            progress_callback(i / len(items) * 100)
        # ... process item
```

### Error Handling
Improve error messages for GUI context:
```python
def patched_function(*args, **kwargs):
    try:
        return original_function(*args, **kwargs)
    except Exception as e:
        # Convert to user-friendly error
        raise ABError(f"Analysis failed: {str(e)}")
```

### Performance Optimizations
Speed up operations for interactive use:
```python
def optimized_function(data):
    # Add caching for repeated calls
    cache_key = hash_data(data)
    if cache_key in cache:
        return cache[cache_key]
    result = expensive_operation(data)
    cache[cache_key] = result
    return result
```

## Patch Application

Patches are applied when the module is imported:

```python
# In activity_browser/mod/__init__.py
import activity_browser.mod.bw2analyzer as bw2analyzer
```

This replaces the original bw2analyzer with the patched version.

## Development Guidelines

When adding patches:

1. **Minimal changes** - Only patch what's necessary
2. **Document reasons** - Explain why each patch is needed
3. **Track upstream** - Monitor if fix is applied upstream
4. **Version awareness** - Handle different bw2analyzer versions
5. **Test thoroughly** - Ensure patches don't break existing functionality
6. **Consider alternatives** - Can it be done in AB code instead?

## Contribution Analysis

Typical contribution analysis patches might include:

### Cutoff Support
```python
def contribution_analysis(lca, cutoff=0.01):
    """Add cutoff parameter to limit results."""
    # Original doesn't support cutoff
    # Patch filters results below threshold
```

### Sorting Options
```python
def contribution_analysis(lca, sort_by='amount'):
    """Add sorting parameter."""
    # Original returns unsorted
    # Patch adds sorting by amount, name, or impact
```

### Result Formatting
```python
def contribution_analysis(lca, format='dict'):
    """Control output format."""
    # Original returns specific format
    # Patch allows choosing format (dict, list, DataFrame)
```

## Testing Patches

Test patches with:
- Unit tests for patched functions
- Integration tests with real LCA data
- Comparison with original behavior
- Edge cases and error conditions
- Performance benchmarks

## Maintenance

When updating Activity Browser:

1. **Check brightway2-analyzer version** - New version may fix issues
2. **Review patches** - Are they still needed?
3. **Test compatibility** - Ensure patches work with new version
4. **Update if needed** - Adjust patches for API changes
5. **Contribute upstream** - Submit fixes to brightway2-analyzer

## Alternative to Patching

Instead of patching, consider:
- Wrapping functions in AB code
- Using composition instead of modification
- Contributing fixes directly to brightway2
- Using configuration/options if available

Patching should be last resort when:
- Upstream fix is not available
- Functionality is GUI-specific
- Performance optimization is needed
- Workaround is required

## Risks of Patching

Be aware that patches:
- May break with upstream updates
- Can cause confusion (behavior differs from docs)
- Require maintenance
- May conflict with other patches
- Complicate debugging

## Documentation

Always document:
- What is patched
- Why it's patched
- When it can be removed
- Any side effects
- Upstream issue tracking

## Contributing Upstream

When possible, contribute patches upstream:
1. Open issue on brightway2-analyzer
2. Propose fix or enhancement
3. Submit pull request
4. Maintain patch until merged
5. Remove patch once in released version

This benefits the entire Brightway community and reduces AB maintenance burden.
