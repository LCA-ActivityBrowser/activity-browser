"""SHRECC configure model unit tests."""
from ab_shrecc.configure_model import (
    build_new_database_kwargs,
    config_completion_errors,
    default_config,
    is_config_complete,
    preview_database_names,
)
from ab_shrecc.shrecc_choices import needs_tyndp_fields


def _complete_config(**overrides):
    config = default_config()
    config.update(
        {
            "years": [2021],
            "countries": ["DE"],
            "time_range_start": "2021-01-01 00:00:00",
            "time_range_end": "2021-12-31 23:00:00",
            "bg_db_name": "ecoinvent-3.11-cutoff",
        }
    )
    config.update(overrides)
    return config


def test_default_config_incomplete():
    assert not is_config_complete(default_config())
    assert "Select at least one country." in config_completion_errors(default_config())


def test_complete_historical_config():
    config = _complete_config()
    assert is_config_complete(config)
    assert config_completion_errors(config) == []


def test_tyndp_fields_required_for_prospective_year():
    config = _complete_config(years=[2035])
    assert needs_tyndp_fields(config)
    assert not is_config_complete(config)
    assert any("TYNDP scenario" in err for err in config_completion_errors(config))

    complete = _complete_config(
        years=[2035],
        tyndp_scenario="DE",
        climate_year=2008,
    )
    assert is_config_complete(complete)


def test_preview_database_names_multi_year_suffix():
    assert preview_database_names(base_name="shrecc_mix", years=[2021, 2025]) == {
        2021: "shrecc_mix_2021",
        2025: "shrecc_mix_2025",
    }


def test_build_new_database_kwargs_historical():
    config = _complete_config()
    kwargs = build_new_database_kwargs(
        config, project_name="proj-a", my_db_name="shrecc_electricity"
    )
    assert kwargs["project_name"] == "proj-a"
    assert kwargs["years"] == [2021]
    assert kwargs["countries"] == ["DE"]
    assert kwargs["bg_db_name"] == "ecoinvent-3.11-cutoff"
    assert kwargs["my_db_name"] == "shrecc_electricity"
    assert kwargs["strict"] is True
    assert "scenario" not in kwargs
    assert kwargs["time_range"] == [
        "2021-01-01 00:00:00",
        "2021-12-31 23:00:00",
    ]


def test_build_new_database_kwargs_tyndp():
    config = _complete_config(
        years=[2035],
        tyndp_scenario="NT",
        climate_year=1995,
    )
    kwargs = build_new_database_kwargs(
        config, project_name="proj-a", my_db_name="shrecc_electricity"
    )
    assert kwargs["scenario"] == "NT"
    assert kwargs["climate_year"] == 1995


def test_per_year_background_mapping():
    config = _complete_config(
        years=[2021, 2025],
        map_bg_db_by_year=True,
        bg_db_by_year={"2021": "db-a", "2025": "db-b"},
    )
    kwargs = build_new_database_kwargs(
        config, project_name="proj-a", my_db_name="shrecc_electricity"
    )
    assert kwargs["bg_db_name"] == {2021: "db-a", 2025: "db-b"}


def test_background_database_names():
    from ab_shrecc.configure_model import background_database_names

    config = _complete_config(
        years=[2021, 2025],
        map_bg_db_by_year=True,
        bg_db_by_year={"2021": "db-a", "2025": "db-b"},
    )
    assert background_database_names(config) == ["db-a", "db-b"]


def test_configure_section_summaries_flags_missing_countries():
    from ab_shrecc.configure_model import configure_section_summaries

    summaries = configure_section_summaries(default_config())
    assert summaries["countries"].level == "warn"
    assert summaries["years"].level == "ok"
    assert summaries["databases"].level == "warn"
