# Changelog

## [Unreleased]

### Added

- It is now possible to unpack tuple columns in the `MetaDataStore`, creating additional columns.

### Changed

- Documented `MLCA` and `Contributions` classes according to [numpydoc](https://numpydoc.readthedocs.io/en/latest/) standards.
- Importing the `biosphere3` database now casts all `categories` values to tuples.
- Added methods to `MetaDataStore` class to simplify handling of the dataframe object inside.

### Fixed

- Cleaning up removed project directories ([#194](https://github.com/LCA-ActivityBrowser/activity-browser/issues/194), [#198](https://github.com/LCA-ActivityBrowser/activity-browser/pull/198)) can now be done by running the `activity-browser-cleanup` command in the anaconda prompt.

## [2.3.1] - 2019-04-15

### Fixed

- Travis now correctly receives and handles a version tag.

## [2.3.0] - 2019-04-12

### Changed

- Major overhaul of the GUI. See [#218](https://github.com/LCA-ActivityBrowser/activity-browser/pull/218) for details.
- New conda stable and development builds (`activity-browser`, `activity-browser-dev`) can now be found in the `bsteubing` [channel](https://anaconda.org/bsteubing/).
