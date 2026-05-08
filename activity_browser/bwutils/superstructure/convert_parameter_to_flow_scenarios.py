# -*- coding: utf-8 -*-
"""
Convert parameter scenario files into flow scenario files.

Purpose
-------
This module contains the complete, standalone conversion pipeline used by the
Activity Browser to transform a parameter scenario table (Name/Group/default +
scenario columns) into a flow scenario table (SUPERSTRUCTURE columns + scenario
columns).

What it does
------------
- Reads scenario columns from the uploaded parameter scenario data.
- Rebuilds parameter values per scenario (project, database, and activity scopes).
- Evaluates formula-bearing exchanges for the selected output database groups.
- Builds and returns a flow scenario DataFrame with preserved scenario order.

Main entry points
-----------------
- ``convert_parameter_to_flow_scenarios(parameter_scenarios)``
  Convert an in-memory parameter scenario DataFrame.
- ``if __name__ == "__main__":``
  Run a local file-to-file conversion script for manual testing/debugging.

Legacy remark
-------------
The conversion logic is intentionally separated from ``ParameterManager`` so
that:
- conversion behavior is easy to run and test independently;
- MonteCarlo-related logic can remain in ``ParameterManager`` without being
  coupled to file conversion workflows.
- However, ParameterManager and MonteCarloParameterManager should be reworked in the future

"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from bw2data.backends import ExchangeDataset
from bw2data.parameters import ActivityParameter, get_new_symbols
from bw2parameters import Interpreter, MissingName, ParameterSet

from activity_browser.mod import bw2data as bd
from activity_browser.bwutils import superstructure
from activity_browser.bwutils.superstructure.utils import SUPERSTRUCTURE
from activity_browser.bwutils.utils import Parameters, StaticParameters


def scenario_columns(parameter_scenarios: pd.DataFrame) -> list[str]:
    """Return scenario columns in file order, excluding Name/Group/default."""
    return [
        c
        for c in parameter_scenarios.columns
        if str(c).strip().lower() not in {"name", "group", "default"}
    ]


def prepare_parameter_matrix(
    parameter_scenarios: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], set[str]]:
    """Build scenario matrix by overlaying uploaded values on BW parameter defaults."""
    selected_groups = set(parameter_scenarios["Group"].astype(str))
    scenario_cols = scenario_columns(parameter_scenarios)
    ps = parameter_scenarios.set_index(["Group", "Name"], inplace=False)

    defaults = [p[:3] for p in Parameters.from_bw_parameters()]
    df = pd.DataFrame(defaults, columns=["Name", "Group", "default"]).set_index(["Group", "Name"])
    for scenario in scenario_cols:
        df[scenario] = df["default"]
    df.update(ps[scenario_cols])
    return df, ps, scenario_cols, selected_groups


def recalculate_project_parameters(
    initial: StaticParameters, parameters: Parameters, active_override_keys: set[tuple[str, str]]
) -> dict:
    """Recalculate project parameters, keeping explicit scenario overrides fixed.

    Why ``active_override_keys``:
        When a parameter is explicitly provided in the scenario file, we want that
        numeric override to win. We therefore blank out its formula for this
        recalculation pass so ``ParameterSet`` doesn't recompute and overwrite it.
        E.g.: if an exchange has a parameter CO2; if that parameter CO2 is calculated
        from other parameters, CO2 = A*B; then the user can specify either A and or B or directly CO2
    """
    raw = initial.project()
    if not raw:
        return {}
    data = deepcopy(raw)
    new_values = parameters.data_by_group("project")
    for name, amount in new_values.items():
        data[name]["amount"] = amount
        if ("project", str(name)) in active_override_keys:
            data[name]["formula"] = ""
    ParameterSet(data).evaluate_and_set_amount_field()
    return StaticParameters.prune_result_data(data)


def recalculate_database_parameters(
    initial: StaticParameters,
    parameters: Parameters,
    database: str,
    global_params: dict,
    active_override_keys: set[tuple[str, str]],
) -> dict:
    """Recalculate database parameters for one database with override protection.

    ``active_override_keys`` has the same role as in project recalculation: enforce
    scenario-specified values over stored formulas for explicitly overridden params.
    """
    raw = initial.by_database(database)
    if not raw:
        return {}
    data = deepcopy(raw)

    new_values = parameters.data_by_group(database)
    for name, amount in new_values.items():
        data[name]["amount"] = amount
        if (str(database), str(name)) in active_override_keys:
            data[name]["formula"] = ""

    new_symbols = get_new_symbols(data.values(), set(data))
    missing = new_symbols.difference(global_params)
    if missing:
        raise MissingName(
            "The following variables aren't defined:\n{}".format("|".join(missing))
        )

    glo = Parameters.static(global_params, needed=new_symbols) if new_symbols else None
    ParameterSet(data, glo).evaluate_and_set_amount_field()
    return StaticParameters.prune_result_data(data)


def recalculate_activity_parameters(
    initial: StaticParameters,
    parameters: Parameters,
    group: str,
    global_params: dict,
    active_override_keys: set[tuple[str, str]],
) -> dict:
    """Recalculate one activity-parameter group against provided scope.

    ``active_override_keys`` ensures activity-level values supplied by the scenario
    file are not re-derived from formulas in this pass.
    """
    raw = initial.act_by_group(group)
    if not raw:
        return {}
    data = deepcopy(raw)

    new_values = parameters.data_by_group(group)
    for name, amount in new_values.items():
        data[name]["amount"] = amount
        if (str(group), str(name)) in active_override_keys:
            data[name]["formula"] = ""

    new_symbols = get_new_symbols(data.values(), set(data))
    missing = new_symbols.difference(global_params)
    if missing:
        raise MissingName(
            "The following variables aren't defined:\n{}".format("|".join(missing))
        )

    glo = Parameters.static(global_params, needed=new_symbols) if new_symbols else None
    ParameterSet(data, glo).evaluate_and_set_amount_field()
    return StaticParameters.prune_result_data(data)


def exchange_formula_rows_for_selected_groups(
    selected_groups: set[str],
) -> list[tuple[str, int, str, str | None]]:
    """Collect formula-bearing exchanges for selected output databases/groups."""
    activity_group_by_key = {}
    for ap in ActivityParameter.select(
        ActivityParameter.group, ActivityParameter.database, ActivityParameter.code
    ).distinct():
        activity_group_by_key[(str(ap.database), str(ap.code))] = str(ap.group)

    rows = []
    query = ExchangeDataset.select().where(
        ExchangeDataset.output_database << list(selected_groups)
    )
    for exc in query:
        formula = ""
        if isinstance(getattr(exc, "data", None), dict):
            formula = str((exc.data or {}).get("formula") or "").strip()
        if not formula:
            formula = str(getattr(exc, "formula", "") or "").strip()
        if formula:
            activity_group = activity_group_by_key.get(
                (str(exc.output_database), str(exc.output_code))
            )
            rows.append(
                (
                    str(exc.output_database),
                    int(exc.id),
                    formula,
                    activity_group,
                    0 if str(exc.input_database) == str(exc.output_database) else 1,
                )
            )
    rows.sort(key=lambda x: (x[0], x[4], x[2], x[1]))
    return [(g, eid, f, act_group) for g, eid, f, act_group, _prio in rows]


def process_selected_exchange_formulas(
    initial: StaticParameters,
    parameters: Parameters,
    project_params: dict,
    database_params: dict,
    selected_groups: set[str],
    active_override_keys: set[tuple[str, str]],
) -> dict[int, float]:
    """Evaluate selected exchange formulas for one scenario scope."""
    rows = exchange_formula_rows_for_selected_groups(selected_groups)
    if not rows:
        return {}

    complete = {}
    for group, exc_id, formula, activity_group in rows:
        scope = project_params.copy()
        scope.update(database_params.get(group, {}))
        if activity_group:
            activity_params = recalculate_activity_parameters(
                initial, parameters, activity_group, scope, active_override_keys
            )
            scope.update(activity_params)
        interpreter = Interpreter()
        interpreter.symtable.update(scope)
        complete[exc_id] = interpreter(formula)
    return complete


def convert_parameter_to_flow_scenarios(parameter_scenarios: pd.DataFrame) -> pd.DataFrame:
    """Convert parameter scenarios DataFrame into flow scenarios DataFrame."""
    df, ps, scenario_columns, selected_groups = prepare_parameter_matrix(parameter_scenarios)
    if not selected_groups:
        raise ValueError("No selected groups provided for direct exchange conversion")

    parameters = Parameters.from_bw_parameters()
    initial = StaticParameters()
    # Why baseline:
    # Parameter updates are sparse (NaNs are skipped). Resetting to baseline at the
    # start of each scenario prevents value carry-over from previous scenarios.
    baseline = {(p.group, p.name): p.amount for p in parameters.data}
    exchanges_by_scenario = {}

    for scenario in scenario_columns:
        values = dict(df[scenario])
        explicit_values = dict(ps[scenario]) if scenario in ps.columns else {}
        active_override_keys = {
            (str(k[0]), str(k[1]))
            for k, v in explicit_values.items()
            if isinstance(k, tuple) and len(k) == 2 and not np.isnan(v)
        }
        parameters.update(baseline)
        parameters.update(values)

        project_params = recalculate_project_parameters(initial, parameters, active_override_keys)
        database_params = {}
        for database in initial.databases:
            db = recalculate_database_parameters(
                initial,
                parameters,
                database,
                project_params,
                active_override_keys,
            )
            database_params[database] = {x: y for x, y in db.items()} if db else {}
        direct = process_selected_exchange_formulas(
            initial,
            parameters,
            project_params,
            database_params,
            selected_groups,
            active_override_keys,
        )
        if not direct:
            raise ValueError(
                "No direct formula exchanges found for selected groups: "
                + ", ".join(sorted(selected_groups))
            )
        exchanges_by_scenario[scenario] = direct

    flow_df = superstructure.superstructure_from_scenario_exchanges(exchanges_by_scenario)
    ordered_columns = SUPERSTRUCTURE.tolist() + scenario_columns
    flow_df = flow_df.reindex(columns=ordered_columns)
    logger.info(
        "Converted parameter scenarios to flow scenarios: {} scenarios -> {} flows",
        len(scenario_columns),
        len(flow_df),
    )
    return flow_df


if __name__ == "__main__":
    """Example runnable script for local parameter->flow conversion."""
    project = "a brightway 2.5 project"
    path = r"path to scenario file"
    parameter_file = "INPUT - parameter scenarios.xlsx"
    flow_file = "OUTPUT - flow scenarios.xlsx"

    bd.projects.set_current(project)
    base = Path(path)
    parameter_path = base / parameter_file
    flow_path = base / flow_file
    parameter_scenarios = pd.read_excel(parameter_path)
    flow_scenarios = convert_parameter_to_flow_scenarios(parameter_scenarios)
    flow_scenarios.to_excel(flow_path, index=False)
