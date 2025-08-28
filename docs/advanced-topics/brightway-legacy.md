---
title: Brightway Legacy
parent: Advanced topics
---
# Brighway Legacy projects
{: .fs-9 }

What changed between Brightway Legacy and Brightway25
{: .fs-6 .fw-300 }

For Activity Browser 3 we have moved from Brightway Legacy (=<2.4) to Brightway25. There have been some major changes in the Brightway libraries which have implications for users that want to use their old Brightway Legacy projects in Activity Browser 3.

Most importantly the way in which Brightway processes data from databases into matrices has changed. The matrices or `processed data` are now stored into datapackages with associated metadata, instead of simple numpy arrays. This means that although you can still open and explore your Brightway Legacy projects in Activity Browser 3, you will have to re-process all databases to be able to run actual calculations.

## Migrating your Brightway Legacy projects
When opening a Brightway Legacy project in Activity Browser 3, a warning bar will be shown in the top of the screen with the option to migrate the project. Migrating the project will re-process all data in your project and store the processed data in the new format. It will also update some of your datasets to be compatible with Brightway25. The migration process can take a while depending on the size of your databases.

{: .warning }
> Migrating a project is a one-way operation. Once you have migrated a project, you cannot go back to the Brightway Legacy format. It is recommended to make a backup or copy of your Brightway Legacy projects before migrating them.
