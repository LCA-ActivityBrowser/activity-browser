# -*- coding: utf-8 -*-
"""
Global sensitivity analysis (GSA) for Monte Carlo LCA results.

Uses SALib's delta moment-independent measure on inputs sampled during
:class:`~activity_browser.bwutils.montecarlo.MonteCarloLCA`. Enable the
uncertainty layers you want analysed (technosphere, biosphere, CFs, parameters)
before running MC.

Results
-------

``GlobalSensitivityAnalysis.df_final`` is sorted by ``delta`` (descending) and
shown in the LCA results GSA tab. Column names are defined in ``GSA_COLUMNS``:

| Column | Role |
|--------|------|
| ``index`` | Unique SALib variable id (full exchange path, including ``(database)``) |
| ``Type`` | ``technosphere``, ``biosphere``, ``characterization factor``, ``parameter`` |
| ``Shortname (without databases)`` | Same path without database suffixes (compact display) |
| ``delta``, ``delta_conf`` | SALib sensitivity indices |
| ``uncertainty`` | Distribution type and parameters (``Uniform; Minimum: 0; Maximum: 1``) |

For technosphere exchanges, ``index`` and the shortname differ; for parameters and
most CFs they are usually identical.

Standalone script
-----------------

Edit the constants under ``if __name__ == "__main__"`` and run this file
(``functional_sqlite`` projects need ``bw_functional`` imported, which the block does).
"""
from __future__ import annotations

import traceback
from pathlib import Path
from time import time

import bw2calc as bc
import bw2data as bd
import bw_functional as bf
import numpy as np
import pandas as pd
from bw_graph_tools.graph_traversal import NewNodeEachVisitGraphTraversal
from loguru import logger
from SALib.analyze import delta

from activity_browser.bwutils.filesystem import get_project_ab_path
from activity_browser.bwutils.uncertainty import uncertainty_cell_summary

from .montecarlo import MonteCarloLCA

if not hasattr(np, "trapezoid"):  # SALib>=1.5 on NumPy 1.x
    np.trapezoid = np.trapz

# Column names for metadata (pre-SALib) and for ``df_final`` / UI / Excel export.
GSA_INDEX_COLUMN = "index"
GSA_TYPE_COLUMN = "Type"
GSA_NAME_COLUMN = "Shortname (without databases)"
GSA_RESULT_COLUMNS = ("delta", "delta_conf")

GSA_COLUMNS = (
    GSA_INDEX_COLUMN,
    GSA_TYPE_COLUMN,
    GSA_NAME_COLUMN,
    *GSA_RESULT_COLUMNS,
    "uncertainty",
)
GSA_METADATA_COLUMNS = tuple(c for c in GSA_COLUMNS if c not in GSA_RESULT_COLUMNS)


def _select_gsa_columns(df: pd.DataFrame, *, metadata: bool = False) -> pd.DataFrame:
    """Restrict a frame to metadata or full GSA output columns (preserves column order)."""
    allowed = GSA_METADATA_COLUMNS if metadata else GSA_COLUMNS
    keep = [col for col in allowed if col in df.columns]
    return df.loc[:, keep] if not df.empty else df


def _gsa_record(
    gsa_type: str,
    shortname: str,
    uncertainty_source,
    *,
    index: str | None = None,
) -> dict:
    """One GSA metadata row; ``index`` defaults to ``shortname`` when omitted."""
    full_index = index if index is not None else shortname
    return {
        GSA_INDEX_COLUMN: full_index,
        GSA_TYPE_COLUMN: gsa_type,
        GSA_NAME_COLUMN: shortname,
        "uncertainty": uncertainty_cell_summary(uncertainty_source),
    }


# --- Matrix index → process (functional_sqlite + sqlite) ----------------------


def _rev_get(rev_mapping, idx):
    if rev_mapping is None:
        return None
    try:
        value = rev_mapping.get(idx) if isinstance(rev_mapping, dict) else rev_mapping[idx]
    except (KeyError, IndexError, TypeError):
        return None
    return None if value in (None, -1) else value


def _node_from_rev_mapping(mapped):
    return bd.get_activity(mapped) if isinstance(mapped, tuple) else bd.get_node(id=mapped)


def _process_from_node(node):
    if isinstance(node, bf.Product):
        return bd.get_activity(node["processor"])
    waste_cls = getattr(bf, "Waste", None)
    if waste_cls is not None and isinstance(node, waste_cls):
        return bd.get_activity(node["processor"])
    return node


def _matrix_index_to_process(lca, idx):
    for rev in (getattr(lca, "product_dict_rev", None), lca.activity_dict_rev):
        mapped = _rev_get(rev, idx)
        if mapped is not None:
            return _process_from_node(_node_from_rev_mapping(mapped))
    raise KeyError(f"Matrix index {idx} not found in reverse mappings")


def _process_from_exchange_io(io_value):
    return _process_from_node(bd.get_activity(io_value))


# --- Exchange labels (shortname vs full index) --------------------------------


def _reference_product(node, process) -> str:
    return node.get("reference product") or process.get("reference product") or node.get("name", "")


def _format_process_segment(
    product, process, location=None, *, include_database: bool = True
) -> str:
    loc = f" [{location}]" if location else ""
    database = process.get("database", "")
    db = f" ({database})" if database and include_database else ""
    return f"{product} | {process.get('name', '')}{loc}{db}"


def _format_exchange_names(raw_input, raw_output) -> tuple[str, str]:
    """Return ``(shortname, index)`` for a technosphere or biosphere exchange."""
    from_process = _process_from_node(raw_input)
    to_process = _process_from_node(raw_output)

    if raw_input.get("type") == "emission":
        flow_name = raw_input.get("name", "")
        categories = raw_input.get("categories")
        left_process = (
            ", ".join(categories) if isinstance(categories, (list, tuple)) else str(categories or flow_name)
        )
        database = raw_input.get("database") or ""
        left_full = f"{flow_name} | {left_process} ({database})" if database else f"{flow_name} | {left_process}"
        left_display = f"{flow_name} | {left_process}"
    else:
        location = from_process.get("location") or raw_input.get("location", "")
        product = _reference_product(raw_input, from_process)
        left_display = _format_process_segment(product, from_process, location, include_database=False)
        left_full = _format_process_segment(product, from_process, location, include_database=True)

    right_location = to_process.get("location") or raw_output.get("location", "")
    right_product = _reference_product(raw_output, to_process)
    right_display = _format_process_segment(
        right_product, to_process, right_location, include_database=False
    )
    right_full = _format_process_segment(
        right_product, to_process, right_location, include_database=True
    )
    return f"{left_display} --> {right_display}", f"{left_full} --> {right_full}"


# --- Deterministic LCA + exchange filtering -----------------------------------


def get_lca(fu, method):
    """Run deterministic LCA and attach reverse dicts for exchange resolution."""
    lca = bc.LCA(fu, method=method)
    lca.lci()
    lca.lcia()
    logger.info(f"Non-stochastic LCA score: {lca.score}")
    lca.activity_dict_rev, lca.product_dict_rev, lca.biosphere_dict_rev = lca.reverse_dict()
    return lca


def filter_technosphere_exchanges(lca, cutoff=0.05, max_calc=1000):
    """Return ``(producer, consumer)`` matrix index pairs above the traversal cutoff."""
    start = time()
    res = NewNodeEachVisitGraphTraversal.calculate(lca, cutoff=cutoff, max_calc=int(max_calc))
    indices = [
        (e.producer_index, e.consumer_index) for e in res["edges"] if e.consumer_index != -1
    ]
    logger.info(
        f"TECHNOSPHERE {lca.technosphere_matrix.shape} filtering: "
        f"{len(indices)} / {lca.technosphere_matrix.getnnz()} exchanges, "
        f"{res['calculation_count']} iterations, {np.round(time() - start, 2)} s"
    )
    return indices


def filter_biosphere_exchanges(lca, cutoff=0.005):
    """Return biosphere matrix indices contributing above ``cutoff`` × |LCA score|."""
    start = time()
    inv = lca.characterized_inventory
    finv = inv.multiply(abs(inv) > abs(lca.score / (1 / cutoff)))
    indices = list(zip(*finv.nonzero()))
    logger.info(
        f"BIOSPHERE {inv.shape} filtering: {finv.nnz} / {inv.nnz} exchanges "
        f"({np.round(finv.sum() / lca.score * 100, 2)}% impact), "
        f"{np.round(time() - start, 2)} s"
    )
    return indices


def _match_exchange(from_process, to_process, exc, *, biosphere=False):
    try:
        if biosphere:
            if exc.get("type") != "biosphere":
                return False
            return (
                bd.get_activity(exc.input).id == from_process.id
                and _process_from_exchange_io(exc.output).id == to_process.id
            )
        if exc.get("type") != "technosphere":
            return False
        return (
            _process_from_exchange_io(exc.input).id == from_process.id
            and _process_from_exchange_io(exc.output).id == to_process.id
        )
    except Exception:
        return False


def get_exchanges(lca, indices, biosphere=False, only_uncertain=True):
    """Map matrix indices to uncertain exchange objects."""
    exchanges, matched_indices = [], []

    for idx in indices:
        if biosphere:
            from_process = bd.get_activity(lca.biosphere_dict_rev[idx[0]])
            to_process = _matrix_index_to_process(lca, idx[1])
        else:
            from_process = _matrix_index_to_process(lca, idx[0])
            to_process = _matrix_index_to_process(lca, idx[1])

        matches = [
            exc for exc in to_process.exchanges()
            if _match_exchange(from_process, to_process, exc, biosphere=biosphere)
        ]
        if not matches:
            raise ValueError(
                f"No exchange for indices {idx} (from id={from_process.id}, to id={to_process.id})"
            )
        exchanges.extend(matches)
        matched_indices.extend([idx] * len(matches))

    if only_uncertain:
        n_before = len(exchanges)
        pairs = [
            (exc, idx)
            for exc, idx in zip(exchanges, matched_indices)
            if exc.get("uncertainty type", 0) >= 1
        ]
        exchanges, matched_indices = map(list, zip(*pairs)) if pairs else ([], [])
        logger.info(f"Uncertain exchanges kept: {len(exchanges)} / {n_before}")

    return exchanges, matched_indices


def get_exchanges_dataframe(exchanges, indices, biosphere=False):
    gsa_type = "biosphere" if biosphere else "technosphere"
    records = []
    for exc, _idx in zip(exchanges, indices):
        raw_input = bd.get_activity(exc.get("input"))
        raw_output = bd.get_activity(exc.get("output"))
        shortname, full_index = _format_exchange_names(raw_input, raw_output)
        records.append(_gsa_record(gsa_type, shortname, exc, index=full_index))
    return _select_gsa_columns(pd.DataFrame.from_records(records), metadata=True)


def _characterization_mm(lca, method):
    if hasattr(lca, "characterization_mm_dict"):
        return lca.characterization_mm_dict[method]
    return lca.characterization_mm


def _method_cf_uncertainty(method) -> dict:
    result = {}
    for flow, cf_data in bd.Method(method).load():
        if not isinstance(cf_data, dict):
            cf_data = {"amount": cf_data}
        ut = int(cf_data.get("uncertainty type", cf_data.get("uncertainty_type", 0)) or 0)
        if isinstance(flow, tuple):
            key = flow
        else:
            act = bd.get_activity(flow)
            key = (act["database"], act["code"])
        result[key] = (cf_data, ut)
    return result


def get_CF_dataframe(lca, method, only_uncertain_CFs=True):
    """Uncertain CF metadata. Returns ``(dataframe, mm_param_indices)``."""
    mm = _characterization_mm(lca, method)
    if mm is None:
        return pd.DataFrame(), np.array([], dtype=int)

    method_cf = _method_cf_uncertainty(method)
    data = {}
    for params_index, unc in enumerate(mm.input_uncertainties()):
        cf_index = int(mm.input_row_col_indices()[params_index]["row"])
        bio_act = bd.get_activity(lca.biosphere_dict_rev[cf_index])
        cf_data, ut = method_cf.get((bio_act["database"], bio_act["code"]), ({}, 0))
        if only_uncertain_CFs and ut <= 1:
            continue

        categories = bio_act.get("categories")
        cat = ", ".join(categories) if isinstance(categories, (list, tuple)) else str(categories or "")
        name = f"{bio_act.get('name', '')} | {cat}" if cat else bio_act.get("name", "")
        data[params_index] = _gsa_record(
            "characterization factor", name, {**cf_data, "uncertainty type": ut}
        )

    logger.info(f"CHARACTERIZATION FACTORS: {len(data)} / {len(mm.input_uncertainties())} included")
    df = pd.DataFrame(data).T
    return _select_gsa_columns(df, metadata=True), df.index.to_numpy()


def get_parameters_dataframe(mc):
    """Parameter metadata for GSA (requires ``mc.parameter_data`` from MC)."""
    if not mc.parameter_data:
        logger.info("PARAMETERS: None included.")
        return pd.DataFrame()

    lookup = {}
    if mc.parameter_mc_manager is not None:
        lookup = {(p.group, p.name): p.data for p in mc.parameter_mc_manager.parameters}

    records = []
    for entry in mc.parameter_data.values():
        data = lookup.get((entry["group"], entry["name"]), entry)
        source = {
            **data,
            "uncertainty type": data.get("uncertainty type", data.get("uncertainty_type")),
        }
        label = f"{entry['name']} [{entry['group']}]"
        records.append(_gsa_record("parameter", label, source))

    logger.info(f"PARAMETERS: {len(records)}")
    return _select_gsa_columns(pd.DataFrame.from_records(records), metadata=True)


def get_X(matrix_list, indices):
    return np.array([[matrix[idx] for idx in indices] for matrix in matrix_list])


def get_X_CF(mc, cf_param_indices, method):
    return np.array(mc.CF_dict[method])[:, cf_param_indices]


def get_X_P(parameter_data: dict, keys: list) -> np.ndarray:
    by_key = {f"{e['name']} [{e['group']}]": e["values"] for e in parameter_data.values()}
    return np.array(list(zip(*[by_key[k] for k in keys])))


def get_problem(X, names):
    return {
        "num_vars": X.shape[1],
        "names": names,
        "bounds": list(zip(np.amin(X, axis=0), np.amax(X, axis=0))),
    }


class GlobalSensitivityAnalysis:
    """SALib delta GSA on a completed :class:`MonteCarloLCA` run.

    Call :meth:`perform_GSA` for one reference flow and impact method. Results
    are in :attr:`df_final`; :attr:`metadata` holds pre-SALib rows indexed by
    ``GSA_INDEX_COLUMN``.
    """

    def __init__(self, mc):
        self.update_mc(mc)

    def update_mc(self, mc):
        """Attach a completed Monte Carlo run (e.g. after a new MC calculation)."""
        if not isinstance(mc, MonteCarloLCA):
            raise TypeError(f"Expected MonteCarloLCA, got {type(mc)}")
        self.mc = mc

    def _initialize_case(self, act_number, method_number, cutoff_technosphere, cutoff_biosphere):
        self.act_number = act_number
        self.method_number = method_number
        self.cutoff_technosphere = cutoff_technosphere
        self.cutoff_biosphere = cutoff_biosphere
        self.fu = self.mc.cs["inv"][act_number]
        self.activity = bd.get_activity(self.mc.rev_activity_index[act_number])
        self.method = self.mc.cs["ia"][method_number]

    def _collect_exchange_metadata(self, *, biosphere=False):
        """Filter, resolve, and tabulate uncertain exchanges for one matrix layer."""
        if biosphere:
            indices = filter_biosphere_exchanges(self.lca, cutoff=self.cutoff_biosphere)
            exchanges, indices = get_exchanges(self.lca, indices, biosphere=True)
            df = get_exchanges_dataframe(exchanges, indices, biosphere=True)
            self.b_indices, self.b_exchanges, self.dfb = indices, exchanges, df
        else:
            indices = filter_technosphere_exchanges(
                self.lca, cutoff=self.cutoff_technosphere, max_calc=int(1e4)
            )
            exchanges, indices = get_exchanges(self.lca, indices)
            df = get_exchanges_dataframe(exchanges, indices)
            self.t_indices, self.t_exchanges, self.dft = indices, exchanges, df
        return df

    def _collect_metadata_frames(self):
        dfs = []

        if self.mc.include_technosphere:
            df = self._collect_exchange_metadata()
            if not df.empty:
                dfs.append(df)

        if self.mc.include_biosphere:
            df = self._collect_exchange_metadata(biosphere=True)
            if not df.empty:
                dfs.append(df)

        if self.mc.include_cfs:
            self.dfcf, self.cf_param_indices = get_CF_dataframe(self.lca, self.method)
            if not self.dfcf.empty:
                dfs.append(self.dfcf)
        else:
            self.dfcf = pd.DataFrame()
            self.cf_param_indices = np.array([], dtype=int)

        self.dfp = get_parameters_dataframe(self.mc)
        if not self.dfp.empty:
            dfs.append(self.dfp)

        if not dfs:
            logger.error("No uncertain exchanges or parameters found for GSA.")
            self.metadata = pd.DataFrame()
            return

        self.metadata = _select_gsa_columns(pd.concat(dfs, ignore_index=True), metadata=True)
        self.metadata.set_index(GSA_INDEX_COLUMN, inplace=True)

    def _build_inputs(self):
        parts = []
        if self.mc.include_technosphere and getattr(self, "t_indices", None):
            parts.append(get_X(self.mc.A_matrices, self.t_indices))
        if self.mc.include_biosphere and getattr(self, "b_indices", None):
            parts.append(get_X(self.mc.B_matrices, self.b_indices))
        if self.mc.include_cfs and not self.dfcf.empty:
            parts.append(get_X_CF(self.mc, self.cf_param_indices, self.method))
        if self.mc.include_parameters and not self.dfp.empty:
            parts.append(get_X_P(self.mc.parameter_data, self.dfp[GSA_INDEX_COLUMN].tolist()))

        self.X = np.concatenate(parts, axis=1)
        self.Y = self.mc.get_results_dataframe(act_key=self.activity.key)[self.method].to_numpy()

    def _validate_mc_inputs(self) -> bool:
        if self.X.shape[0] != len(self.Y):
            logger.error(f"GSA size mismatch: {self.X.shape[0]} MC rows vs {len(self.Y)} scores")
            return False
        if not np.isfinite(self.X).all():
            logger.error("Non-finite values in MC inputs (check uncertainty definitions)")
            return False
        if not np.isfinite(self.Y).all():
            n_bad = int(np.sum(~np.isfinite(self.Y)))
            logger.error(f"MC produced {n_bad}/{len(self.Y)} non-finite scores; GSA cannot run")
            return False
        if self.metadata.empty or self.X.shape[1] != len(self.metadata):
            logger.error(
                f"Metadata/input mismatch: {len(self.metadata)} inputs vs {self.X.shape[1]} X columns"
            )
            return False
        return True

    def _apply_log_transform(self):
        if np.all(self.Y > 0):
            self.Y = np.log(np.abs(self.Y))
            logger.info("All positive LCA scores — log-transform applied")
        elif np.all(self.Y < 0):
            self.Y = -np.log(np.abs(self.Y))
            logger.info("All negative LCA scores — log-transform applied")
        else:
            logger.warning("Log-transform skipped (scores cross zero)")

    def perform_GSA(
        self,
        act_number=0,
        method_number=0,
        cutoff_technosphere=0.01,
        cutoff_biosphere=0.01,
    ):
        """Run delta GSA; sets :attr:`df_final` or returns ``None`` on failure."""
        start = time()
        try:
            self._initialize_case(
                act_number, method_number, cutoff_technosphere, cutoff_biosphere
            )
        except Exception:
            traceback.print_exc()
            logger.error("Initializing the GSA failed.")
            return None

        logger.info(
            f"-- GSA --\n Project: {bd.projects.current} CS: {self.mc.cs_name} "
            f"Activity: {self.activity} Method: {self.method}"
        )

        self.lca = get_lca(self.fu, self.method)
        self._collect_metadata_frames()
        if self.metadata.empty:
            return None

        self._build_inputs()
        self._apply_log_transform()
        if not self._validate_mc_inputs():
            return None

        t0 = time()
        self.Si = delta.analyze(
            get_problem(self.X, self.metadata.index.tolist()), self.X, self.Y, print_to_console=False
        )
        logger.info(f"Delta analysis took {np.round(time() - t0, 2)} s")

        combined = (
            pd.DataFrame(self.Si, index=self.metadata.index)
            .sort_values("delta", ascending=False)
            .join(self.metadata)
            .reset_index()
        )
        self.df_final = _select_gsa_columns(combined)
        logger.info(f"GSA took {np.round(time() - start, 2)} s")

    def get_save_name(self) -> str:
        """Default export basename: ``{cs}_GSA_{product}_{process}_{location}_{db}_{method}``."""
        from .export_names import activity_export_fields, lca_export_basename

        fields = [self.mc.cs_name, "GSA"]
        if self.activity is not None:
            fields.extend(activity_export_fields(self.activity))
        fields.append(self.method)
        return lca_export_basename(*fields)

    def _gsa_input_dataframe(self) -> pd.DataFrame:
        """MC input matrix with rows in the same order as :attr:`df_final`."""
        df_input = pd.DataFrame(self.X.T, index=self.metadata.index)
        if self.df_final is not None and not self.df_final.empty:
            order = self.df_final[GSA_INDEX_COLUMN].tolist()
            df_input = df_input.reindex(order)
        return df_input

    def export_GSA_all(self, filepath: str | Path) -> Path:
        """Write GSA results and MC input matrix to one Excel workbook (two sheets)."""
        path = Path(filepath)
        if path.suffix.lower() != ".xlsx":
            path = path.with_suffix(".xlsx")
        with pd.ExcelWriter(path) as writer:
            self.df_final.to_excel(writer, sheet_name="GSA output", index=False)
            self._gsa_input_dataframe().to_excel(writer, sheet_name="GSA input")
        logger.info(f"GSA data exported to {path}")
        return path

    def export_GSA_all_csv(self, filepath: str | Path) -> tuple[Path, Path]:
        """Write GSA results and MC input matrix to two CSV files (*_output.csv, *_input.csv)."""
        path = Path(filepath)
        base = path.with_suffix("") if path.suffix.lower() == ".csv" else path
        output_path = base.parent / f"{base.name}_output.csv"
        input_path = base.parent / f"{base.name}_input.csv"
        self.df_final.to_csv(output_path, index=False)
        self._gsa_input_dataframe().to_csv(input_path)
        logger.info(f"GSA data exported to {output_path} and {input_path}")
        return output_path, input_path


if __name__ == "__main__":
    import bw_functional  # noqa: F401 — functional_sqlite backend (AB loads this at startup)

    from activity_browser.bwutils.montecarlo import perform_MonteCarlo_LCA

    # --- edit these, then run this file -----------------------------------------
    PROJECT = "testing"
    CS_NAME = "mc_calculation_setup"
    ITERATIONS = 25
    ACT_NUMBER = 0
    METHOD_NUMBER = 0
    CUTOFF_TECHNOSPHERE = 0.01
    CUTOFF_BIOSPHERE = 0.01
    INCLUDE_TECHNOSPHERE = True
    INCLUDE_BIOSPHERE = True
    INCLUDE_CF = True
    INCLUDE_PARAMETERS = False
    EXPORT_EXCEL = False
    # -----------------------------------------------------------------------------

    mc = perform_MonteCarlo_LCA(
        project=PROJECT,
        cs_name=CS_NAME,
        iterations=ITERATIONS,
        technosphere=INCLUDE_TECHNOSPHERE,
        biosphere=INCLUDE_BIOSPHERE,
        cf=INCLUDE_CF,
        parameters=INCLUDE_PARAMETERS,
    )
    gsa = GlobalSensitivityAnalysis(mc)
    gsa.perform_GSA(
        act_number=ACT_NUMBER,
        method_number=METHOD_NUMBER,
        cutoff_technosphere=CUTOFF_TECHNOSPHERE,
        cutoff_biosphere=CUTOFF_BIOSPHERE,
    )
    if gsa.df_final is None or gsa.df_final.empty:
        raise SystemExit("GSA produced no results (check MC uncertainty flags and iterations).")

    if EXPORT_EXCEL:
        gsa.export_GSA_all(get_project_ab_path() / f"{gsa.get_save_name()}.xlsx")

    print(gsa.df_final.to_string())
