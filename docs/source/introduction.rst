.. _introduction:

Introduction to Meta-Processes
******************************

Meta-Processes
--------------

.. image:: images/mp.png
    :align: center

Meta-Processes can group several life cycle inventories into a single process. 

Meta-Processes *need* to have:

	* a name
	* at least one product output with a user defined name
	* at least one activity
	* a scaling activity (determined autmatically)

Meta-Processes *can* have:

	* additional processes forming the process chain
	* multiple outputs
	* multiple inputs; product inputs involve a cut-off


System of Linked Meta-Processes
-------------------------------

.. image:: images/lmp.png
    :align: center

Linked Meta-Process Systems are created by combining meta-processes based on their product inputs and outputs. As shown in the example, the product based linking allows to efficiently specify alternative supply chains.

A detailed description of the math behind meta-processes, its application scope and examples are provided in the following paper (not yet available). 