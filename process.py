# -*- coding: utf-8 -*-
from brightway2 import *
from bw2data.utils import recursive_str_to_unicode
import itertools
import numpy as np
import warnings


class SimplifiedProcess(object):
    """A description of a simplified supply chain, which has the following characteristics:

    * It produces one or more outputs (products)
    * It has at least one process from an inventory database
    * It can have links back into the inventory process that are cut; these links can then be replaced at another point with alternative supply chains.
    * It has one scaling activity, which determines the amounts of the various inputs and outputs

    Args:
        * *name* (``str``): Name of the new process
        * *outputs* (``[(key, str, optional float)]``): A list of products produced by the simplified process. Format is ``(key into inventory database, product name, optional amount of product produced)``.
        * *chain* (``[key]``): A list of inventory processes in the supply chain (not necessarily in order).
        * *cuts* (``[(key, key, str)]``): A set of linkages in the supply chain that should be cut. These will appear as **negative** products (i.e. inputs) in the process-product table. Format is (input key, output key, product name).
        * *scaling activity* (key, optional): The reference activity for the supply chain. **Required** for circular supply chains; in simple supply chains, the scaling activity is calculated automatically.

    """
    def __init__(self, name, outputs, chain, cuts, activity=None, **kwargs):
        # TODO: how to get the original data (it is not distributed in the input arguments)?
        self.original_data = None # original user data used to make this simplified process (to be saved in the SPDB)
        self.key = None # exists only of SP is saved to a DB, either manually or through doing lca calculations
        self.name = name
        self.outputs = self.pad_outputs(outputs)
        self.chain = set(chain)  # order doesn't matter, set searching is fast
        self.cuts = cuts
        self.depending_database_names = list(set(c[0] for c in self.chain))
        # TODO: load all databases that are listed in the chain (could depend on multiple DB)
        # TODO: do this with an dict.update() statement
        self.depending_database = self.filter_database(self.chain, Database(self.depending_database_names[0]).load())
        self.edges = self.construct_graph(self.depending_database)
        self.simple, activity_guesses = self.is_simple(self.chain, self.edges)
        if activity and self.simple and activity != activity_guesses[0]:
            self.activity = None
            warnings.warn("Scaling activity must be terminal process in "
                "supply chain")
        elif activity:
            self.activity = activity
        elif self.simple:
            self.activity = activity_guesses[0]
        else:
            self.activity = None
            warnings.warn("Supply chain has no distinct head and no"
                " scaling activity specified")
        self.mapping, self.matrix, self.supply_vector = self.get_supply_vector(self.chain, self.edges,
            self.activity)

    def pad_outputs(self, outputs):
        """Add default amount (1) to outputs if not present.

        Args:
            * *outputs* (list): outputs

        Returns:
            Padded outputs

        """
        return [tuple(x) + (1,) * (3 - len(x)) for x in outputs]

    def filter_database(self, nodes, db):
        """Extract the supply chain for this process from larger database.

        Args:
            * *nodes* (set): The datasets to extract (keys in db dict)
            * *db* (dict): The inventory database, e.g. ecoinvent

        Returns:
            A filtered database, in the same dict format

        """
        return dict([(k, v) for k, v in db.iteritems() if k in self.chain])

    def construct_graph(self, db):
        """Construct a list of edges.

        Args:
            * *db* (dict): The supply chain database

        Returns:
            A list of (in, out, amount) edges.

        """
        return list(itertools.chain(*[[(tuple(e["input"]), k, e["amount"]) for e in v["exchanges"] if e["type"] != "production"] for k, v in db.iteritems()]))

    def is_simple(self, nodes, edges):
        """Does the supply chain have more than one head?

        Calculate by filtering for processes which are not used as inputs.

        Args:
            * *nodes* (set): The supply chain processes
            * *edges* (list): The list of supply chain edges

        Returns:
            Boolean.

        """
        used_inputs = [x[0] for x in edges if x[0] in nodes]
        unused_outputs = set([tuple(x[1]) for x in edges if x[1] not in used_inputs])
        return len(unused_outputs) == 1, list(unused_outputs)

    def get_supply_vector(self, nodes, edges, activity):
        """Construct supply vector (solve linear system) for the supply chain of this simplified product system.

        Args:
            * *nodes* (list): Nodes in supply chain
            * *edges* (list): List of edges
            * *activity* (key): Scaling activity

        Returns:
            Mapping from process keys to supply vector indices
            Supply vector (as list)

        """
        mapping = dict(*[zip(sorted(nodes), itertools.count())])
        M = len(nodes)
        matrix = np.zeros((M, M))
        # Set ones on diagonal; standard LCA stuff
        matrix[range(M), range(M)] = 1
        # Only add edges that are within our system
        # But, allow multiple links to same product (simply add them)
        for in_, out_, a in [x for x in edges if x[0] in nodes and x[1] in nodes]:
            matrix[
                mapping[in_],
                mapping[out_]
            ] -= a
        demand = np.zeros((M,))
        demand[mapping[activity]] = 1
        return mapping, matrix, np.linalg.solve(matrix, demand).tolist()

    @property
    def pp(self):
        """Shortcut, as full method uses no global state"""
        # TODO: self.database gibt es gar nicht...
        return self.process_products(self.chain, self.edges, self.cuts,
            self.outputs, self.activity, self.depending_database_names)

    def process_products(self, nodes, edges, cuts, outputs, activity, database):
        """Provide data for construction of process-product table.

        Note that products from multi-output activities are **not** scaled using the amounts in ``outputs``.

        Args:
            * *nodes* (list): List of processes in supply chain
            * *edges* (list): List of edges from ``construct_graph``
            * *cuts* (list): List of cuts from supply chain to inventory database
            * *outputs* (list): List of products
            * *activity* (key): The scaling activity
            * *database* (dict): Inventory database for supply chain

        Output:
            List of (name, amount) product names and amounts.

        """
        products_from_cuts = [(c[2],
            # Get edge amount
            filter(lambda y: y[0] == c[0] and y[1] == c[1], edges)[0][2] \
            # times supply amount of edge end times -1
            * self.supply_vector[self.mapping[c[1]]] * -1
            ) for c in cuts]

        # Cuts can be from multiple inputs but the same product
        # TODO: TEST
        r = {}
        for product, amount in products_from_cuts:
            r[product] = r.get(product, 0) + amount
        products_from_cuts = list(r.iteritems())

        a_data = database[activity]
        if a_data.get("multioutput", False):
            # Special handling for MO processes
            products_from_outputs = [(o[1], a_data["multioutput"][o[0]]
                ) for o in outputs]
        else:
            # One output from scaling activity or manually-specified
            # multi-output process
            products_from_outputs = [(o[1], o[2]) for o in outputs]

        return products_from_cuts + products_from_outputs

    @property
    def external_edges(self):
        """Get list of edges outside our system, which are not cut"""
        return [x for x in self.edges if (x[0] not in self.chain and \
            x[:2] not in set([y[:2] for y in self.cuts]))]

    @property
    def external_scaled_edges(self):
        """Adjust edge amounts by scaling vector"""
        mapping, matrix, supply_vector = self.get_supply_vector(self.chain, self.edges,
            self.activity)
        return [(x[0], x[1], x[2] * supply_vector[mapping[x[1]]]
            ) for x in self.external_edges]

    @property
    def internal_edges(self):
        return [x for x in self.edges if (x[0] in self.chain and \
            x[:2] not in set([y[:2] for y in self.cuts]))]

    def save_supply_chain_as_new_database(self, db_name="SPDB_default", unit=None,
            location=None, categories=[]):
        """Save simplified process to a database (by default the SPDB_default).

        Creates database if necessary; otherwise *adds* to existing database. Uses the ``unit`` and ``location`` of ``self.activity[0]``, if not otherwise provided. Assumes that one unit of the scaling activity is being produced.

        Args:
            * *db_name* (str): Name of Database
            * *unit* (str, optional): Unit of the simplified process.
            * *location* (str, optional): Location of the simplified process.
            * *categories* (list, optional): Category/ies of the scaling activity.

        """
        metadata = Database(self.activity[0]).load()[self.activity]

        db = Database(db_name)
        if db_name not in databases:
            db.register(format=("Simplified Process", 1))
            data = {}
        else:
            data = db.load()

        self.key = (db_name, self.name)
        unit = unit or metadata.get(u'unit', '')
        location = location or metadata.get(u'location', '')
        data[self.key] = {
            "name": self.name,
            "unit": unit,
            "location": location,
            "categories": categories,
            "type": "process",
            "exchanges": [{
                "amount": exc[2],
                "input": exc[0],
                "type": "biosphere" \
                    if exc[0][0] in (u"biosphere", u"biosphere3") \
                    else "technosphere",
                } for exc in self.external_scaled_edges],
            "original data": self.original_data # the user data at the root of this simplified process
        }
        # Production amount
        data[self.key]["exchanges"].append({
            "amount": 1,
            "input": self.key,
            "type": "production"
        })
        # TODO: Include uncertainty from original databases. Can't just scale
        # uncertainty parameters. Maybe solution is to use "dummy" processes
        # like we want to do to separate inputs of same flow in any case.
        # data = db.relabel_data(data, db_name)
        db.write(recursive_str_to_unicode(data))
        db.process()

    def lca(self, method):
        if not self.activity:
            raise ValueError("No defining activity")
        if hasattr(self, "calculated_lca"):
            self.calculated_lca.method = method
            self.calculated_lca.lcia()
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if not self.key:
                    self.save_supply_chain_as_new_database()
                # TODO: Is scaling correct?
                self.calculated_lca = LCA(demand={self.key: 1}, method=method)
                self.calculated_lca.lci()
                self.calculated_lca.decompose_technosphere()
                self.calculated_lca.lcia()
        return self.calculated_lca.score

    def lci(self):
        if not self.activity:
            raise ValueError("No defining activity")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if not self.key:
                self.save_supply_chain_as_new_database()
            # TODO: Is scaling correct?
            self.calculated_lca = LCA(demand={self.key: 1})
        return self.calculated_lca.lci()

if __name__ == "__main__":
    from reformat import converted_test_data
    converted = converted_test_data()[-1]
    sp = SimplifiedProcess(**converted)
    print "LCA result:"
    print sp.lca((u'IPCC 2007', u'climate change', u'GWP 100a'))
