# Changelog

## [Unreleased]

### Added

- ([#259](https://github.com/LCA-ActivityBrowser/activity-browser/pull/259)) Subclassed the `Icons` class into `QIcons` which directly returns QIcon objects of the icon figures. 

### Changed

- ([#256](https://github.com/LCA-ActivityBrowser/activity-browser/pull/256)) Do not open the activity tab for activities without a product (ie. biosphere flows).
  - Includes tests!
- ([#258](https://github.com/LCA-ActivityBrowser/activity-browser/pull/258), [#261](https://github.com/LCA-ActivityBrowser/activity-browser/pull/261)) Refactor the dataframe Model/View code to allow a lot of customization.

### Fixed

- ([#246](https://github.com/LCA-ActivityBrowser/activity-browser/pull/246)) Added a workaround for running LCA on databases with missing or unset uncertainty.
- ([#262](https://github.com/LCA-ActivityBrowser/activity-browser/pull/262)) Database will no longer be deleted if the user selects `No` in the `delete_database` question dialog.
- ([#263](https://github.com/LCA-ActivityBrowser/activity-browser/pull/263)) Add separate check of `database_changed` signal to ensure the correct table is refreshed. 

## [2.3.2] - 2019-07-03

### Added

- It is now possible to unpack tuple columns in the `MetaDataStore`, creating additional columns. ([#237](https://github.com/LCA-ActivityBrowser/activity-browser/pull/237))
- The results in the elementary flows and process contributions tabs can now be aggregated by their relevant columns. ([#239](https://github.com/LCA-ActivityBrowser/activity-browser/pull/239))
- This changelog file! ([#240](https://github.com/LCA-ActivityBrowser/activity-browser/pull/240))

### Changed

- Documented `MLCA` and `Contributions` classes according to [numpydoc](https://numpydoc.readthedocs.io/en/latest/) standards. ([#236](https://github.com/LCA-ActivityBrowser/activity-browser/pull/236))
- Importing the `biosphere3` database now casts all `categories` values to tuples. ([07a1cc3 in #237](https://github.com/LCA-ActivityBrowser/activity-browser/pull/237/commits/07a1cc381afe1ddfb8c97f54f7fc98af55dbedd3))
- Added methods to `MetaDataStore` class to simplify handling of the dataframe object inside. ([f95483c in #236](https://github.com/LCA-ActivityBrowser/activity-browser/pull/236/commits/f95483c03f216765f15def5ec7bce898a834b6a3))

### Fixed

- Cleaning up removed project directories ([#194](https://github.com/LCA-ActivityBrowser/activity-browser/issues/194), [#198](https://github.com/LCA-ActivityBrowser/activity-browser/pull/198)) can now be done by running the `activity-browser-cleanup` command in the anaconda prompt.
- Removed the line in the README file recommending people use the development version. Strip 'development' line from the recipe yaml when building a stable version. ([#241](https://github.com/LCA-ActivityBrowser/activity-browser/pull/241))
- Added method to `ProjectSettings` class to ensure the `read-only-databases` key is always present in the settings ([#235](https://github.com/LCA-ActivityBrowser/activity-browser/issues/235), [#242](https://github.com/LCA-ActivityBrowser/activity-browser/pull/242)). This fix also includes adding methods and calls to ensure new databases are added to- and removed from the settings.
- Allow users to add all (default) biosphere types to an activity instead of only exchanges of type 'emission'. ([#244](https://github.com/LCA-ActivityBrowser/activity-browser/pull/244))

## [2.3.1] - 2019-04-15

### Fixed

- Travis now correctly receives and handles a version tag.

## [2.3.0] - 2019-04-12

### Changed

- Major overhaul of the GUI. See [#218](https://github.com/LCA-ActivityBrowser/activity-browser/pull/218) for details.
- New conda stable and development builds (`activity-browser`, `activity-browser-dev`) can now be found in the `bsteubing` [channel](https://anaconda.org/bsteubing/).


[Unreleased]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.2...HEAD
[2.3.2]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.1...2.3.2
[2.3.1]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.0...2.3.1
[2.3.0]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.2.5...2.3.0
