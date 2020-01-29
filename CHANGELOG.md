# Changelog

## [Unreleased]

## [2.5.0] - 2020-01-23

### Added

- ([#352](https://github.com/LCA-ActivityBrowser/activity-browser/pull/352))
    Added uncertainty wizard, which guides users in adding or changing the
    uncertainty of a process exchange or parameter. This addition includes
    some changes in how uncertainty is shown, by adding additional columns
    and hiding all uncertainty columns in exchange and parameter tables
    by default.
- ([cf04f2e](https://github.com/LCA-ActivityBrowser/activity-browser/commit/cf04f2eff61b3bffb92c2334d2fe0b742cd3c84d))
    A link to a scientific publication on the Activity Browser is now included
    in the readme.
- ([#341](https://github.com/LCA-ActivityBrowser/activity-browser/pull/341))
    Added the brightway2 `bw2test` decorator as a pytest fixture, allowing
    tests which use that fixture to be performed in a new and completely
    separate environment which is torn down after the test completes. Also
    includes tests for the new presamples Qt objects and some of the
    on-demand Qt widgets.
- ([#330](https://github.com/LCA-ActivityBrowser/activity-browser/pull/330))
    Added scenario analysis! It is now possible to create scenarios for
    parameters and store the calculated new exchange amounts for each
    scenario as a presamples package. It is also possible to select presamples
    packages created outside of the Activity Browser for use in LCA
    calculations. 
- ([#323](https://github.com/LCA-ActivityBrowser/activity-browser/pull/323))
    Make use of the builtin import/export fuctionality of brightway to
    allow quick imports and exports of databases. Note that there are a lot
    of rules and complications involved!

### Changed

- ([9352758](https://github.com/LCA-ActivityBrowser/activity-browser/commit/935275809945ee4f3a6c783e0f0062c9e5ec4922))
    Always show the MonteCarlo tab in LCA results, show a warning when
    running MonteCarlo on databases with incorrect uncertainty data. 
- ([#348](https://github.com/LCA-ActivityBrowser/activity-browser/pull/348))
    Moved metadata-changing signal connections out of the `MetaDataStore` class
    and into the `Controller` class.
- ([#345](https://github.com/LCA-ActivityBrowser/activity-browser/pull/345),
    [#349](https://github.com/LCA-ActivityBrowser/activity-browser/pull/349))
    Improvements to the (code) documentation and layout of the LCA results tab and
    added tooltips for many of the related buttons. With thanks to
    [@e4BdSBmUzHowFico5Ktn](https://github.com/e4BdSBmUzHowFico5Ktn).
- ([#322](https://github.com/LCA-ActivityBrowser/activity-browser/pull/322))
    Updating the biosphere through the menu-option will now warn the user
    that the action is not reversible.
- ([#325](https://github.com/LCA-ActivityBrowser/activity-browser/pull/325))
    Changing the naming of 'LCIA methods' into 'Impact Categories'.
- ([#312](https://github.com/LCA-ActivityBrowser/activity-browser/pull/312))
    Slight changes to the main drop-down menu's, adding relevant icons to
    functionality.
- ([#315](https://github.com/LCA-ActivityBrowser/activity-browser/pull/315))
    Refactor code to use PySide2, use LGPL license.

### Fixed

- ([#344](https://github.com/LCA-ActivityBrowser/activity-browser/pull/344),
    [#347](https://github.com/LCA-ActivityBrowser/activity-browser/pull/347),
    [#351](https://github.com/LCA-ActivityBrowser/activity-browser/pull/351))
    Numerous fixes related to the functioning of the dataset/database import wizard.
    Includes: a fix for [#333](https://github.com/LCA-ActivityBrowser/activity-browser/issues/333)
    and fixes aggregation of LCA results [#331](https://github.com/LCA-ActivityBrowser/activity-browser/issues/331).
- ([#340](https://github.com/LCA-ActivityBrowser/activity-browser/pull/340))
    It is now again possible to open multiple activities at once when selecting
    them from the database table.
- ([#339](https://github.com/LCA-ActivityBrowser/activity-browser/pull/339))
    Clearing the formula in the formula delegate will now properly signal
    the parameter recalculation, ensuring the same functionality as the
    'clear formula' action in the right-click menu.
- ([b08b9a8](https://github.com/LCA-ActivityBrowser/activity-browser/commit/b08b9a8351a6d2d4af54eab1e98f9b29e1a2ceca))
    Fixed typo, clarified division button, use default value of 1.0 for
    new parameters to avoid sudden division by 0 errors.
- ([#327](https://github.com/LCA-ActivityBrowser/activity-browser/pull/327))
    Indexes in ParameterWizard now correctly set. Uncertainty type is
    grabbed from the exchanges instead of processes, as it should be.
    Code improvements to ensure filenames are 'safe' when exporting figures.

## [2.4.0] - 2019-10-30

### Added

- ([#260](https://github.com/LCA-ActivityBrowser/activity-browser/pull/260))
    Exposed the brightway2 parameterization functionality through the Activity
    Browser. This includes a custom formula creation delegate used by the
    existing exchange tables and the parameter tables in the new 'Parameters'
    tab. Please see the [brightway2 documentation](https://2.docs.brightwaylca.org/intro.html#parameterized-datasets)
    for a rundown of how to use parameters.
- ([#308](https://github.com/LCA-ActivityBrowser/activity-browser/pull/308))
    Added a small biosphere3 updater for users with long-running projects.
    This will allow users to update their biosphere3 database allowing the
    importer to correctly link never versions of ecoinvent. Also includes
    an exception handler which explicitly explains what to do when an ecoinvent
    import fails.

### Changed

- ([#297](https://github.com/LCA-ActivityBrowser/activity-browser/pull/297))
    Refactored settings code and moved relevant code from `app/bwutils/commontasks.py`
    into the settings classes themselves.

### Fixed

- ([#300](https://github.com/LCA-ActivityBrowser/activity-browser/pull/300))
    Perform searches on complete database inventory instead of previous
    search results.
- ([#306](https://github.com/LCA-ActivityBrowser/activity-browser/pull/306))
    Fixes a number of reported issues. The checkbox should now be working correctly on MacOS.
- ([#309](https://github.com/LCA-ActivityBrowser/activity-browser/pull/309))
    Corrects an edge-case bug which causes the AB to complain when a calculation
    setup could not be found.
- ([#310](https://github.com/LCA-ActivityBrowser/activity-browser/pull/310))
    Fixes an edge-case issue caused by copying a process with only technosphere
    exchanges to a new database. Fixes the `copy to a different db` command,
    and add minor changes to ensure that copying to a large database is snappy.

## [2.3.4] - 2019-10-16

### Changed

- ([#279](https://github.com/LCA-ActivityBrowser/activity-browser/pull/279))
    and a follow-up commit ([6edb798](https://github.com/LCA-ActivityBrowser/activity-browser/commit/6edb7982f6ef27bd7569c8b2464fe71cb7589a6f))
    disable the custom paint-delegate, due to it not functioning correctly
    on MacOS (issue [#278](https://github.com/LCA-ActivityBrowser/activity-browser/issues/278)).
- ([#281](https://github.com/LCA-ActivityBrowser/activity-browser/pull/281))
    A number of under-the-hood code tweaks were made which either streamline
    code or remove non-functional parts in the inventory table classes.
- ([#282](https://github.com/LCA-ActivityBrowser/activity-browser/pull/282))
    Closed a TODO in the tests, a mouseclick is now used to select the row
    and trigger a signal.
- ([#291](https://github.com/LCA-ActivityBrowser/activity-browser/pull/291))
    By splitting the test fixture into parts it became possible to unpin the
    the `pytest` version, allowing automated tests to take place on python 3.6
    and up!

### Fixed

- ([#283](https://github.com/LCA-ActivityBrowser/activity-browser/pull/283))
    Introduced a workaround for users with custom-bases databases which do not
    use a `location` field.
- ([#290](https://github.com/LCA-ActivityBrowser/activity-browser/pull/290))
    Link ecoinvent dataset-type to version explicitly to avoid key-errors.
- ([#293](https://github.com/LCA-ActivityBrowser/activity-browser/pull/293))
    With parameterization coming closer, a number of additional bugs and
    issues cropped up during testing. These fixes should remove most of the
    problems that arose by refactoring the tables to custom QTableViews.

## [2.3.3] - 2019-08-27

### Added

- ([#259](https://github.com/LCA-ActivityBrowser/activity-browser/pull/259))
    Subclassed the `Icons` class into `QIcons` which directly returns QIcon objects
    of the icon figures.

### Changed

- ([#256](https://github.com/LCA-ActivityBrowser/activity-browser/pull/256))
    Do not open the activity tab for activities without a product (ie. biosphere flows).
  - Includes tests!
- ([#258](https://github.com/LCA-ActivityBrowser/activity-browser/pull/258), [#261](https://github.com/LCA-ActivityBrowser/activity-browser/pull/261))
    Refactor the dataframe Model/View code to allow a lot of customization.
- ([#273](https://github.com/LCA-ActivityBrowser/activity-browser/pull/273))
    Filtering activities in the databases table is now case-insensitive: 'Gold' will
    now also find activities with 'gold' in them.
- Refactored all `ABTableWidget` classes to implement them as `ABDataFrameView` classes.
    See [#264](https://github.com/LCA-ActivityBrowser/activity-browser/pull/264),
    [#265](https://github.com/LCA-ActivityBrowser/activity-browser/pull/265),
    [#266](https://github.com/LCA-ActivityBrowser/activity-browser/pull/266),
    [#271](https://github.com/LCA-ActivityBrowser/activity-browser/pull/271),
    [#274](https://github.com/LCA-ActivityBrowser/activity-browser/pull/274).
    This fixes the issue of tables being sorted incorrectly.

### Fixed

- ([#246](https://github.com/LCA-ActivityBrowser/activity-browser/pull/246))
    Added a workaround for running LCA on databases with missing or unset uncertainty.
- ([#262](https://github.com/LCA-ActivityBrowser/activity-browser/pull/262))
    Database will no longer be deleted if the user selects `No` in the `delete_database`
    question dialog.
- ([#263](https://github.com/LCA-ActivityBrowser/activity-browser/pull/263))
    Add separate check of `database_changed` signal to ensure the correct table is refreshed.
- ([#267](https://github.com/LCA-ActivityBrowser/activity-browser/pull/267))
    Updating the metadata (by updating activities) will no longer throw errors.
- ([#231](https://github.com/LCA-ActivityBrowser/activity-browser/issues/231))
    Tables sorted on `float` or `integer`-type columns will now do so correctly instead of
    sorting the column by string.

### Removed

- ([#272](https://github.com/LCA-ActivityBrowser/activity-browser/pull/272))
    Removed `ConvenienceData` class as it has been completely replaced by the `MetaDataStore` class.
- ([#275](https://github.com/LCA-ActivityBrowser/activity-browser/pull/275))
    Removed unused `ABTableWidget` and `ABTableItem` classes, these have been completely
    replaced with the more flexible model/view implementation.

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

[Unreleased]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.5.0...HEAD
[2.5.0]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.4.0...2.5.0
[2.4.0]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.4...2.4.0
[2.3.4]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.3...2.3.4
[2.3.3]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.2...2.3.3
[2.3.2]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.1...2.3.2
[2.3.1]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.3.0...2.3.1
[2.3.0]: https://github.com/LCA-ActivityBrowser/activity-browser/compare/2.2.5...2.3.0
