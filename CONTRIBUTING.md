# Activity Browser Contributing Guidelines

## How can I contribute?

If you notice a breaking bug or feature that doesn't work as expected, please
see the [Issues](https://github.com/LCA-ActivityBrowser/activity-browser/issues)
page on  [GitHub](https://github.com/LCA-ActivityBrowser/activity-browser/).
On this page you can see if others have reported the same or similar issue
and add your voice there.

If no others have reported your issue you can create a new issue and describe
your problem. Use a short and descriptive title for the issue. Ideally describe
what you expected to happen vs. what actually happened. If there is a visual
component to the bug, please also add a screenshot (just drag-and-drop into
your issue text). You can also add the output of the debug window or console
if there is an error message related to the bug. Last but not least, you can
include the application version (Found under ‘Help -> About Activity Browser’).

### Reporting bugs

If you have an idea for a new feature or a logical extension on an existing
one, don’t hesitate to share this on the github page. Additionally, if you
see other feature suggestions that look important or interesting for your
work, add your voice!

### Contributing (to) ideas

If you want to contribute your time to make the activity browser better,
great! If you don’t know where to start you can either bring this up on the
GitHub issues tab or by directly messaging/emailing the main developers.

For more in-depth information about contributing to the project, please read on.

### Adding (big) features

A large amount of the code in the activity browser is based on the logic and
features present in `brightway2`. If you have an idea for a new big feature
you want to see in the activity browser, please (help us) work it out in a
Jupyter notebook! This will give us a solid starting point on how to implement
the feature in the activity browser as well as write tests for it!

## Developing the Activity Browser

### What should I know before getting started?

The activity browser is an open-source project. On deciding you want to
contribute to the activity browser, it might be unclear where in the code
certain kinds of functionality or features are placed. This section is here
to help give some direction.

As of 2021-01-13, the activity browser is undergoing a restructuring to better
separate the different parts of the application from each other.


### Special cases

* __Controllers__

  [Controllers](https://github.com/LCA-ActivityBrowser/activity-browser/tree/master/activity_browser/controllers) in the activity browser act as go-betweens for the Qt application
  and the underlying brightway layer. Ideally, these controllers are called
  exclusively through signals from the Qt application and will in turn call
  methods and classes that edit the structured data in brightway.
  If you want to present a warning or question to the user when they try and
  change brightway data, you can use a controller to do so.

* __BW-Utils__

  The code, methods and classes in the [`bwutils`](https://github.com/LCA-ActivityBrowser/activity-browser/tree/master/activity_browser/bwutils)
  directory are kept separate
  from the rest of the application specifically because they are only dependent
  on-, and extensions of the brightway layer. Keeping a strict separation
  between brightway and the rest of the activity browser application allows
  for future changes to the brightway code to be handled in one place.

* __Tables__

  [Tables](https://github.com/LCA-ActivityBrowser/activity-browser/tree/master/activity_browser/ui/tables) in the activity browser are one of the more complex parts of the
  application as these are required to both present the data from brightway
  as well  as handle the editing of this data (through the model embedded in
  the table class).

* __Figures__

  [Figures](https://github.com/LCA-ActivityBrowser/activity-browser/blob/master/activity_browser/ui/figures.py) constructed in the Activity Browser are currently implemented in matplotlib through either using pandas .plot or matplotlib directly.
  In the future we want to move to a different library, to make figures more interactive.

* __Graphs__

  These graphs are made up out of two parts, the [__python__](https://github.com/LCA-ActivityBrowser/activity-browser/tree/master/activity_browser/ui/web) part which extracts information from brightway and prepares a JSON document, and the [__javascript__](https://github.com/LCA-ActivityBrowser/activity-browser/tree/master/activity_browser/static/javascript) part which presents a given JSON document as a graph (built using the JavaScript dagre D3 library).


### Do's and Don'ts

* Please do document any new code you wish to include in the activity browser.
* Where possible, avoid importing and using brightway2 classes and methods
  directly in the Qt application code. If some complex data processing is needed,
  see if your use-case is covered by bwutils instead. If bwutils does not
  contain any for your use-case you are welcome to add it.


### Setting up a development environment

If you want to contribute code, we suggest the following setup:

- Set up the conda channels as explained in the readme
- Create a new conda environment, where only the dependencies of the AB are installed:
```
conda create -n dev_ab
conda activate dev_ab
conda install --channel conda-forge --only-deps activity-browser
```
- `cd` into your forked repository
- start the AB with this command: `python run-activity-browser.py`

### Running and writing tests

If you want to check whether your changes break anything essential, you can run
the automated tests. This requires some additional packages.

```bash
conda install -n dev_ab pytest pytest-mock pytest-qt pytest-cov
```

You can then run the tests inside the repo like this:

```bash
# You can add the -v or --cov=activity_browser arguments to add additional
# information to the output of the test.
py.test
# OR
pytest
# OR
python -m pytest
```

An AB window will open and perform some automated actions. If you interfere,
the tests will most likely fail. Also note that having multiple instances of
the AB open can lead to unexpected responses.

In an ideal case, you can write your own tests for new features that you add.
Please see the tests that are already present in the [`tests`](https://github.com/LCA-ActivityBrowser/activity-browser/tree/master/tests) folder or look at
the [pytest-qt documentation](https://pytest-qt.readthedocs.io/en/latest/)
for inspiration and examples.

### Pull requests

If you have created a feature that you want to add to the AB or added
documentation to the codebase, please open a pull-request. We use the
[fork and pull model](https://help.github.com/articles/about-collaborative-development-models/)
for external contributions. Fork the AB repository, create a new branch from
the ‘master’ branch, apply your changes on the new branch in your forked
repository and open a pull request from there. When creating a pull-request,
please also add a short description of what the pull request accomplishes.

On creating a new pull-request, there are a number of automated tests that
will be run. If the test-runners fail in some way, it is likely that there
is an error somewhere in your PR. You can look at the logs of the continuous
integration services to see what failed and where.

When the tests pass on a pull-request, one of the main developers of the AB
will come by and review the changes (possibly requesting some edits) and
approve or reject the request.

If feasible, you can record the changes you made in the
[`CHANGELOG.md`](https://github.com/LCA-ActivityBrowser/activity-browser/blob/master/CHANGELOG.md)
file, under the __UNRELEASED__ header.

### Merging changes

On merging the changes from a pull-request into the `master` branch of the AB
the test-suite will run again, and if the tests pass a new version of the
_development_ [conda package](https://anaconda.org/bsteubing/activity-browser-dev)
will be built and deployed (`activity-browser-dev`).

### Stable deployments

Activity Browser versions and related information can be found on the
[__releases__](https://github.com/LCA-ActivityBrowser/activity-browser/releases)
page.

A stable version of the Activity Browser will be created by the test-suite
scripts whenever a git tag is added to an existing commit. This is most often
done through the `draft a new release` tool on the releases page.

Where possible the AB follows the `major.minor.patch` versioning
[schema](https://semver.org/).
Where `major` releases are reserved for completely backwards-incompatible
changes, `minor` for (small) new features or improvements and `patch` for
bugfixes.

## Contributing documentation to the AB

### Youtube

The README file already contains a link to a youtube channel for introducing
beginning users of the AB to the application. If you have the time, further
contributions to further explain the more advanced features of the AB are
especially welcome!

If you want to include the opening graphics created for the existing youtube
videos, please contact Bernhard Steubing.

### Github wiki page

The Activity Browser has its own
[__wiki__](https://github.com/LCA-ActivityBrowser/activity-browser/wiki) page!
This page contains an explanation (in text) of how to get started with the AB.

Sadly, other than this, there is still very little to be found there. If you
want to contribute to the wiki, either by adding figures or links or by writing
new sections, please contact the developers!

### In-software guidance

With more and more features being included into the AB, the inclusion of
in-software guidance for how these features work is becoming more and more
a priority. Examples of in-software guidance go from __?__ buttons that
explain the function of the tab/section, hover-text that show what buttons
or drop-down menus do, through to in-depth warnings or error messages when
something goes wrong when calculation or preparing data.
