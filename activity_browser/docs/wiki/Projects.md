Projects are one of the many ways in which [Brightway](https://docs.brightway.dev/en/latest/) helps you structure your data. A project is a standalone
environment in which you store your [LCI databases](Databases), [Impact Categories](Impact-Categories), [Calculation Setups](LCA-Calculation-Setups) and any other data. Data that
is stored in project **One** cannot be used in project **Two** and vice versa. Use this to your advantage in any way you like.

Projects are stored separately from your Activity Browser installation in a folder dependent on your operating system
and user preferences. This means you can install multiple version of Activity Browser and access the same projects. It 
also means that removing Activity Browser is not going to fix any issues related to your project.

If you want to know where a particular project is stored, check the Activity Browser console window, which will display 
the folder for the current project when you open it.

## Selecting a project

When you launch the Activity Browser you will be dropped into your startup project, Brightway's "default" project by
default. You can always see what project you are in by checking the window title bar, the toolbar at the bottom of the
screen, or see what project is selected in the drop-down menu at the top of the project tab.

You can switch between projects in one of two ways: you can either choose a project from project tab's drop-down menu, 
or through the `Project` menu in the main menu bar.

- `Project` > `Open project` > _Choose your desired project_

## Creating a new project
 
You can create a new project by either clicking the `New` button at the top of the Project tab, or through the
`Project` menu in the main menu bar.

- `Project` > `New`

You'll be asked to provide a unique name for your new project, after which the Activity Browser will switch to your new
project and allow you to setup your project in any way you like.

## Deleting a project
You can delete your current project by either clicking the `Delete` button at the top of the Project tab, or through the
`Project` menu in the main menu bar.

- `Project` > `Delete`

You'll be asked for confirmation and whether you want to delete the project folder from the disk as well. If you do not
delete your project from disk, Brightway will just unregister the project, which will hide it from the project selection
menu's, but the data is preserved in the project folder mentioned above. If you choose to delete it from disk entirely,
the project and it's data are removed entirely.

## Duplicating a project
You can duplicate your current project by either clicking the **Duplicate** button at the top of the Project tab, or through the
`Project` menu in the main menu bar.

- `Project` > `Duplicate`

You'll be asked to provide a unique name for your duplicate project, after which the Activity Browser will switch to this
project. This feature is handy if you want to test out anything that may break your data, by first duplicating your project
you ensure that your data is preserved if you want to return to it.

## Exporting a project
You can export your entire project to a .7z archive. This archive will contain all data stored within the project like
LCI databases, Impact Categories and Calculation Setups. You can export your project through the `Project` menu in the
main menu bar.

- `Project` > `Export this project`

You will be asked for a location the .7z archive with your project data should be saved to. Exporting may take a while 
to complete.

## Importing a project
Similarly, you can also import a project that has been exported to a .7z archive. You can import the project through the
`Project` menu in the main menu bar.

- `Project` > `Import a project`

You will be prompted for a unique project name, after which the project will be installed and the Activity Browser will
switch to your imported project.

## A note on Brightway25 projects
Brightway25 is not yet officially supported by the Activity Browser. Projects created using Brightway25 use a different
structure and managing them through the Activity Browser may cause breaking issues. Brightway25 projects are shown in
the project selection menus, but disabled for this reason. 

If you know what you're doing feel free to enable these projects by setting the `AB_BW25` environmental variable. Needless
to say this is at your own risk.
