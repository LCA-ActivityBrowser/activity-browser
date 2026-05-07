# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
from bw2data.backends import ExchangeDataset
from bw2data.parameters import ActivityParameter, get_new_symbols
from bw2parameters import Interpreter, MissingName, ParameterSet

from activity_browser.mod import bw2data as bd
from activity_browser.bwutils import superstructure
from activity_browser.bwutils.superstructure.utils import SUPERSTRUCTURE
from activity_browser.bwutils.utils import Parameters, StaticParameters


def get_scenario_columns(parameter_scenarios: pd.DataFrame) -> list[str]:
    return [
        c
        for c in parameter_scenarios.columns
        if str(c).strip().lower() not in {"name", "group", "default"}
    ]


def prepare_parameter_matrix(parameter_scenarios: pd.DataFrame) -> tuple[pd.DataFrame, list[str], set[str]]:
    selected_groups = set(parameter_scenarios["Group"].astype(str))
    scenario_columns = get_scenario_columns(parameter_scenarios)
    ps = parameter_scenarios.set_index(["Group", "Name"], inplace=False)

    defaults = [p[:3] for p in Parameters.from_bw_parameters()]
    df = pd.DataFrame(defaults, columns=["Name", "Group", "default"]).set_index(["Group", "Name"])
    for scenario in scenario_columns:
        df[scenario] = df["default"]
    df.update(ps[scenario_columns])
    return df, scenario_columns, selected_groups


def recalculate_project_parameters(
    initial: StaticParameters, parameters: Parameters, active_override_keys: set[tuple[str, str]]
) -> dict:
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


def process_database_parameters(
    initial: StaticParameters,
    parameters: Parameters,
    global_params: dict,
    active_override_keys: set[tuple[str, str]],
) -> dict:
    all_db = {}
    for database in initial.databases:
        db = recalculate_database_parameters(
            initial, parameters, database, global_params, active_override_keys
        )
        all_db[database] = {x: y for x, y in db.items()} if db else {}
    return all_db


def recalculate_activity_parameters(
    initial: StaticParameters,
    parameters: Parameters,
    group: str,
    global_params: dict,
    active_override_keys: set[tuple[str, str]],
) -> dict:
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


def get_exchange_formula_rows_for_selected_groups(
    selected_groups: set[str],
) -> list[tuple[str, int, str, str | None]]:
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
    rows = get_exchange_formula_rows_for_selected_groups(selected_groups)
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
    df, scenario_columns, selected_groups = prepare_parameter_matrix(parameter_scenarios)
    if not selected_groups:
        raise ValueError("No selected groups provided for direct exchange conversion")

    parameters = Parameters.from_bw_parameters()
    initial = StaticParameters()
    baseline = {(p.group, p.name): p.amount for p in parameters.data}
    exchanges_by_scenario = {}

    for scenario in scenario_columns:
        values = dict(df[scenario])
        active_override_keys = {
            (str(k[0]), str(k[1]))
            for k, v in values.items()
            if isinstance(k, tuple) and len(k) == 2 and not np.isnan(v)
        }
        parameters.update(baseline)
        parameters.update(values)

        project_params = recalculate_project_parameters(initial, parameters, active_override_keys)
        database_params = process_database_parameters(
            initial, parameters, project_params, active_override_keys
        )
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
    return flow_df.reindex(columns=ordered_columns)


def main(project: str, path: str, parameter_file: str, flow_file: str) -> None:
    bd.projects.set_current(project)
    base = Path(path)
    parameter_path = base / parameter_file
    flow_path = base / flow_file
    parameter_scenarios = pd.read_excel(parameter_path)
    flow_scenarios = convert_parameter_to_flow_scenarios(parameter_scenarios)
    flow_scenarios.to_excel(flow_path, index=False)


if __name__ == "__main__":
    project = "paris-lca-course-2026"
    path = r"C:\Users\steub\PycharmProjects\paris-mines-lca-school-2026\tutorials\DAY 3 - Premise and Activity Browser Part II\scenarios"
    parameter_file = "_INPUT - parameter scenarios.xlsx"
    flow_file = "_OUTPUT - flow scenarios.xlsx"
    main(project, path, parameter_file, flow_file)
