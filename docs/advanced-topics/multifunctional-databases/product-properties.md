---
title: Product properties
parent: Functional SQLite
nav_order: 2
---
# Product properties
{: .fs-9 }

Defining properties for products in the Functional SQLite backend.
{: .fs-6 .fw-300 }

In the `FunctionalSqliteBackend`, products can have additional properties that define their characteristics. These properties can be used to store information such as mass, price, or any other relevant numerical attributes that can be used to [allocate](allocation.md) the process edges to its products.

## Defining product properties
In the Activity Browser 3, you can define product properties when editing a process. Click on the **Add property...** button in the header of the Process details. Here you can define a property name, unit, and whether the property should be normalized with the production amount. After clicking **Ok** the property will be added to all products of the process with an initial amount of `1`.

## The structure of product properties
Product properties are defined in the `properties` attribute of a product node. This is a dictionary where the keys are the names of the different properties, the values are property definitions with the following structure:
```python
{
    "amount": float | int, # The numerical value of the property
    "unit": str, # The unit of the property (e.g. "kg", "USD")
    "normalize": bool # Whether this property should be normalized with the production amount
}
```