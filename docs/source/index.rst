.. Meta Processes documentation master file, created by
   sphinx-quickstart on Tue Feb 03 16:33:15 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Activity Browser
================

The activity browser is a free `LCA <http://en.wikipedia.org/wiki/Life-cycle_assessment>`_ software.
It relies on `brightway2 <http://brightwaylca.org/>`_ for much of its functionality (e.g. LCA calculations and database management). It extends brightway2 through a graphical user interface (GUI) increasing the efficiency of certain tasks.

As it is open source, you can add your own extensions.


Features
--------

Core features currently involve:

- fast browser-inspired navigation through inventory databases 
- creating and modifying inventories and databases
- fast LCA calculations (even multi-inventory-multi-method)


Extensions
----------

A tool for modeling life cycles based on a :ref:`Meta-Processes Concept <_introduction-metaprocesses>`, which enables:

- modeling inventories at a meta-level, e.g. life cycle stages 
- linking meta-processes to represent complete, possibly new life cycles
- efficient modeling of alternative life cycles
- efficient coupling of LCA and optimization


Documentation
---------------------

.. toctree::
   :maxdepth: 1

   installation
   introduction-metaprocesses

.. Class reference
.. ---------------

.. .. toctree::
..    :maxdepth: 2

..    metaprocess
..    linkedmetaprocess


Contact
-------
`Bernhard Steubing <steubing@ifu.baug.ethz.ch>`_


License
-------

The project is licensed under the GNU General Public License.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

