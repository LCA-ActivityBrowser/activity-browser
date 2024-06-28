# Activity Browser Contributing Guidelines

## How can I contribute?

There are several ways how you can contribute to the Activity Browser project:
- Reporting bugs
- Sharing ideas for new features
- Helping other users work with Activity Browser
- Contributing to the code of Activity Browser

### Reporting bugs
If you notice a breaking bug or feature that doesn't work as expected, please
see the [Issues](https://github.com/LCA-ActivityBrowser/activity-browser/issues)
page on  [GitHub](https://github.com/LCA-ActivityBrowser/activity-browser/).
On this page you can see if others have reported the same or similar issue. 
If someone already shared the same or a similar issue, just let us know you're experiencing the same problem.
If you can't find an existing issue matching your problem, create a [bug report](https://github.com/LCA-ActivityBrowser/activity-browser/issues/new?assignees=&labels=bug&projects=&template=bug_report.yml).
The bug report page will help you share the right information for us to help you.

### Sharing ideas for new features
If you have an idea for a new feature or a logical extension on an existing
one, don’t hesitate to share this through a [feature request](https://github.com/LCA-ActivityBrowser/activity-browser/issues/new?assignees=&labels=feature&projects=&template=feature_request.yml). 
Additionally, if you see other feature suggestions that look important or interesting for your work, add your voice!

## Contributing documentation to the Activity Browser and helping other users

### Youtube
The README file already contains a link to a youtube channel for introducing beginning users of the AB to the 
application. 
If you have the time, further contributions to further explain the more advanced features of the AB are especially 
welcome!

If you want to include the opening graphics created for the existing youtube videos, please 
[contact the developers](https://github.com/LCA-ActivityBrowser/activity-browser#developers).

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
a priority. Examples of in-software guidance go from `?` buttons that
explain the function of the tab/section, hover-text that show what buttons
or drop-down menus do, through to in-depth warnings or error messages when
something goes wrong when calculation or preparing data.

### Helping other users
You can always try to help out our users by looking at our [discussions page](https://github.com/LCA-ActivityBrowser/activity-browser/discussions).
If you would like to help other users in a more structured way, 
just [contact the developers](https://github.com/LCA-ActivityBrowser/activity-browser#developers) and lets discuss!  


## Developing the Activity Browser
If you want to contribute your time to make the activity browser better, great! 
If you don’t know where to start you can either have a look at the issues with a 
[`good first issue` label](https://github.com/LCA-ActivityBrowser/activity-browser/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) 
or by [contacting the developers](https://github.com/LCA-ActivityBrowser/activity-browser#developers).

For more in-depth information about contributing to the project, please read on.

#### Adding (big) features
If you want to make big changes to the code or functionality of Activity Browser, please always 
[contact the developers](https://github.com/LCA-ActivityBrowser/activity-browser#developers) first.
A large amount of the code in the activity browser is based on the logic and features present in `brightway2`. 
If you have an idea for a new big feature you want to see in the activity browser, please (help us) work it out in a
Jupyter notebook! 
This will give us a solid starting point on how to implement the feature in the activity browser as well as write tests 
for it!

### What should I know before getting started?
The activity browser is an open-source project. 
On deciding you want to contribute to the activity browser, it might be unclear where in the code certain kinds of 
functionality or features are placed. 
This section is here to help give some direction.

- __Controllers__

  [Controllers](https://github.com/LCA-ActivityBrowser/activity-browser/tree/main/activity_browser/controllers) 
  in the activity browser act as go-betweens for the Qt application and the underlying brightway layer. 
  Ideally, these controllers are called exclusively through signals from the Qt application and will in turn call
  methods and classes that edit the structured data in brightway.
  If you want to present a warning or question to the user when they try and change brightway data, you can use a 
  controller to do so.

- __BW-Utils__

  The code, methods and classes in the 
  [`bwutils`](https://github.com/LCA-ActivityBrowser/activity-browser/tree/main/activity_browser/bwutils)
  directory are kept separate from the rest of the application specifically because they are only dependent on-, and 
  extensions of the brightway layer.  
  Keeping a strict separation between brightway and the rest of the activity browser application allows for future 
  changes to the brightway code to be handled in one place.

- __Tables__

  [Tables](https://github.com/LCA-ActivityBrowser/activity-browser/tree/main/activity_browser/ui/tables) 
  in the activity browser are one of the more complex parts of the application as these are required to both present 
  the data from brightway as well as handle the editing of this data (through the model embedded in
  the table class).

- __Figures__

  [Figures](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/activity_browser/ui/figures.py) 
  constructed in the Activity Browser are currently implemented in matplotlib through either using pandas .plot or 
  matplotlib directly.
  In the future we want to move to a different library, to make figures more interactive.

- __Graphs__

  These graphs are made up out of two parts, the 
  [__python__](https://github.com/LCA-ActivityBrowser/activity-browser/tree/main/activity_browser/ui/web) 
  part which extracts information from brightway and prepares a JSON document, and the 
  [__javascript__](https://github.com/LCA-ActivityBrowser/activity-browser/tree/main/activity_browser/static/javascript) 
  part which presents a given JSON document as a graph (built using the JavaScript dagre D3 library).

### Setting up a development environment
If you want to contribute code, we suggest the following setup:

- Set up a `conda` environment as explained in the 
[readme](https://github.com/LCA-ActivityBrowser/activity-browser#the-thorough-way)
- Fork this repository and download your fork through git to your favourite IDE
- Set up this repository as an `upstream` remote like in the image below (for PyCharm):
  - Note that `upstream` can be named anything, but it is good convention to call it this

![image](https://github.com/LCA-ActivityBrowser/activity-browser/assets/34626062/de77953f-12c1-4188-9898-1e44a9ce04df) 

### Running and writing tests
If you want to check whether your changes break anything essential, you can run the automated tests. 
This requires some additional packages.

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

An AB window will open and perform some automated actions. 
If you interfere, the tests will most likely fail. 
Also note that having multiple instances of the AB open can lead to unexpected responses.

In an ideal case, you can write your own tests for new features that you add.
Please see the tests that are already present in the 
[`tests`](https://github.com/LCA-ActivityBrowser/activity-browser/tree/main/tests) folder or look at the 
[pytest-qt documentation](https://pytest-qt.readthedocs.io/en/latest/) for inspiration and examples.

### Pull requests
Once you are happy with your changes to AB, please open a pull-request. 
We use the
[fork and pull model](https://help.github.com/articles/about-collaborative-development-models/)
for external contributions. 
Fork the AB repository, create a new branch from the `main` branch, apply your changes on the new branch in your 
forked repository and open a pull request from there. 
When creating a pull-request, please add a description of what your new changes should accomplish (and if this wasn't a 
known problem, _why_ AB needs this).
If it's a larger pull-request, feel free to add screenshots/gifs or other useful descriptions to help us understand what 
you did. 
Next, make sure your pull-request has a sensible title that _users_ can easily understand, this name is shown in the 
changelog of the next release.
Avoid issue numbers in the title.

This is a [BAD example of a title](https://github.com/LCA-ActivityBrowser/activity-browser/pull/958):

![image](https://github.com/LCA-ActivityBrowser/activity-browser/assets/34626062/ea751c88-d25d-4edb-a724-380c73ec9347)
- This example is bad because it is not clear to users what this does and uses an issue number, which will show in the 
  changelog, but also, does not work directly in titles.

This is a [GOOD example of a title](https://github.com/LCA-ActivityBrowser/activity-browser/pull/1051):

![image](https://github.com/LCA-ActivityBrowser/activity-browser/assets/34626062/0822a3c8-d01c-4a0c-8cbc-d44c4bbddc02)
- This is a good example because it describes what is changed.

Finally, please make sure you follow the pull-request checklist (you can see this when you open a pull-request).
If you can't complete certain tasks because you don't have write-access (e.g. adding a label and milestone), 
they will be performed by the maintainers.

Upon creating a new pull-request, there are a number of automated tests that will be run. 
If the test-runners fail in some way, it is likely that there is an error somewhere in your PR. 
You can look at the logs of the continuous integration services to see what failed and where.

When the tests pass on a pull-request, one of the maintainers of AB will review the changes 
(possibly requesting some edits) and approve or reject the request.

### Do's and Don'ts
- Please do document any new code you wish to include in the activity browser.
  This means writing useful documentation in the code (please follow the 
  [numpy style guide](https://numpydoc.readthedocs.io/en/latest/format.html)), but also writing useful tooltips, labels
  and other things that can help users.
- Where possible, avoid importing and using brightway2 classes and methods directly in the Qt application code. 
  If some complex data processing is needed, see if your use-case is covered by bwutils instead. 
  If bwutils does not contain any for your use-case you are welcome to add it.
- Always create changes on your own fork, even if you have write access to the main repository
- Do try to write descriptive commit messages:
  - This is a [BAD example](https://github.com/LCA-ActivityBrowser/activity-browser/commit/86922c1578c9d9d9fd034a7048bc9c74fae20e4a):

    ![image](https://github.com/LCA-ActivityBrowser/activity-browser/assets/34626062/af20ed45-4a47-4a76-b5ef-1bea12723cf5)
    - This is a bad example because looking back through the commit history, we don't know what this refers to
    - A better title could have been: `implement dialog for new location linking feature`
  - This is a [GOOD example](https://github.com/LCA-ActivityBrowser/activity-browser/commit/f8f58a1a365419d33d9ca929cdbfaef52199e67e):
  
    ![image](https://github.com/LCA-ActivityBrowser/activity-browser/assets/34626062/c2b587ea-5539-452a-991e-2061fb20c249)
    - This is a good example because it is clear _what_ has been done and _where_.
    - This commit message also uses a [closing keyword](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue), 
      making writing your pull-requests easier because the issue is already linked automatically
    - This could have been better as 2 commits, one for resolving the issue, one for improving the documentation, it is
      not clear in the commit what actually fixes the issue.  
  - __Tip__: Keep in mind that these commits are visible on Github, you can make use of this by referencing issues and 
    using 
    [Markdown formatting](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)
    in your commits.

## Maintaining the Activity Browser
Next to developers, some people maintain the AB. 
Maintainers can contribute to AB themselves, but also have the following tasks:
- Review pull-requests made by _others_; not reviewing your own pull-requests should always be avoided, however small 
  the changes
- Planning bug-fixes and features for release through 
  [milestones](https://github.com/LCA-ActivityBrowser/activity-browser/milestones)
  so the community knows what bug fixes and new features to expect in the next versions
- Creating new releases

### Reviewing pull-requests
When reviewing a pull-request the below should be kept in mind.
Consider that you're helping developers do better work and ensure the quality of AB, so be helpful; 
add/improve the basics and a milestone if they're missing.  

__Basics__ 
- Is the title easy to understand for _users_?
- Is the checklist completed and have no things been removed that are relevant?
- Are the checklisted items correct? (e.g issues properly linked, correct label applied etc.)?

__Necessity__
- Do we _need_ this change (e.g. is it from an open issue or clear from the pull-request why this is needed)?  
- Does this conflict with other planned changes?

__Code quality__ 
- Is the code readable? 
- Do the comments make sense? 
- Is all the added code used?
- Is there still commented code that should be removed?
- Do the tests succeed and should new tests be added?

__Functionality__
- Try the new changes on your machine, does it do what it is supposed to do?
- Has nothing else accidentally broken because of this change?
- Try to abuse/break the new changes, better to find problems now than to have users find them.  
  
### Planning bug-fixes and new features
The AB team should schedule and prioritize bug-fixes and new features to be added to AB.
By adding milestones to issues and pull-requests, it becomes clear to the community and other developers and maintainers
what is planned for when. 
Using milestones also allows us to keep a log of when certain things have been added or removed from AB. 
While the releases changelog shows merged pull-requests, the milestones will also show issues that have been closed in 
a certain version making it easier to track when changes were made.   

Once it has been decided that an issue will be worked on, it is useful to provide additional information in the issue: 
- When: Adding a milestone 
- Who: Assigning someone to the issue 
- What: Commenting a TODO list with simple broken-down steps
  ([e.g. like this](https://github.com/LCA-ActivityBrowser/activity-browser/issues/632))

#### Regular checks for dependency problems
AB has a [canary install](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/install-canary.yaml) 
that runs the installation of AB every 24 hours, it will report any problems with installing AB.

In addition, the tests that run when a pull-request is opened can pass, while still having `warnings`, these may be 
`DeprecationWarning` or other things that are not a problem now, but will become a problem in the future.

If any installation problems occur or warnings happen in the pull-requests tests, they should be resolved. 

### Creating a new release of Activity Browser
Activity Browser versions and related information can be found on the
[__releases__](https://github.com/LCA-ActivityBrowser/activity-browser/releases)
page.

The AB follows the `major.minor.patch` versioning [schema](https://semver.org/) closely, but not entirely.
Where `major` releases are reserved for completely backwards-incompatible
changes, `minor` for new (non-breaking) features or improvements and `patch` for
bug-fixes and minor changes.

To create a new release follow these steps:
- Review if all scheduled changes in the [milestone](https://github.com/LCA-ActivityBrowser/activity-browser/milestones) 
  for the next version are complete, if not, either re-plan them for a next milestone or finish them
- __Do not__ close the milestone yet
- Check out the main branch (either through your IDE or with `git checkout main`)
- `Fetch` and `Pull` changes
- Create a new tag: `git tag -a x.y.z -m 'x.y.z'` (where `x.y.z` is the new version number)
- Push the new tag to the repository: `git push upstream x.y.z`
  - Of course make sure your upstream remote is actually called `upstream`
- The above triggers the following:
  - github actions creates a new [release](https://github.com/LCA-ActivityBrowser/activity-browser/releases), showing 
    all changes in a changelog
  - Within a few hours, the `conda forge` bot will notice a new release and open a new pull-request on our 
    [feedstock page](https://github.com/conda-forge/activity-browser-feedstock)
- Wait until a new pull-request is opened on the 
  [`conda forge feedstock`](https://github.com/conda-forge/activity-browser-feedstock/pulls)
  automatically, then review the pull-request and merge the changes
  - The release will be available on [conda-forge](https://anaconda.org/conda-forge/activity-browser) shortly 
- Close the [milestone](https://github.com/LCA-ActivityBrowser/activity-browser/milestones) for this version
  - This triggers a 
    [`github actions`](https://github.com/LCA-ActivityBrowser/activity-browser/actions/workflows/comment-milestoned-issues.yaml) 
    bot that will reply to each _closed_ issue with this milestone that a new release is available with an 
    implemented solution for the issue
- Write an email to the   [updates mailing list](https://brightway.groups.io/g/AB-updates/topics) announcing the 
  new changes

### Don'ts for maintainers:
- Never create a new release on a Friday or on a day before you'll be unavailable
- Never create `major` or `minor` releases close to (e.g. 3 weeks before) something like a course where AB is used, 
  only release changes that are certain to improve stability or fix things that are known to be a problem during the 
  course
- In general, don't make releases more than once every two weeks, of course if there are urgent fixes, make them
