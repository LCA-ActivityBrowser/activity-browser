# activity_browser_beta

Beta version package for Activity Browser.

## Overview

This is a separate package for the Activity Browser beta version (Version 3.0). It allows users to install and test beta features alongside the stable version without conflicts.

## Purpose

The beta package:
- **Parallel Installation** - Can coexist with stable version
- **Early Access** - Test new features before general release
- **Feedback** - Help improve Activity Browser through testing
- **Brightway 2.5** - Uses the latest Brightway version

## Key Features in Beta

- **Brightway 2.5 support** - Uses the latest Brightway framework
- **Multi-functionality** - Enhanced support for multi-functional processes
- **Improved performance** - Optimizations for large databases
- **New UI elements** - Updated interface components
- **Enhanced calculations** - Better calculation setup and management

## Installation

### From conda-forge
```bash
conda install -c conda-forge activity-browser-beta
```

### Alongside Stable Version
Both versions can be installed in different environments:

```bash
# Stable version in one environment
conda create -n ab-stable -c conda-forge activity-browser

# Beta version in another environment
conda create -n ab-beta -c conda-forge activity-browser-beta
```

## Running Beta

Launch the beta version:
```bash
activity-browser-beta
```

Or from Python:
```python
from activity_browser_beta import run_activity_browser
run_activity_browser()
```

## Package Structure

The `__init__.py` file likely re-exports or wraps the main activity_browser package with beta-specific configurations or modifications.

## Data Compatibility

### Projects
Beta may create or modify projects in ways incompatible with stable:
- **Separate projects** - Use different project names for beta testing
- **Backup first** - Always backup projects before testing beta
- **One-way migration** - Some changes may not be reversible

### Databases
- Beta may support features not available in stable
- Database format changes may prevent opening in stable version
- Export/import may be needed to move data between versions

## Reporting Issues

Report beta issues on GitHub:
- Label issues with "beta" tag
- Specify you're using the beta version
- Include version number from Help → About
- Describe expected vs actual behavior
- Provide steps to reproduce

## Transitioning to Stable

When beta becomes stable:
1. Beta features are merged into main release
2. activity-browser-beta package is deprecated
3. Users migrate to standard activity-browser package
4. Projects created in beta work in new stable version

## Development

The beta package is typically:
- Built from a beta branch in the repository
- Tagged with beta version numbers (e.g., 3.0.0b1)
- Distributed via conda-forge beta channel
- Updated more frequently than stable

## Feedback

Help improve Activity Browser by:
- Testing new features
- Reporting bugs
- Suggesting improvements
- Comparing with stable version
- Documenting workflows

Submit feedback:
- GitHub Issues: https://github.com/LCA-ActivityBrowser/activity-browser/issues
- Discussions: https://github.com/LCA-ActivityBrowser/activity-browser/discussions
- Email maintainers

## Documentation

Beta documentation is available at:
https://lca-activitybrowser.github.io/activity-browser/beta.html

## Caution

Beta software:
- **May have bugs** - Expect issues
- **May change** - Features may be modified or removed
- **May be unstable** - Crashes possible
- **Not for production** - Don't use for critical work
- **Data loss risk** - Always backup your data

## Best Practices

When testing beta:
1. **Create test projects** - Don't use real project data
2. **Backup everything** - Projects, databases, custom data
3. **Document issues** - Take notes on problems
4. **Compare with stable** - Verify behavior differences
5. **Separate environments** - Use dedicated conda environment
6. **Stay updated** - Check for beta updates regularly
7. **Read release notes** - Understand what changed
8. **Provide feedback** - Share your experience

## Version Numbering

Beta versions use pre-release identifiers:
- `3.0.0b1` - First beta
- `3.0.0b2` - Second beta
- `3.0.0rc1` - Release candidate
- `3.0.0` - Stable release

## Support

Beta support:
- Community support via GitHub Discussions
- Issue tracker for bug reports
- Limited email support
- Self-service documentation

Remember: Beta software is experimental. Use at your own risk and always maintain backups of important data.
