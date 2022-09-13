# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, division
from bw2calc import LCA
import numpy as np

class GraphTraversal(object):
    """
    Traverse a supply chain, following paths of greatest impact.

    This implementation uses a queue of datasets to assess. As the supply chain is traversed, datasets inputs are added to a list sorted by LCA score. Each activity in the sorted list is assessed, and added to the supply chain graph, as long as its impact is above a certain threshold, and the maximum number of calculations has not been exceeded.

    Because the next dataset assessed is chosen by its impact, not its position in the graph, this is neither a breadth-first nor a depth-first search, but rather "importance-first".

    This class is written in a functional style - no variables are stored in *self*, only methods.

    Should be used by calling the ``calculate`` method.

    .. warning:: Graph traversal with multioutput processes only works when other inputs are substituted (see `Multioutput processes in LCA <http://chris.mutel.org/multioutput.html>`__ for a description of multiputput process math in LCA).

    """

    def calculate(self, demand, method, cutoff=0.005, max_depth=10):
        """
        Traverse the supply chain graph.

        Args:
            * *demand* (dict): The functional unit. Same format as in LCA class.
            * *method* (tuple): LCIA method. Same format as in LCA class.
            * *cutoff* (float, default=0.005): Cutoff criteria to stop LCA calculations. Relative score of total, i.e. 0.005 will cutoff if a dataset has a score less than 0.5 percent of the total.
            * *max_depth* (int, default=10): Maximum depth of the iteration.

        Returns:
            Dictionary of nodes, edges, LCA object, and number of LCA calculations.

        """

        number_acts_in_fu = len(demand)
        if number_acts_in_fu > 1:
            raise ValueError(
                "Number activities in functional unit must be one. Aborting."
            )
        act = list(demand.keys())[0]

        lca, supply, score = self.build_lca(demand, method)
        if score == 0:
            raise ValueError("Zero total LCA score makes traversal impossible")

        # Create matrix of LCIA CFs times biosphere flows, as these don't
        # change. This is also the unit score of each activity.
        characterized_biosphere = np.array(
            (lca.characterization_matrix * lca.biosphere_matrix).sum(axis=0)
        ).ravel()

        from_id = lca.activity_dict[act]
        from_amount = demand[act]
        edges = [
            {
                "to": -1,
                "from": from_id,
                "amount": from_amount,
                "exc_amount": from_amount,
                "impact": score,
                "from_type": "technosphere",
            }
        ]
        self.traverse(
            to_id=from_id,
            to_amount=from_amount,
            depth=0,
            max_depth=max_depth,
            abs_cutoff=abs(cutoff * score),
            edges=edges,
            lca=lca,
            characterized_biosphere=characterized_biosphere,
        )

        # build nodes dict
        rev_act, _, rev_bio = lca.reverse_dict()
        nodes = {-1: {"amount": 1, "cum": lca.score, "ind": 0}}
        for edge in edges:
            id = edge["from"]
            if edge["from_type"] == "technosphere":
                key = rev_act[id]
                if key in nodes:
                    continue
                nodes[key] = {
                    "amount": supply[id],
                    "cum": self.cumulative_score(
                        id, characterized_biosphere, lca
                    )
                    * supply[id],
                    "ind": 0,
                }
            elif edge["from_type"] == "biosphere":
                key = rev_bio[id]
                if key in nodes:
                    continue
                amount = lca.inventory.sum(axis=1)[id].sum() / from_amount
                unit_impact = lca.characterization_matrix[id, id]
                nodes[key] = {
                    "amount": amount,
                    "cum": unit_impact * amount,
                    "ind": unit_impact * amount,
                }

        # replace edge indices by keys
        for edge in edges:
            edge["to"] = (
                rev_act[edge["to"]] if edge["to"] != -1 else edge["to"]
            )
            edge["from"] = (
                rev_act[edge["from"]]
                if edge["from_type"] == "technosphere"
                else rev_bio[edge["from"]]
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "lca": lca,
            "counter": None,
        }

    def build_lca(self, demand, method):
        """Build LCA object from *demand* and *method*."""
        lca = LCA(demand, method)
        lca.lci()
        lca.lcia()
        lca.decompose_technosphere()
        return lca, lca.solve_linear_system(), lca.score

    def cumulative_score(self, index, characterized_biosphere, lca):
        """Compute cumulative LCA score for a given activity"""
        demand = np.zeros(lca.demand_array.shape)
        demand[index] = 1
        return float((characterized_biosphere * lca.solver(demand)).sum())

    def traverse(
        self,
        to_id,
        to_amount,
        lca,
        depth,
        max_depth,
        edges,
        abs_cutoff,
        characterized_biosphere,
    ):

        if depth > max_depth:
            return

        scale_value = lca.technosphere_matrix[to_id, to_id]

        # add biosphere contributions
        bio_inputs = lca.biosphere_matrix[:, to_id] / scale_value
        indices = bio_inputs.nonzero()[0]
        for from_id, from_amount in zip(indices, bio_inputs[indices].data):
            unit_impact = lca.characterization_matrix[from_id, from_id]
            amount = to_amount * from_amount
            scaled_impact = unit_impact * amount
            if abs(scaled_impact) > abs_cutoff:
                edges.append(
                    {
                        "to": to_id,
                        "from": from_id,
                        "amount": amount,
                        "exc_amount": from_amount,
                        "impact": scaled_impact,
                        "from_type": "biosphere",
                    }
                )

        # add technosphere contributions
        techno_inputs = (
            -1 * lca.technosphere_matrix[:, to_id].copy() / scale_value
        )
        techno_inputs[to_id] = 0
        indices = techno_inputs.nonzero()[0]
        for from_id, from_amount in zip(indices, techno_inputs[indices].data):
            unit_impact = self.cumulative_score(
                from_id, characterized_biosphere, lca
            )
            amount = to_amount * from_amount
            scaled_impact = unit_impact * amount
            if abs(scaled_impact) > abs_cutoff:
                edges.append(
                    {
                        "to": to_id,
                        "from": from_id,
                        "amount": amount,
                        "exc_amount": from_amount,
                        "impact": scaled_impact,
                        "from_type": "technosphere",
                    }
                )
                self.traverse(
                    to_id=from_id,
                    to_amount=amount,
                    depth=depth + 1,
                    max_depth=max_depth,
                    abs_cutoff=abs_cutoff,
                    edges=edges,
                    lca=lca,
                    characterized_biosphere=characterized_biosphere,
                )
