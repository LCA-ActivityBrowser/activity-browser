> [!IMPORTANT]
> This wiki section is __incomplete__ or __outdated__.
> 
> Please help us improve the wiki by reading our
> [contributing guidelines](https://github.com/LCA-ActivityBrowser/activity-browser/blob/main/CONTRIBUTING.md#wiki).

## General concepts

## Creating parameters

Parameters are 
[special objects in Brightway](https://docs.brightway.dev/en/latest/content/api/bw2data/parameters/index.html)
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

## Scenarios
