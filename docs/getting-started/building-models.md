---
title: Building models
parent: Getting started
nav_order: 4
---
# Building your system models
{: .fs-9 }

Connecting elementary flows, products and processes through edges.
{: .fs-6 .fw-300 }

In Brightway and Activity Browser system models are defined by linking `nodes` (Processes, Products, and Elementary Flows) through `edges`. Edges represent quantitative relationships between nodes, such as a process producing an amount of product or consuming an amount of elementary flow. By connecting these nodes with edges, you can create a detailed representation of your system.

## Creating nodes
To create nodes in your database, you can use the Activity Browser interface. Open your database, right click to open the context menu and click on the **New process** button to create a new process node. You will be prompted to enter details such as the name, location, and unit of the process.

{: .note-title }
> Implementation detail
> 
> This action will create two nodes: a **Process** node and a **Product** node. The Process node represents the activity or operation, while the Product node represents the output of that process. [Advanced info on backends and node types](../advanced-topics/database-backends.md).

After creating the process, the **Process details page** will open. Here you can view and edit details of the process and see what it consumes and produces.

## Creating edges
Edges are defined as having an input node, and output node and an amount. To create an edge you can simply drag and drop a node from **Products pane** onto the **Process details page**. This will create an edge with the dropped node as the input node, the process as the output node, and a default amount of 1. You can then edit the amount and other details of the edge in the process details page.
