"""Sequential scenario datapackage input for Scenario LCA.

One package per calculation. Inclusion slices columns into an in-memory package;
the file on disk is left unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

NO_PATH = "no_path"
MISSING = "missing"
UNREADABLE = "unreadable"
EMPTY = "empty"

_ARRAY_KINDS = ("indices", "data", "flip")


class ScenarioDatapackageError(ValueError):
    """The path is not a readable sequential scenario datapackage."""


@dataclass(frozen=True)
class ScenarioDatapackageContents:
    """Scenario names in column order, and the loaded package."""

    names: list[str]
    used_fallback: bool
    package: Any


def read_scenario_datapackage(path: str | Path) -> ScenarioDatapackageContents:
    """Load one sequential scenario datapackage and its scenario names.

    Names are the ordered ``scenario_labels`` list when ``scenario_count`` and
    every scenario data array agree with that list. Otherwise the names are
    ``Scenario 0`` … ``Scenario n-1`` and ``used_fallback`` is true.
    """
    package = _load_package(path)
    if not package.metadata.get("sequential") or package.metadata.get("combinatorial"):
        raise ScenarioDatapackageError(
            "Not a sequential scenario datapackage."
        )
    groups = _array_groups(package)
    width = _shared_width(groups)
    names, used_fallback = _scenario_names(package, width)
    return ScenarioDatapackageContents(
        names=names,
        used_fallback=used_fallback,
        package=package,
    )


def subset_scenario_datapackage(package: Any, ordered_names: list[str], all_names: list[str]):
    """In-memory sequential package limited to ``ordered_names``.

    Columns stay in ``all_names`` order. Indexes and flip arrays are copied.
    Nothing is written back to the source package.
    """
    import bw_processing as bwp

    indexes = [all_names.index(name) for name in ordered_names]
    subset = bwp.create_datapackage(
        name=(package.metadata.get("name") or "scenarios"),
        sequential=True,
        metadata={
            "scenario_labels": list(ordered_names),
            "scenario_count": len(ordered_names),
        },
    )
    for group in _array_groups(package).values():
        data = np.ascontiguousarray(np.asarray(group["data"])[:, indexes])
        kwargs = {
            "matrix": group["matrix"],
            "name": group["name"],
            "indices_array": np.asarray(group["indices"]),
            "data_array": data,
        }
        if "flip" in group:
            kwargs["flip_array"] = np.asarray(group["flip"])
        subset.add_persistent_array(**kwargs)
    return subset


def datapackage_calculation_refusal(path, included) -> str | None:
    """Why Calculate must stop, or ``None`` when the datapackage side can run."""
    if path is None or str(path).strip() == "":
        return NO_PATH
    file_path = Path(path)
    if not file_path.exists():
        return MISSING
    try:
        contents = read_scenario_datapackage(file_path)
    except ScenarioDatapackageError:
        return UNREADABLE
    chosen = [name for name in contents.names if name in set(included or [])]
    if not chosen:
        return EMPTY
    return None


def _load_package(path: str | Path):
    from bw2calc.utils import get_datapackage

    file_path = Path(path)
    if not file_path.exists():
        raise ScenarioDatapackageError(f"Scenario datapackage not found: {file_path}")
    try:
        return get_datapackage(file_path)
    except ScenarioDatapackageError:
        raise
    except Exception as exc:
        raise ScenarioDatapackageError(
            f"Could not read scenario datapackage: {file_path}"
        ) from exc


def _array_groups(package) -> dict[str, dict]:
    groups: dict[str, dict] = {}
    for resource in package.resources:
        if resource.get("category") != "array":
            continue
        kind = resource.get("kind")
        if kind not in _ARRAY_KINDS:
            continue
        data, _meta = package.get_resource(resource["name"])
        group = groups.setdefault(
            resource["group"],
            {"matrix": resource.get("matrix"), "name": resource["group"]},
        )
        group[kind] = np.asarray(data)
    if not groups:
        raise ScenarioDatapackageError(
            "Scenario datapackage has no scenario data arrays."
        )
    return groups


def _shared_width(groups: dict[str, dict]) -> int:
    widths: list[int] = []
    for group in groups.values():
        data = group.get("data")
        if data is None or getattr(data, "ndim", 0) != 2 or "indices" not in group:
            raise ScenarioDatapackageError(
                "Scenario datapackage is missing a scenario data array."
            )
        widths.append(int(data.shape[1]))
    if not widths or len(set(widths)) != 1 or widths[0] < 1:
        raise ScenarioDatapackageError(
            "Scenario data arrays do not share one scenario-column count."
        )
    return widths[0]


def _scenario_names(package, width: int) -> tuple[list[str], bool]:
    labels = package.metadata.get("scenario_labels")
    if isinstance(labels, np.ndarray):
        labels = labels.tolist()
    count = package.metadata.get("scenario_count")
    fallback = [f"Scenario {index}" for index in range(width)]
    if not isinstance(labels, (list, tuple)) or len(labels) != width:
        return fallback, True
    names = [str(label) for label in labels]
    if len(set(names)) != width:
        return fallback, True
    if count is None or int(count) != width:
        return fallback, True
    return names, False


def _mapping_value(mapping, method, fu_key):
    """Pick the MultiLCA result stored for one impact category and reference flow."""
    method_t = tuple(method)
    candidates = (
        (method, fu_key),
        (method_t, fu_key),
        (fu_key, method),
        (fu_key, method_t),
    )
    for key in candidates:
        try:
            if key in mapping:
                return mapping[key]
        except TypeError:
            continue
    for key, value in mapping.items():
        if not isinstance(key, tuple) or len(key) != 2:
            continue
        left, right = key
        left_t = tuple(left) if isinstance(left, (list, tuple)) else left
        right_t = tuple(right) if isinstance(right, (list, tuple)) else right
        if (left_t == method_t and right == fu_key) or (
            right_t == method_t and left == fu_key
        ):
            return value
    raise KeyError(
        f"No result for method {method!r} and reference flow {fu_key!r}. "
        f"Keys: {list(mapping)[:6]!r}"
    )


def _demand_cache_key(demand: dict) -> tuple:
    import bw2data as bd

    items = []
    for key, amount in demand.items():
        if hasattr(key, "id"):
            node_id = int(key.id)
        elif isinstance(key, int):
            node_id = int(key)
        else:
            node_id = int(bd.get_activity(key).id)
        items.append((node_id, float(amount)))
    return tuple(sorted(items))


class ABMultiLCA:
    """Datapackage Scenario LCA results in the shape LCA Results already reads.

    Built on one Brightway ``MultiLCA`` with ``use_arrays``. Each included
    scenario is stored while it is current. ``set_scenario`` only moves
    ``current``; it does not calculate again.
    """

    def __init__(self, cs_name: str, path: str | Path, included, cs: dict | None = None):
        import bw2calc as bc
        import bw2data as bd

        from activity_browser.bwutils.multilca import _load_cs

        contents = read_scenario_datapackage(path)
        chosen = [name for name in contents.names if name in set(included or [])]
        if not chosen:
            raise ScenarioDatapackageError("No scenarios selected")

        self.cs_name = cs_name
        self.source_path = str(path)
        self.scenario_names = chosen
        self.total = len(chosen)
        self.scenario_index = {name: index for index, name in enumerate(chosen)}
        self._current = 0
        self._singular: dict[tuple, Any] = {}

        try:
            stored = cs if cs is not None else bd.calculation_setups[cs_name]
        except KeyError as exc:
            raise ValueError(f"{cs_name} is not a known `calculation_setup`.") from exc
        _load_cs(self, stored["inv"], stored["ia"])
        self.method_index = {method: index for index, method in enumerate(self.methods)}
        self.rev_method_index = {index: method for method, index in self.method_index.items()}
        self.scenario_labels = {index: name for index, name in enumerate(self.scenario_names)}

        self.scenario_package = subset_scenario_datapackage(
            contents.package, self.scenario_names, contents.names
        )
        demands = {
            key: {bd.get_activity(flow).id: amount for flow, amount in fu.items()}
            for key, fu in self.fu_demands.items()
        }
        data_objs = list(
            bd.get_multilca_data_objs(
                functional_units=demands,
                method_config={"impact_categories": self.methods},
            )
        )
        data_objs.append(self.scenario_package)
        self.lca = bc.MultiLCA(
            demands=demands,
            method_config={"impact_categories": self.methods},
            data_objs=data_objs,
            use_arrays=True,
        )
        self.lca.lci()
        self.lca.lcia()
        (
            self.rev_activity_dict,
            self.rev_product_dict,
            self.rev_biosphere_dict,
        ) = (
            self.lca.dicts.activity.reversed,
            self.lca.dicts.product.reversed,
            self.lca.dicts.biosphere.reversed,
        )
        self.method_matrices = [
            self._characterization_matrix(method) for method in self.methods
        ]
        n_fu = len(self.func_units)
        n_methods = len(self.methods)
        n_bio = self.lca.biosphere_matrix.shape[0]
        n_tech = self.lca.technosphere_matrix.shape[0]
        self.lca_scores = np.zeros((n_fu, n_methods, self.total))
        self.elementary_flow_contributions = np.zeros((n_fu, n_methods, self.total, n_bio))
        self.process_contributions = np.zeros((n_fu, n_methods, self.total, n_tech))
        self.scaling_factors = {}
        self.technosphere_flows = {}
        self.inventory = {}
        self.inventories = {}
        self.characterized_inventories = {}

    def _characterization_matrix(self, method):
        matrices = self.lca.characterization_matrices
        if method in matrices:
            return matrices[method].copy()
        method_t = tuple(method)
        for key, matrix in matrices.items():
            key_t = tuple(key) if isinstance(key, (list, tuple)) else key
            if key_t == method_t:
                return matrix.copy()
        raise KeyError(method)

    def calculate(self) -> None:
        """Walk each included scenario once and store its results."""
        self.lca.keep_first_iteration()
        for index in range(self.total):
            next(self.lca)
            self._capture(index)

    def _capture(self, scenario_index: int) -> None:
        lca = self.lca
        for row, fu_key in enumerate(self.fu_keys):
            supply = np.array(lca.supply_arrays[fu_key], copy=True)
            self.scaling_factors[(fu_key, scenario_index)] = supply
            self.technosphere_flows[(fu_key, scenario_index)] = np.multiply(
                supply, lca.technosphere_matrix.diagonal()
            )
            inventory = lca.inventories[fu_key]
            self.inventory[(fu_key, scenario_index)] = np.ravel(
                np.asarray(inventory.sum(axis=1))
            )
            self.inventories[(fu_key, scenario_index)] = inventory.copy()
            for col, method in enumerate(self.methods):
                characterized = _mapping_value(
                    lca.characterized_inventories, method, fu_key
                )
                self.characterized_inventories[(row, col, scenario_index)] = (
                    characterized.copy()
                )
                self.lca_scores[row, col, scenario_index] = float(
                    np.asarray(characterized.sum())
                )
                self.elementary_flow_contributions[row, col, scenario_index, :] = np.ravel(
                    np.asarray(characterized.sum(axis=1))
                )
                self.process_contributions[row, col, scenario_index, :] = np.ravel(
                    np.asarray(characterized.sum(axis=0))
                )

    @property
    def current(self) -> int:
        return self._current

    @current.setter
    def current(self, value: int) -> None:
        self._current = int(value)

    def set_scenario(self, index: int) -> None:
        """Point result tabs at a stored scenario. Does not calculate."""
        self.current = index

    @property
    def lca_scores_normalized(self) -> np.ndarray:
        from activity_browser.bwutils.lcia_overview import normalize_column

        scores = np.asarray(self.lca_scores, dtype=float)
        if scores.size == 0:
            return scores
        out = np.empty_like(scores)
        for col in range(scores.shape[1]):
            out[:, col] = normalize_column(scores[:, col], relative=True) / 100.0
        return out

    def singular_lca(self, demand: dict, method, scenario_index: int):
        """Singular LCA whose technosphere contains only this scenario column.

        Cached per reference-flow demand, impact category, and scenario.
        """
        import bw2calc as bc

        from activity_browser.bwutils.lca_inputs import prepared_lca_inputs

        scenario_index = int(scenario_index)
        key = (_demand_cache_key(demand), tuple(method), scenario_index)
        cached = self._singular.get(key)
        if cached is not None:
            return cached
        column = subset_scenario_datapackage(
            self.scenario_package,
            [self.scenario_names[scenario_index]],
            self.scenario_names,
        )
        fu, data_objs, _rest = prepared_lca_inputs(demand, method)
        lca = bc.LCA(
            demand=fu,
            data_objs=[*list(data_objs), column],
            use_arrays=True,
        )
        lca.lci()
        lca.lcia()
        self._singular[key] = lca
        return lca
