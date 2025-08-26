---
title: Project setup
parent: Getting started
nav_order: 2
---
# Setting up a project
{: .fs-9 }

Projects are the main way to organize your work in Activity Browser and Brightway.
{: .fs-6 .fw-300 }

A project in Activity Browser is a folder on your computer that contains all the files related to your work in Activity Browser. This includes databases, LCA calculation setups, results, and any other relevant files. 

Projects are shared with Brightway, so you can also access them using Brightway's Python interface. They are also independent of the Activity Browser installation: deleting or updating Activity Browser will not affect your projects. You can even have multiple versions of Activity Browser installed on your computer and use the same project with all of them. By default your projects are stored in the following location:
- **Windows:** `C:\Users\<YourUsername>\AppData\Local\pylca\Brightway3`
- **MacOS/Linux [UPDATE THIS]:** `/Users/<YourUsername>/Documents/ActivityBrowser/Projects`

## Creating a new project
How to create a new project in the Activity Browser depends on how you want to set up the base data (e.g. elementary flows and impact categories). You can either start from scratch and import the data you need yourself, or you can use a Brightway template project, that will come pre-loaded with a specific database and impact categories.

### Create a new empty project
To create a new empty project, open the **Project** menu in the top left corner of the application window and select **New project > Empty project**.

You will be prompted to enter a name for your new project. Choose a descriptive name that will help you identify the project later. After entering the name, click **Ok**. The new project will be created and set as the active project in Activity Browser.

### Create a new project from a Brightway template
To create a new project from a Brightway template, open the **Project** menu in the top left corner of the application window and select **New project > From template**. This will show a list of available Brightway templates. Choose the template that best fits your needs.

You will be prompted to enter a name for your new project. Choose a descriptive name that will help you identify the project later. After entering the name, click **Ok**. The new project will be downloaded, created, and set as the active project in Activity Browser.

## Importing an existing project or backup
Brightway projects can be easily shared and transferred between different computers. If you have received a Brightway project folder from someone else, or if you have a backup of your own project, you can import it into Activity Browser.

To import an existing project or backup, open the **Project** menu in the top left corner of the application window and select **Import a project...**. You will be prompted to select the .7z file containing the Brightway project you want to import. You will be prompted to enter a name for the project after which it will be imported and set as the active project in Activity Browser.
