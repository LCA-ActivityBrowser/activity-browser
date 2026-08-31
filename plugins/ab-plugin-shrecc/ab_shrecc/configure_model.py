# -*- coding: utf-8 -*-
"""Configure-stage validation and NewDatabase kwargs (no Qt)."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from .shrecc_choices import (
    consumption_profiles,
    inventory_resolutions,
    needs_tyndp_fields,
    source_for_year,
    valid_sources,
    zero_consumption_modes,
)


def default_config() -> dict[str, Any]:
    first_year = 2025
    return {
        "years": [first_year],
        "countries": [],
        "time_mode": "range",
        "time_range_start": f"{first_year}-01-01 00:00:00",
        "time_range_end": f"{first_year}-12-31 23:00:00",
        "hour_range_start": 0,
        "hour_range_end": 23,
        "times_text": "",
        "source": "auto",
        "tyndp_scenario": None,
        "climate_year": None,
        "iam": "remind-eu",
        "map_bg_db_by_year": False,
        "bg_db_name": "",
        "bg_db_by_year": {},
        "inventory_resolution": "annual",
        "strict": True,
        "cutoff": 1e-3,
        "include_cutoff": True,
        "network": True,
        "zero_consumption": zero_consumption_modes()[0],
        "consumption_profile": consumption_profiles()[0],
        "download": True,
        "verbose": False,
        "check": True,
        "include_consumption_mix_volume": True,
        "retain_hourly_results": True,
    }


def normalize_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = default_config()
    if config:
        merged.update(config)
    merged["years"] = sorted({int(year) for year in merged.get("years") or []})
    merged["countries"] = sorted({str(country) for country in merged.get("countries") or []})
    return merged


def preview_database_names(
    *,
    base_name: str,
    years: list[int],
) -> dict[int, str]:
    """Resolve output DB names from a base name and year list."""
    years = [int(year) for year in years]
    base = str(base_name or "").strip()
    if not years:
        return {}
    if len(years) == 1:
        return {years[0]: base}
    if "{year}" in base:
        return {year: base.format(year=year) for year in years}
    return {year: f"{base}_{year}" for year in years}


def config_completion_errors(config: dict[str, Any]) -> list[str]:
    config = normalize_config(config)
    errors: list[str] = []

    if not config["years"]:
        errors.append("Select at least one year.")
    if not config["countries"]:
        errors.append("Select at least one country.")

    time_mode = config.get("time_mode", "range")
    if time_mode == "range":
        if not str(config.get("time_range_start") or "").strip():
            errors.append("Enter a time range start.")
        if not str(config.get("time_range_end") or "").strip():
            errors.append("Enter a time range end.")
    elif time_mode == "hour_range":
        if not str(config.get("time_range_start") or "").strip():
            errors.append("Enter a time range start for hour range mode.")
        if not str(config.get("time_range_end") or "").strip():
            errors.append("Enter a time range end for hour range mode.")
    elif time_mode == "times":
        if not _parse_times_text(config.get("times_text", "")):
            errors.append("Enter at least one explicit timestamp.")
    else:
        errors.append(f"Unknown time mode: {time_mode!r}.")

    source = str(config.get("source", "auto")).lower()
    if source not in valid_sources():
        errors.append("Select a valid source.")

    if needs_tyndp_fields(config):
        if not config.get("tyndp_scenario"):
            errors.append("Select a TYNDP scenario.")
        if config.get("climate_year") is None:
            errors.append("Select a TYNDP climate year.")

    if not str(config.get("iam") or "").strip():
        errors.append("Select an IAM model.")

    if config.get("map_bg_db_by_year"):
        by_year = config.get("bg_db_by_year") or {}
        for year in config["years"]:
            if not str(by_year.get(str(year)) or by_year.get(year) or "").strip():
                errors.append(f"Select a background database for {year}.")
    else:
        if not str(config.get("bg_db_name") or "").strip():
            errors.append("Select a background database.")

    resolution = str(config.get("inventory_resolution") or "")
    if resolution not in inventory_resolutions():
        errors.append("Select an inventory resolution.")

    profile = str(config.get("consumption_profile") or "")
    if profile not in consumption_profiles():
        errors.append("Select a consumption profile.")

    zero_mode = str(config.get("zero_consumption") or "")
    if zero_mode not in zero_consumption_modes():
        errors.append("Select a zero-consumption mode.")

    return errors


def is_config_complete(config: dict[str, Any]) -> bool:
    return not config_completion_errors(config)


SectionLevel = Literal["ok", "warn", "error", "neutral"]


@dataclass(frozen=True)
class SectionSummary:
    summary: str
    status: str
    level: SectionLevel


def configure_section_summaries(config: dict[str, Any]) -> dict[str, SectionSummary]:
    config = normalize_config(config)
    summaries: dict[str, SectionSummary] = {}

    years = config["years"]
    if years:
        summaries["years"] = SectionSummary(
            summary=", ".join(str(year) for year in years),
            status="Complete",
            level="ok",
        )
    else:
        summaries["years"] = SectionSummary(
            summary="No years selected",
            status="Required",
            level="warn",
        )

    countries = config["countries"]
    if countries:
        text = ", ".join(countries)
        if len(text) > 48:
            text = f"{len(countries)} countries"
        summaries["countries"] = SectionSummary(
            summary=text,
            status="Complete",
            level="ok",
        )
    else:
        summaries["countries"] = SectionSummary(
            summary="No countries selected",
            status="Required",
            level="warn",
        )

    time_mode = config.get("time_mode", "range")
    if time_mode == "times":
        times = _parse_times_text(config.get("times_text", ""))
        if times:
            summaries["time"] = SectionSummary(
                summary=f"{len(times)} explicit timestamps",
                status="Complete",
                level="ok",
            )
        else:
            summaries["time"] = SectionSummary(
                summary="Explicit timestamps",
                status="Required",
                level="warn",
            )
    elif time_mode == "hour_range":
        start = str(config.get("time_range_start") or "").strip()
        end = str(config.get("time_range_end") or "").strip()
        hours = f"{config.get('hour_range_start')}-{config.get('hour_range_end')}h"
        if start and end:
            summaries["time"] = SectionSummary(
                summary=f"{start} → {end}, hours {hours}",
                status="Complete",
                level="ok",
            )
        else:
            summaries["time"] = SectionSummary(
                summary=f"Hour range {hours}",
                status="Required",
                level="warn",
            )
    else:
        start = str(config.get("time_range_start") or "").strip()
        end = str(config.get("time_range_end") or "").strip()
        if start and end:
            summaries["time"] = SectionSummary(
                summary=f"{start} → {end}",
                status="Complete",
                level="ok",
            )
        else:
            summaries["time"] = SectionSummary(
                summary="Time range",
                status="Required",
                level="warn",
            )

    source = str(config.get("source", "auto"))
    summaries["source"] = SectionSummary(
        summary=f"Source: {source}",
        status="Complete",
        level="ok",
    )

    if needs_tyndp_fields(config):
        scenario = config.get("tyndp_scenario")
        climate = config.get("climate_year")
        iam = config.get("iam")
        if scenario and climate is not None:
            summaries["tyndp"] = SectionSummary(
                summary=f"{scenario}, climate {climate}, {iam}",
                status="Complete",
                level="ok",
            )
        else:
            summaries["tyndp"] = SectionSummary(
                summary="TYNDP scenario and climate year",
                status="Required",
                level="warn",
            )
    else:
        summaries["tyndp"] = SectionSummary(
            summary="Not required for selected years",
            status="N/A",
            level="neutral",
        )

    if config.get("map_bg_db_by_year"):
        by_year = config.get("bg_db_by_year") or {}
        missing = [
            year
            for year in years
            if not str(by_year.get(str(year)) or by_year.get(year) or "").strip()
        ]
        if missing:
            summaries["databases"] = SectionSummary(
                summary="Per-year background mapping",
                status="Required",
                level="warn",
            )
        else:
            summaries["databases"] = SectionSummary(
                summary="Mapped by year",
                status="Complete",
                level="ok",
            )
    else:
        bg_name = str(config.get("bg_db_name") or "").strip()
        if bg_name:
            summaries["databases"] = SectionSummary(
                summary=f"Background {bg_name}",
                status="Complete",
                level="ok",
            )
        else:
            summaries["databases"] = SectionSummary(
                summary="Background database",
                status="Required",
                level="warn",
            )

    non_defaults = []
    if not config.get("strict", True):
        non_defaults.append("non-strict")
    if not config.get("download", True):
        non_defaults.append("no download")
    if config.get("verbose"):
        non_defaults.append("verbose")
    if non_defaults:
        summary = "Custom: " + ", ".join(non_defaults)
    else:
        summary = "Defaults (strict on)"
    summaries["advanced"] = SectionSummary(
        summary=summary,
        status="Optional",
        level="neutral",
    )

    return summaries


def build_new_database_kwargs(
    config: dict[str, Any],
    *,
    project_name: str,
    my_db_name: str | None = None,
) -> dict[str, Any]:
    if not is_config_complete(config):
        raise ValueError("Configure form is incomplete.")

    config = normalize_config(config)
    output_name = str(my_db_name or config.get("my_db_name") or "").strip()
    if not output_name:
        raise ValueError("Output database base name is required.")

    kwargs: dict[str, Any] = {
        "years": config["years"],
        "countries": config["countries"],
        "project_name": project_name,
        "source": config["source"],
        "iam": config["iam"],
        "inventory_resolution": config["inventory_resolution"],
        "strict": bool(config["strict"]),
        "cutoff": float(config["cutoff"]),
        "include_cutoff": bool(config["include_cutoff"]),
        "network": bool(config["network"]),
        "zero_consumption": config["zero_consumption"],
        "consumption_profile": config["consumption_profile"],
        "download": bool(config["download"]),
        "verbose": bool(config["verbose"]),
        "check": bool(config["check"]),
        "include_consumption_mix_volume": bool(config["include_consumption_mix_volume"]),
        "retain_hourly_results": bool(config["retain_hourly_results"]),
        "my_db_name": output_name,
    }

    if config.get("map_bg_db_by_year"):
        by_year = config.get("bg_db_by_year") or {}
        kwargs["bg_db_name"] = {
            year: str(by_year.get(str(year)) or by_year.get(year))
            for year in config["years"]
        }
    else:
        kwargs["bg_db_name"] = config["bg_db_name"]

    if needs_tyndp_fields(config):
        kwargs["scenario"] = config["tyndp_scenario"]
        kwargs["climate_year"] = int(config["climate_year"])

    time_mode = config.get("time_mode", "range")
    if time_mode == "range":
        kwargs["time_range"] = [
            config["time_range_start"],
            config["time_range_end"],
        ]
    elif time_mode == "hour_range":
        kwargs["time_range"] = [
            config["time_range_start"],
            config["time_range_end"],
        ]
        kwargs["hour_range"] = [
            int(config["hour_range_start"]),
            int(config["hour_range_end"]),
        ]
    elif time_mode == "times":
        kwargs["times"] = _parse_times_text(config.get("times_text", ""))

    return kwargs


def resolved_sources(config: dict[str, Any]) -> dict[int, str]:
    config = normalize_config(config)
    return {
        year: source_for_year(year, str(config.get("source", "auto")))
        for year in config["years"]
    }


def _parse_times_text(text: str) -> list[str]:
    times = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return times


def merge_config_update(
    current: dict[str, Any] | None,
    update: dict[str, Any],
) -> dict[str, Any]:
    merged = normalize_config(current)
    merged.update(deepcopy(update))
    return normalize_config(merged)


def background_database_names(config: dict[str, Any]) -> list[str]:
    config = normalize_config(config)
    if config.get("map_bg_db_by_year"):
        by_year = config.get("bg_db_by_year") or {}
        names = {
            str(by_year.get(str(year)) or by_year.get(year) or "").strip()
            for year in config["years"]
        }
        return sorted(name for name in names if name)
    name = str(config.get("bg_db_name") or "").strip()
    return [name] if name else []


def background_database_names_from_kwargs(kwargs: dict[str, Any]) -> list[str]:
    bg_db = kwargs.get("bg_db_name")
    if isinstance(bg_db, dict):
        return sorted({str(name).strip() for name in bg_db.values() if str(name).strip()})
    name = str(bg_db or "").strip()
    return [name] if name else []


def config_fingerprint(config: dict[str, Any]) -> str:
    """Fingerprint Create-time config only (excludes Write-options naming)."""
    import json

    data = normalize_config(config)
    data.pop("my_db_name", None)
    return json.dumps(data, sort_keys=True, default=str)
