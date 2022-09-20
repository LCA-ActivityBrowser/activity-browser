# -*- coding: utf-8 -*-
from dataclasses import dataclass
from heapq import heappop, heappush
from numbers import Real
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    SupportsInt,
    Tuple,
    Union,
)

import numpy as np
from bw2calc import LCA


@dataclass
class GTNode:
    index: SupportsInt
    amount: Optional[Real] = None
    cum: Optional[Real] = None
    ind: Optional[Real] = None
    key: Optional[Tuple] = None

    def __lt__(self, other):
        """Compare two nodes based on the size of their individual impact.
        This function guarantees that ordering in heapq algorithm doesn't
        raise errors when two nodes have the same priority (cumulative impact)."""
        return self.ind < other.ind

    def __hash__(self):
        return hash((self.index, self.amount, self.cum, self.ind))

    def to_dict(self) -> Dict:
        return {"amount": self.amount, "cum": self.cum, "ind": self.ind}


class GTTechnosphereNode(GTNode):
    def __init__(
        self,
        index: int,
        lca: LCA,
        cb: np.array,
        include_biosphere: bool,
        key: Optional[Tuple] = None,
    ):
        super().__init__(index=index, key=key)
        self._unit_score = self.__unit_score(lca=lca, cb=cb)
        self.amount = self._lci_amount(lca=lca)
        self.cum = self.scaled_score(factor=self.amount)
        self.ind = self._individual_score(
            lca=lca, cb=cb, include_biosphere=include_biosphere
        )

    def _lci_amount(self, lca: LCA) -> Real:
        return (
            lca.supply_array[self.index]
            * lca.technosphere_matrix[self.index, self.index]
        )

    def _individual_score(
        self, lca: LCA, cb: np.array, include_biosphere: bool
    ) -> float:
        """Compute the direct impact caused by the emissions and resource consumption of a given activity"""
        if include_biosphere:
            return 0
        else:
            return float(cb[self.index] * lca.supply_array[self.index])

    def __unit_score(self, lca: LCA, cb: np.array) -> float:
        """Compute LCA score for one unit of a given technosphere activity"""
        demand = np.zeros(lca.demand_array.shape)
        demand[self.index] = 1
        return float((cb * lca.solver(demand)).sum())

    def scaled_score(self, factor: Real) -> Real:
        return self._unit_score * factor


class GTBiosphereNode(GTNode):
    def __init__(
        self,
        index: int,
        lca: LCA,
        key: Optional[Tuple] = None,
    ):
        super().__init__(index=index, key=key)
        self._unit_score = self.__unit_score(lca=lca)
        lci_amount = self._lci_amount(lca=lca)
        self.amount = lci_amount
        self.cum = self.scaled_score(factor=lci_amount)
        self.ind = self._individual_score(lci_amount=lci_amount)

    def _lci_amount(self, lca: LCA) -> float:
        return float(lca.inventory.sum(axis=1)[self.index])

    def _individual_score(self, lci_amount: Real) -> Real:
        """Compute the direct impact caused by the emissions and resource consumption of a given activity"""
        return self._unit_score * lci_amount

    def __unit_score(self, lca: LCA) -> Real:
        """Compute LCA score for one unit of a given biosphere activity"""
        return lca.characterization_matrix[self.index, self.index]

    def scaled_score(self, factor: Real) -> Real:
        return self._unit_score * factor


class GTNodeSet:
    def __init__(self, nodes: Optional[Iterable[GTNode]] = ()):
        self.nodes = set(nodes)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self.nodes, attr)

    def get_by_index(self, index: int) -> Optional[GTNode]:
        for node in self.nodes:
            if node.index == index:
                return node
        return None

    def add_node_keys(self, rev_act: Dict, rev_bio: Dict) -> None:
        for n in self.nodes:
            if n.index == -1:
                n.key = -1
            else:
                rev_dict = (
                    rev_act if isinstance(n, GTTechnosphereNode) else rev_bio
                )
                n.key = rev_dict[n.index]

    def to_dict(self, use_keys: bool = True) -> Dict:
        if use_keys:
            return {n.key: n.to_dict() for n in self.nodes}
        else:
            return {n.index: n.to_dict() for n in self.nodes}

    def __repr__(self):
        return self.nodes.__repr__()


@dataclass
class GTEdge:
    to_node: GTNode
    from_node: GTNode
    amount: Real
    exc_amount: Real
    impact: Real

    def to_dict(self, use_keys: bool = True) -> Dict:
        if use_keys:
            return {
                "to": self.to_node.key,
                "from": self.from_node.key,
                "amount": self.amount,
                "exc_amount": self.exc_amount,
                "impact": self.impact,
            }
        else:
            return {
                "to": self.to_node.index,
                "from": self.from_node.index,
                "amount": self.amount,
                "exc_amount": self.exc_amount,
                "impact": self.impact,
            }


class GTEdgeList:
    def __init__(self, edges: Optional[List[GTEdge]] = None):
        self.edges = edges or []

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self.edges, attr)

    def get(
        self,
        to_node: GTNode,
        from_node: GTNode,
    ) -> Optional[Union[GTBiosphereNode, GTTechnosphereNode]]:
        for edge in self.edges:
            if edge.to_node == to_node and edge.from_node == from_node:
                return edge
        return None

    def to_list(self, use_keys: bool = True) -> List[Dict]:
        return [e.to_dict(use_keys) for e in self.edges]

    def get_unique_nodes(self) -> Set[GTNode]:
        return set(
            [e.from_node for e in self.edges] + [e.to_node for e in self.edges]
        )

    def __repr__(self):
        return self.edges.__repr__()


class GraphTraversal:
    """
    Traverse a supply chain, following paths of greatest impact.

    This implementation uses a queue of datasets to assess. As the supply chain is traversed, datasets inputs are added to a list sorted by LCA score. Each activity in the sorted list is assessed, and added to the supply chain graph, as long as its impact is above a certain threshold, and the maximum number of calculations has not been exceeded.

    Because the next dataset assessed is chosen by its impact, not its position in the graph, this is neither a breadth-first nor a depth-first search, but rather "importance-first".

    This class is written in a functional style - no variables are stored in *self*, only methods.

    Should be used by calling the ``calculate`` method.

    .. warning:: Graph traversal with multioutput processes only works when other inputs are substituted (see `Multioutput processes in LCA <http://chris.mutel.org/multioutput.html>`__ for a description of multiputput process math in LCA).

    """

    def __init__(
        self,
        use_keys: bool = True,
        include_biosphere: bool = True,
        importance_first: bool = True,
    ):
        # class options
        self.use_keys: bool = use_keys
        self.include_biosphere: bool = include_biosphere
        if importance_first:
            self.traverse: Callable = self.traverse_importance_first
        else:
            self.traverse: Callable = self.traverse_depth_first

        # traversal helper variables
        self.lca: Optional[LCA] = None
        self.score: Optional[Real] = None
        self.cb: Optional[np.array] = None
        self.rev_act: Optional[Dict] = None
        self.rev_bio: Optional[Dict] = None
        self.edge_list: Optional[GTEdgeList] = None
        self.bio_node_list: Optional[GTNodeSet] = None
        self.techno_node_list: Optional[GTNodeSet] = None
        self.number_calcs: Optional[int] = None

    def reset(self, demand, method) -> List[Tuple[GTTechnosphereNode, Real]]:

        # calculate lci, supply, score
        self.lca = LCA(demand, method)
        self.lca.lci()
        self.lca.lcia()
        self.score = self.lca.score

        if self.score == 0:
            raise ValueError("Zero total LCA score makes traversal impossible")

        # decompose technosphere to speed up later re-calculations
        self.lca.decompose_technosphere()

        # Create matrix of LCIA CFs times biosphere flows, as these don't
        # change. This is also the unit score of each activity.
        self.cb = np.array(
            (self.lca.characterization_matrix * self.lca.biosphere_matrix).sum(
                axis=0
            )
        ).ravel()

        # make lookup dictionaries: matrix index -> activity key
        self.rev_act, _, self.rev_bio = self.lca.reverse_dict()

        # initialize node and edge list
        root = GTNode(index=-1, amount=1, cum=self.score, ind=0)
        self.techno_node_list = GTNodeSet([root])
        self.bio_node_list = GTNodeSet()
        self.edge_list = GTEdgeList()

        # add functional unit nodes and edges
        fu_node_amount = []
        for fu_key, fu_amount in demand.items():
            fu_index = self.lca.activity_dict[fu_key]
            fu_node = GTTechnosphereNode(
                index=fu_index,
                lca=self.lca,
                cb=self.cb,
                include_biosphere=self.include_biosphere,
            )
            self.techno_node_list.add(fu_node)

            edge = GTEdge(
                to_node=root,
                from_node=fu_node,
                amount=fu_amount,
                exc_amount=fu_amount,
                impact=fu_node.scaled_score(fu_amount),
            )
            self.edge_list.append(edge)

            fu_node_amount.append((fu_node, fu_amount))

        # reset calculation counter
        self.number_calcs = 0

        return fu_node_amount

    def calculate(
        self,
        demand: Dict,
        method: Tuple[str, ...],
        cutoff: Real = 0.005,
        max_depth: int = 10,
        max_calc: int = 10000,
    ) -> Dict:
        """
        Traverse the supply chain graph.

        Args:
            * *demand* (dict): The functional unit. Same format as in LCA class.
            * *method* (tuple): LCIA method. Same format as in LCA class.
            * *cutoff* (float, default=0.005): Cutoff criteria to stop LCA calculations. Relative score of total, i.e. 0.005 will cutoff if a dataset has a score less than 0.5 percent of the total.
            * *max_depth* (int, default=10): Maximum depth of the iteration.
            * *max_calc* (int, default=10000): Maximum number of LCA calculation to perform.

        Returns:
            Dictionary of nodes, edges, LCA object, and number of LCA calculations.

        """

        fu_node_amount = self.reset(demand, method)

        for fu_node, fu_amount in fu_node_amount:
            self.traverse(
                to_node=fu_node,
                to_amount=fu_amount,
                depth=0,
                max_depth=max_depth,
                max_calc=max_calc,
                abs_cutoff=abs(cutoff * self.score),
            )

        # filter nodes: only keep nodes contained in edge list
        node_list = GTNodeSet(self.edge_list.get_unique_nodes())

        # add node.key information
        if self.use_keys:
            node_list.add_node_keys(self.rev_act, self.rev_bio)

        return {
            "nodes": node_list.to_dict(self.use_keys),
            "edges": self.edge_list.to_list(self.use_keys),
            "lca": self.lca,
            "counter": self.number_calcs,
        }

    def _get_or_add_biosphere_node(self, index: int) -> GTBiosphereNode:
        node = self.bio_node_list.get_by_index(index)
        if not node:
            node = GTBiosphereNode(index=index, lca=self.lca)
            self.bio_node_list.add(node)
        return node

    def _get_or_add_technosphere_node(self, index: int) -> GTTechnosphereNode:
        node = self.techno_node_list.get_by_index(index)
        if not node:
            node = GTTechnosphereNode(
                index=index,
                lca=self.lca,
                cb=self.cb,
                include_biosphere=self.include_biosphere,
            )
            self.techno_node_list.add(node)
        return node

    def _add_edge_if_above_cutoff(
        self,
        from_node: Union[GTTechnosphereNode, GTBiosphereNode],
        from_amount: Real,
        to_node: GTNode,
        to_amount: Real,
        abs_cutoff: Real,
    ) -> Optional[GTEdge]:
        amount = to_amount * from_amount
        self.number_calcs += 1
        scaled_impact = from_node.scaled_score(factor=amount)
        if abs(scaled_impact) > abs_cutoff:
            edge = GTEdge(
                to_node=to_node,
                from_node=from_node,
                amount=amount,
                exc_amount=from_amount,
                impact=scaled_impact,
            )
            self.edge_list.append(edge)
            return edge
        else:
            return None

    def traverse_depth_first(
        self,
        to_node: GTNode,
        to_amount: Real,
        depth: int,
        max_depth: int,
        max_calc: int,
        abs_cutoff: Real,
    ) -> None:

        if depth >= max_depth:
            print(f"Max. depth reached at activity id {to_node.index}")
            return

        if self.number_calcs >= max_calc:
            print(
                f"Max. number calculations reached at activity id {to_node.index}"
            )
            return

        scale_value = self.lca.technosphere_matrix[
            to_node.index, to_node.index
        ]

        # add biosphere contributions
        if self.include_biosphere:
            bio_inputs = (
                self.lca.biosphere_matrix[:, to_node.index] / scale_value
            )
            indices = bio_inputs.nonzero()[0]
            for from_index, from_amount in zip(
                indices, bio_inputs[indices].data
            ):
                from_node = self._get_or_add_biosphere_node(index=from_index)
                self._add_edge_if_above_cutoff(
                    from_node=from_node,
                    from_amount=from_amount,
                    to_node=to_node,
                    to_amount=to_amount,
                    abs_cutoff=abs_cutoff,
                )

        # add technosphere contributions
        techno_inputs = (
            -1 * self.lca.technosphere_matrix[:, to_node.index] / scale_value
        )
        indices = techno_inputs.nonzero()[0]
        for from_index, from_amount in zip(
            indices, techno_inputs[indices].data
        ):
            # skip diagonal entries
            if from_index == to_node.index:
                continue

            # get node from node list or create new one if it doesn't exist
            from_node = self._get_or_add_technosphere_node(index=from_index)

            # create new edge
            edge = self._add_edge_if_above_cutoff(
                from_node=from_node,
                from_amount=from_amount,
                to_node=to_node,
                to_amount=to_amount,
                abs_cutoff=abs_cutoff,
            )

            # go deep if edge impact is above cutoff
            if edge:
                self.traverse(
                    to_node=from_node,
                    to_amount=edge.amount,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_calc=max_calc,
                    abs_cutoff=abs_cutoff,
                )

    def traverse_importance_first(
        self,
        to_node: GTNode,
        to_amount: Real,
        depth: int,
        max_depth: int,
        max_calc: int,
        abs_cutoff: Real,
    ) -> None:

        heap = []
        heappush(heap, (0, to_node, to_amount, depth))

        while heap:

            _, to_node, to_amount, depth = heappop(heap)

            if self.number_calcs >= max_calc:
                print(
                    f"Max. number calculations reached at activity id {to_node.index}"
                )
                return

            if depth >= max_depth:
                print(f"Max. depth reached at activity id {to_node.index}")
                continue

            to_scale = self.lca.technosphere_matrix[
                to_node.index, to_node.index
            ]

            # add biosphere contributions
            if self.include_biosphere:
                bio_inputs = (
                    self.lca.biosphere_matrix[:, to_node.index] / to_scale
                )
                indices = bio_inputs.nonzero()[0]
                for from_index, from_amount in zip(
                    indices, bio_inputs[indices].data
                ):
                    from_node = self._get_or_add_biosphere_node(
                        index=from_index
                    )
                    self._add_edge_if_above_cutoff(
                        from_node=from_node,
                        from_amount=from_amount,
                        to_node=to_node,
                        to_amount=to_amount,
                        abs_cutoff=abs_cutoff,
                    )

            # add technosphere contributions
            techno_inputs = (
                -1 * self.lca.technosphere_matrix[:, to_node.index] / to_scale
            )
            indices = techno_inputs.nonzero()[0]
            for from_index, from_amount in zip(
                indices, techno_inputs[indices].data
            ):
                # skip diagonal entries
                if from_index == to_node.index:
                    continue

                # get node from node list or create new one if it doesn't exist
                from_node = self._get_or_add_technosphere_node(
                    index=from_index
                )

                # create new edge
                edge = self._add_edge_if_above_cutoff(
                    from_node=from_node,
                    from_amount=from_amount,
                    to_node=to_node,
                    to_amount=to_amount,
                    abs_cutoff=abs_cutoff,
                )

                # add source to priority list if edge impact is above cutoff
                if edge:
                    heappush(
                        heap,
                        (
                            abs(1 / from_node.cum),
                            from_node,
                            edge.amount,
                            depth + 1,
                        ),
                    )
