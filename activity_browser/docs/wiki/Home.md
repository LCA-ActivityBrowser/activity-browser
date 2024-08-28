Welcome to the Activity Browser wiki!


This page aims to explain how to get started using the Activity Browser to import and organize your data, construct and run simple LCA calculations, make changes to datasets and create simple parameterized systems.

The Activity Browser (AB) is an open source LCA software that builds on top of the **Brightway** LCA framework. Users that are unfamiliar with Brightway2 are invited to also look at [the documentation of the framework](https://2.docs.brightway.dev/intro.html#main-brightway2-components), as this will explain a number of the components and terms used by AB.

Please consider also watching our short AB [Youtube tutorials](https://www.youtube.com/channel/UCsyySKrzEMsRFsWW1Oz-6aA)


## Contents

* [Importing data](#importing-data)
* [Creating a calculation setup](#creating-a-calculation-setup)
* [Editing processes](#editing-processes)
* [Creating parameters](#creating-parameters)

## Importing data

When starting in a new project the first thing to import is the 'default data',
this data consists of the `biosphere3` database which contains a number of
 standardized biosphere flows and a large amount of pre-made
`Impact Categories` (Viewable in the 'Impact Categories' tab on the left).
The button `Add default data (biosphere flows and impact categories)` will add
these to the project.

After this is done it becomes possible to create and import databases through the `New`
and `Import` buttons next to the 'Databases:' header.

With 'New' you can create a completely empty database with any given name and
enter your own data as desired.

Clicking 'Import' will open a new window that will allow you to select how you
want to import data into brightway (and by extension, the Activity Browser).
There are three main options: 'Ecoinvent', 'Forwast' and 'Local', see below for
an in-depth explanation of these options.

1. [Ecoinvent](https://www.ecoinvent.org/), a well-known and expansive life cycle inventory database.
    * Download by login: This option will ask for a username and password and
    will use these to attempt to login to the ecoinvent website. If this
    succeeds you will be able to download the versions and kinds that are
    available to the licence the username and password has.
    * Local 7z-archive: This option expects that you have downloaded a version
    of ecoinvent from their website before and will attempt to extract the
    selected archive and import the data from there.
    * Local directory: This option will directly read `ecospold2`
    [format](https://www.ecoinvent.org/data-provider/data-provider-toolkit/ecospold2/ecospold2.html)
    type files from the given directory and will attempt to import the data.
      * Do note that this option will actually work with any other kind of dataset,
      as long as it is using the ecospold2 format.
2. [Forwast](https://lca-net.com/projects/show/forwast/), a publicly available
dataset focussing on material stocks and waste amounts for the EU. Selecting
this option will download the FORWAST dataset and import it into the project.
3. Local brightway file ([BW2Package](https://2.docs.brightway.dev/technical/bw2io.html#bw2package)).
This option allows for the import of databases previously exported from
brightway, allowing for a straightforward way of sharing datasets between
users.
    * There are some validation steps when attempting to import data this way
    and in the future these will be extended in an attempt to make this method
    of database importing a lot more flexible to use.

## Creating a calculation setup

A calculation setup needs to be created in order to do LCA calculations. 

![Calculation Setup](https://user-images.githubusercontent.com/33026150/115353679-177cab00-a1b9-11eb-920e-ac2f1c2c690f.jpg)

You can find the `LCA Setup` tab on the right side of the window, opening it will
show a number of buttons and a drop-down menu at the top. A new calculation setup
can be created by clicking the `New` button. 

After creating a new calculation setup you can drag-and-drop activities
(technosphere processes) from their database list (Accessed by double-clicking
on any database name) into the 'Reference Flows' table. Impact categories can
be dragged-and-dropped from their list under the 'Impact Categories' tab into
the 'Impact categories' table for the setup.

A minimum LCA setup consists of 1 reference flow and 1 impact category. 

## Editing processes

Sometimes you want to quickly change a process to see what kind of influence some
exchange has on the impact assessment of that functional unit, or to see if
this change has some effect on the impact assessments of other downstream processes.

Editing an activity can be done **only** when the database it belongs to is
not in `read-only` mode, this mode is individually toggleable by clicking on
the check-mark for the database in the databases table on the left side.
**Take note however:** making an edit to any activity in a database will
mark that database as 'dirty', but it won't keep track of the changes themselves.
Keep this in mind when working with datasets such as ecoinvent.

Editing an activity inside the activity browser is possible when viewing its
details. Activity details can be seen by double-clicking on any _technosphere_
activity (i.e. process) in a database, this will open the `Activity Details` tab
on the right side of the window. After opening the details view of an activity,
actually editing it requires checking the `Edit Activity` check-box inside the
tab.

It is possible to change a number of things about an activity: the `location`
an activity occurs in, the `unit` of measurement for the product it produces,
even the `product name` can be altered.

Note that for the technosphere inputs and biosphere flows only the `amount` and
`formula` fields can be edited, this is because only these fields have an
actual effect on the assessment calculation.

## Creating parameters

Parameters are [special objects in Brightway](https://2.docs.brightway.dev/intro.html#parameterized-datasets)
that allow users to create incredibly complex systems of interlocking parts.

What parameters actually do is store a _value_ and allow recalculation of that
value through a _formula_. While there are technically three layers of
parameters (`Project`, `Database` and `Activity`), the AB encourages users to
only use two (`Project` and `Activity`).

Note that each parameter has a _name_ which is unique  within their 'group'.
So project parameters have unique names within the project and activity
parameters have names unique within their 'group'. The Activity Browser will
strongly enforce this uniqueness and won't allow name changes if a conflict
exists.

The reason for this uniqueness is that a parameter _name_ can be used in
_formulas_ to insert the _value_ of that parameter at that specific place
in the _formula_.

### Project parameters

A new project parameter can be created by clicking the `New` button next
to the 'Project' label. A default name is assigned to this parameter which
can later be altered (renaming) by right-clicking on the parameter and
selecting the `Rename parameter` option from the drop-down menu that opens.

Both the _amount_ and _formula_ fields can be edited by double-clicking
in them, though keep in mind that the _formula_ field has precedence when
determining the _amount_ of the parameter.

Finally, a (project) parameter can be deleted by right-clicking on the
parameter and selecting the `Delete parameter` option from the drop-down
menu. Do note however that a parameter can __only__ be deleted if it is
not being used in any other _formula_ field, if the Activity Browser finds
that this __is__ the case, the `Delete` option will be grayed out.

### Activity Parameters

Where project parameters can be used by any formula anywhere in the project,
activity parameters are a lot more narrow in scope. These parameters are made
to target the specific exchanges that exist within the activity that is
parameterized.

There are some rules for activity parameters:

* Multiple parameters can be created for one activity.

* Exchanges for activity B __cannot__ use parameters created for activity A.

* Activity parameters must have a unique name __within__ the 'group' of the
  related activity. Two parameters on __different__ activities can have the
  same name.

* If a project parameter and an activity parameter share a name, the activity
  parameter will be preferred if that name is used in a formula for one of the
  exchanges.

In the Activity Browser activity parameters can be created in two ways:

1. The first way is through dragging-and-dropping activities from the activities
  table on the left side into the activity parameters table on the right side.
  This allows for an easy way of parameterizing multiple activities at once.
  However, the user still has to go into each activity (by way of the Activity
  Detail tab) and parameterize the relevant exchanges.

2. The second way is through directly parameterizing exchanges within the Activity
  Detail tab (by editing the _formula_ field). As soon as an exchange formula is
  stored, the Activity Browser will generate a new activity parameter for the 
  related activity.

Activity parameters can be `Renamed` and `Deleted` through right-clicking the
parameter, much the same as project parameters. Additionally, the Activity
Detail tab can be opened for the parameterized activity by way of the
`Open activities` option.

