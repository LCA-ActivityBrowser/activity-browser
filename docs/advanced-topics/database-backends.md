---
title: Database backends
parent: Advanced topics
---
# Different database backends
{: .fs-9 }

How different database backends store nodes and exchanges differently.
{: .fs-6 .fw-300 }

Brightway LCI databases are stored in something called a "backend". The backend is responsible for storing and processing the data that makes up the database. For example, by default Brightway uses the `SQLiteBackend`, which stores your LCI data in a local SQLite database file.

Activity Browser 3 comes shipped with the additional `FunctionalSqliteBackend` which extends the default `SQLiteBackend` with support for multifunctional processes.

## The original SQLiteBackend
The original `SQLiteBackend` stores all activities and exchanges into a local SQLite database file. This database contains two tables: one for nodes and one for edges. Each node has a unique numeric ID. Each edge is defined by an input node, output node and amount.

When these nodes and edges are processed into matrices for LCA calculations, the backend creates a technosphere matrix with the node IDs as row and column indices. As long as you only have single-output processes in your database, this will create a square technosphere matrix that can be inverted during LCA calculations.

### The multifunctionality problem
If you have multifunctional processes in your database, the technosphere matrix will no longer be square. There are different ways to deal with multifunctionality in LCA (e.g. allocation), but for this we need to split multifunctional processes into multiple single-functional nodes.

However, due to the way in which the matrices are built using the node IDs as indices, this cannot be done in a simple manner. As long as these single-functional nodes are not stored in the database with their own unique IDs, we cannot create a square technosphere matrix.
