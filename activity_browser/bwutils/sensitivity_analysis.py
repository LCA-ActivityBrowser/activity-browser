# -*- coding: utf-8 -*-

# =============================================================================
# Global Sensitivity Analysis (GSA) functions and class for the Delta
# Moment-Independent measure based on Monte Carlo simulation LCA results.
# =============================================================================
import os
import traceback
from time import time
from loguru import logger

import bw2calc as bc
import bw2data as bd
import bw_functional as bf
import numpy as np
import pandas as pd
from bw_graph_tools.graph_traversal import NewNodeEachVisitGraphTraversal
from SALib.analyze import delta

from .montecarlo import MonteCarloLCA, perform_MonteCarlo_LCA

# SALib>=1.5 can call `numpy.trapezoid`, which is only available in NumPy 2.x.
if not hasattr(np, "trapezoid"):
    np.trapezoid = np.trapz

# ------------------------------
# Resolution layer
# ------------------------------
def _rev_get(rev_mapping, idx):
    if rev_mapping is None:
        return None
    if isinstance(rev_mapping, dict):
        value = rev_mapping.get(idx)
    else:
        try:
            value = rev_mapping[idx]
        except (KeyError, IndexError, TypeError):
            value = None
    if value in (None, -1):
        return None
    return value


def _node_from_rev_mapping(mapped):
    if isinstance(mapped, tuple) and len(mapped) >= 2:
        return bd.get_activity(mapped)
    return bd.get_node(id=mapped)


def _process_from_node(node):
    if isinstance(node, bf.Product):
        return bd.get_activity(node["processor"])
    waste_cls = getattr(bf, "Waste", None)
    if waste_cls is not None and isinstance(node, waste_cls):
        return bd.get_activity(node["processor"])
    return node


def _matrix_index_to_process(lca, idx):
    """Resolve matrix index to process for sqlite and functional_sqlite."""
    for rev in (getattr(lca, "product_dict_rev", None), lca.activity_dict_rev):
        mapped = _rev_get(rev, idx)
        if mapped is None:
            continue
        return _process_from_node(_node_from_rev_mapping(mapped))
    raise KeyError(f"Matrix index {idx} not found in reverse mappings")


def _process_from_exchange_io(io_value):
    node = bd.get_activity(io_value)
    return _process_from_node(node)


# ------------------------------
# Extraction layer
# ------------------------------
def get_lca(fu, method):
    """Calculate deterministic LCA and add reverse dictionaries."""
    lca = bc.LCA(fu, method=method)
    lca.lci()
    lca.lcia()
    logger.info(f"Non-stochastic LCA score: {lca.score}")
    lca.activity_dict_rev, lca.product_dict_rev, lca.biosphere_dict_rev = lca.reverse_dict()
    return lca


def filter_technosphere_exchanges(lca, cutoff=0.05, max_calc=1000):
    start = time()
    res = NewNodeEachVisitGraphTraversal.calculate(
        lca,
        cutoff=cutoff,
        max_calc=int(max_calc),
    )
    indices = [
        (edge.producer_index, edge.consumer_index)
        for edge in res["edges"]
        if edge.consumer_index != -1
    ]
    logger.info(
        "TECHNOSPHERE {} filtering resulted in {} of {} exchanges and took {} iterations in {} seconds.".format(
            lca.technosphere_matrix.shape,
            len(indices),
            lca.technosphere_matrix.getnnz(),
            res["calculation_count"],
            np.round(time() - start, 2),
        )
    )
    return indices


def filter_biosphere_exchanges(lca, cutoff=0.005):
    start = time()
    inv = lca.characterized_inventory
    finv = inv.multiply(abs(inv) > abs(lca.score / (1 / cutoff)))
    indices = list(zip(*finv.nonzero()))
    explained_fraction = finv.sum() / lca.score
    logger.info(
        "BIOSPHERE {} filtering resulted in {} of {} exchanges ({}% of total impact) and took {} seconds.".format(
            inv.shape,
            finv.nnz,
            inv.nnz,
            np.round(explained_fraction * 100, 2),
            np.round(time() - start, 2),
        )
    )
    return indices


def _match_exchange(from_process, to_process, exc, biosphere=False):
    if biosphere:
        if exc.get("type") != "biosphere":
            return False
        try:
            emitter = bd.get_activity(exc.input)
            consumer = _process_from_exchange_io(exc.output)
        except Exception:
            return False
        return emitter.id == from_process.id and consumer.id == to_process.id

    if exc.get("type") != "technosphere":
        return False
    try:
        supplier = _process_from_exchange_io(exc.input)
        consumer = _process_from_exchange_io(exc.output)
    except Exception:
        return False
    return supplier.id == from_process.id and consumer.id == to_process.id


def get_exchanges(lca, indices, biosphere=False, only_uncertain=True):
    """Resolve matrix indices to exchange objects."""
    exchanges = []
    matched_indices = []

    for idx in indices:
        if biosphere:
            from_process = bd.get_activity(lca.biosphere_dict_rev[idx[0]])
            to_process = _matrix_index_to_process(lca, idx[1])
        else:
            from_process = _matrix_index_to_process(lca, idx[0])
            to_process = _matrix_index_to_process(lca, idx[1])

        matches = []
        for exc in to_process.exchanges():
            if _match_exchange(from_process, to_process, exc, biosphere=biosphere):
                matches.append(exc)

        if not matches:
            raise ValueError(
                "Could not resolve exchange for indices {} (from id={}, to id={}).".format(
                    idx,
                    from_process.id,
                    to_process.id,
                )
            )

        exchanges.extend(matches)
        matched_indices.extend([idx] * len(matches))

    if only_uncertain:
        exchanges, matched_indices = drop_no_uncertainty_exchanges(exchanges, matched_indices)

    return exchanges, matched_indices


def drop_no_uncertainty_exchanges(excs, indices):
    excs_filtered = []
    indices_filtered = []
    for exc, idx in zip(excs, indices):
        if exc.get("uncertainty type") and exc.get("uncertainty type") >= 1:
            excs_filtered.append(exc)
            indices_filtered.append(idx)

    logger.info(
        "Dropping {} exchanges of {} with no uncertainty. {} remaining.".format(
            len(excs) - len(excs_filtered),
            len(excs),
            len(excs_filtered),
        )
    )
    return excs_filtered, indices_filtered


def get_exchanges_dataframe(exchanges, indices, biosphere=False):
    records = []
    for exc, idx in zip(exchanges, indices):
        raw_input = bd.get_activity(exc.get("input"))
        raw_output = bd.get_activity(exc.get("output"))
        to_process = _process_from_node(raw_output)

        if biosphere:
            from_obj = raw_input
            gsa_name = "B: {} // {} ({}) [{}]".format(
                from_obj.get("name", ""),
                to_process.get("name", ""),
                to_process.get("reference product", ""),
                to_process.get("location", ""),
            )
        else:
            from_obj = _process_from_node(raw_input)
            gsa_name = "T: {} FROM {} [{}] TO {} ({}) [{}]".format(
                from_obj.get("reference product", ""),
                from_obj.get("name", ""),
                from_obj.get("location", ""),
                to_process.get("name", ""),
                to_process.get("reference product", ""),
                to_process.get("location", ""),
            )

        rec = dict(exc)
        rec.update(
            {
                "index": idx,
                "from name": from_obj.get("name", np.nan),
                "from location": from_obj.get("location", np.nan),
                "to name": to_process.get("name", np.nan),
                "to location": to_process.get("location", np.nan),
                "GSA name": gsa_name,
            }
        )
        records.append(rec)

    return pd.DataFrame.from_records(records)


def get_CF_dataframe(lca, only_uncertain_CFs=True):
    data = {}
    for params_index, row in enumerate(lca.cf_params):
        if only_uncertain_CFs and row["uncertainty_type"] <= 1:
            continue
        cf_index = row["row"]
        bio_act = bd.get_activity(lca.biosphere_dict_rev[cf_index])

        data[params_index] = bio_act.as_dict()
        for name in row.dtype.names:
            data[params_index][name] = row[name]
        data[params_index]["index"] = cf_index
        data[params_index]["GSA name"] = "CF: " + bio_act["name"] + str(bio_act["categories"])

    logger.info(
        "CHARACTERIZATION FACTORS filtering resulted in including {} of {} characteriation factors.".format(
            len(data),
            len(lca.cf_params),
        )
    )

    df = pd.DataFrame(data).T
    df.rename(columns={"uncertainty_type": "uncertainty type"}, inplace=True)
    return df


def get_parameters_DF(mc):
    if bool(mc.parameter_data):
        dfp = pd.DataFrame(mc.parameter_data).T
        dfp["GSA name"] = "P: " + dfp["name"]
        logger.info(f"PARAMETERS: {len(dfp)}")
        return dfp

    logger.info("PARAMETERS: None included.")
    return pd.DataFrame()


def get_exchange_values(matrix, indices):
    return [matrix[idx] for idx in indices]


def get_X(matrix_list, indices):
    X = np.zeros((len(matrix_list), len(indices)))
    for row, matrix in enumerate(matrix_list):
        X[row, :] = get_exchange_values(matrix, indices)
    return X


def get_X_CF(mc, dfcf, method):
    cf_data = np.array(mc.CF_dict[method])
    params_indices = dfcf.index.values
    return cf_data[:, params_indices]


def get_X_P(dfp):
    lists = [values for values in dfp["values"]]
    return list(zip(*lists))


def get_problem(X, names):
    return {
        "num_vars": X.shape[1],
        "names": names,
        "bounds": list(zip(*(np.amin(X, axis=0), np.amax(X, axis=0)))),
    }


# ------------------------------
# Analysis layer / public API
# ------------------------------
class GlobalSensitivityAnalysis(object):
    """Global Sensitivity Analysis using SALib Delta index."""

    def __init__(self, mc):
        self.update_mc(mc)
        self.act_number = int()
        self.method_number = int()
        self.cutoff_technosphere = float()
        self.cutoff_biosphere = float()

    def update_mc(self, mc):
        if not isinstance(mc, MonteCarloLCA):
            raise AssertionError(
                "mc should be an instance of MonteCarloLCA, but instead it is a {}.".format(
                    type(mc)
                )
            )
        self.mc = mc

    def _initialize_case(self, act_number, method_number, cutoff_technosphere, cutoff_biosphere):
        self.act_number = act_number
        self.method_number = method_number
        self.cutoff_technosphere = cutoff_technosphere
        self.cutoff_biosphere = cutoff_biosphere

        self.fu = self.mc.cs["inv"][act_number]
        self.activity = bd.get_activity(self.mc.rev_activity_index[act_number])
        self.method = self.mc.cs["ia"][method_number]

    def _collect_metadata_frames(self):
        dfs = []

        if self.mc.include_technosphere:
            self.t_indices = filter_technosphere_exchanges(
                self.lca,
                cutoff=self.cutoff_technosphere,
                max_calc=1e4,
            )
            self.t_exchanges, self.t_indices = get_exchanges(self.lca, self.t_indices)
            self.dft = get_exchanges_dataframe(self.t_exchanges, self.t_indices)
            if not self.dft.empty:
                dfs.append(self.dft)

        if self.mc.include_biosphere:
            self.b_indices = filter_biosphere_exchanges(
                self.lca,
                cutoff=self.cutoff_biosphere,
            )
            self.b_exchanges, self.b_indices = get_exchanges(
                self.lca,
                self.b_indices,
                biosphere=True,
            )
            self.dfb = get_exchanges_dataframe(
                self.b_exchanges,
                self.b_indices,
                biosphere=True,
            )
            if not self.dfb.empty:
                dfs.append(self.dfb)

        if self.mc.include_cfs:
            self.dfcf = get_CF_dataframe(self.lca, only_uncertain_CFs=True)
            if not self.dfcf.empty:
                dfs.append(self.dfcf)
        else:
            self.dfcf = pd.DataFrame()

        self.dfp = get_parameters_DF(self.mc)
        if not self.dfp.empty:
            dfs.append(self.dfp)

        self.metadata = pd.concat(dfs, axis=0, ignore_index=True, sort=False)
        self.metadata.set_index("GSA name", inplace=True)

    def _build_inputs(self):
        X_list = []

        if self.mc.include_technosphere and self.t_indices:
            self.Xa = get_X(self.mc.A_matrices, self.t_indices)
            X_list.append(self.Xa)

        if self.mc.include_biosphere and self.b_indices:
            self.Xb = get_X(self.mc.B_matrices, self.b_indices)
            X_list.append(self.Xb)

        if self.mc.include_cfs and not self.dfcf.empty:
            self.Xc = get_X_CF(self.mc, self.dfcf, self.method)
            X_list.append(self.Xc)

        if self.mc.include_parameters and not self.dfp.empty:
            self.Xp = get_X_P(self.dfp)
            X_list.append(self.Xp)

        self.X = np.concatenate(X_list, axis=1)
        self.Y = self.mc.get_results_dataframe(act_key=self.activity.key)[self.method].to_numpy()

    def _apply_log_transform(self):
        if np.all(self.Y > 0):
            self.Y = np.log(np.abs(self.Y))
            logger.info("All positive LCA scores. Log-transformation performed.")
        elif np.all(self.Y < 0):
            self.Y = -np.log(np.abs(self.Y))
            logger.info("All negative LCA scores. Log-transformation performed.")
        else:
            logger.warning("Log-transformation cannot be applied as LCA scores overlap zero.")

    def perform_GSA(
        self,
        act_number=0,
        method_number=0,
        cutoff_technosphere=0.01,
        cutoff_biosphere=0.01,
    ):
        """Perform GSA for selected functional unit and impact method."""
        start = time()

        try:
            self._initialize_case(
                act_number,
                method_number,
                cutoff_technosphere,
                cutoff_biosphere,
            )
        except Exception:
            traceback.print_exc()
            logger.error("Initializing the GSA failed.")
            return None

        logger.info(
            f"-- GSA --\n Project: {bd.projects.current} CS: {self.mc.cs_name} "
            f"Activity: {self.activity} Method: {self.method}",
        )

        self.lca = get_lca(self.fu, self.method)
        self._collect_metadata_frames()
        self._build_inputs()
        self._apply_log_transform()

        self.names = self.metadata.index
        self.problem = get_problem(self.X, self.names)

        time_delta = time()
        self.Si = delta.analyze(self.problem, self.X, self.Y, print_to_console=False)
        logger.info("Delta analysis took {} seconds".format(np.round(time() - time_delta, 2)))

        self.dfgsa = pd.DataFrame(self.Si, index=self.names).sort_values(by="delta", ascending=False)
        self.dfgsa.index.names = ["GSA name"]

        self.df_final = self.dfgsa.join(self.metadata, on="GSA name")
        self.df_final.reset_index(inplace=True)
        if "pedigree" in self.df_final.columns:
            self.df_final["pedigree"] = self.df_final["pedigree"].astype(str)

        logger.info("GSA took {} seconds".format(np.round(time() - start, 2)))

    def get_save_name(self):
        save_name = (
            self.mc.cs_name
            + "_"
            + str(self.mc.iterations)
            + "_"
            + self.activity["name"]
            + "_"
            + str(self.method)
            + ".xlsx"
        )
        return save_name.replace(",", "").replace("'", "").replace("/", "")

    def export_GSA_output(self):
        from ..settings import ab_settings

        save_name = "gsa_output_" + self.get_save_name()
        self.df_final.to_excel(os.path.join(ab_settings.data_dir, save_name))

    def export_GSA_input(self):
        from ..settings import ab_settings

        X_with_index = pd.DataFrame(self.X.T, index=self.metadata.index)
        save_name = "gsa_input_" + self.get_save_name()
        X_with_index.to_excel(os.path.join(ab_settings.data_dir, save_name))


if __name__ == "__main__":
    mc = perform_MonteCarlo_LCA(project="ei34", cs_name="kraft paper", iterations=20)
    g = GlobalSensitivityAnalysis(mc)
    g.perform_GSA(act_number=0, method_number=1, cutoff_technosphere=0.01, cutoff_biosphere=0.01)
