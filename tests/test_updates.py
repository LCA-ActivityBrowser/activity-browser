"""Update-check seam: channel-local version discovery (no Qt)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from activity_browser.bwutils.updates import (
    UpdateCheckResult,
    check_for_updates,
    detect_install_channel,
    display_version,
    normalize_base_version,
    should_show_auto_prompt,
)


def test_normalize_strips_stand_alone_tag_suffix():
    assert normalize_base_version("3.0.0b202601011200") == "3.0.0b202601011200"
    assert normalize_base_version("3.0.0b202601011200-stand-alone") == "3.0.0b202601011200"


def test_display_version_adds_suffix_when_frozen():
    with patch("activity_browser.bwutils.updates.sys") as sys_mod:
        sys_mod.frozen = True
        assert display_version("3.0.0b1") == "3.0.0b1-stand-alone"
    with patch("activity_browser.bwutils.updates.sys") as sys_mod:
        sys_mod.frozen = False
        assert display_version("3.0.0b1") == "3.0.0b1"


def test_detect_stand_alone_from_frozen():
    with patch("activity_browser.bwutils.updates.sys") as sys_mod:
        sys_mod.frozen = True
        assert detect_install_channel() == "stand-alone"


def test_detect_conda_then_pip(monkeypatch):
    with patch("activity_browser.bwutils.updates.sys") as sys_mod:
        sys_mod.frozen = False
        monkeypatch.setenv("CONDA_DEFAULT_ENV", "ab")
        assert detect_install_channel() == "conda"
        monkeypatch.delenv("CONDA_DEFAULT_ENV", raising=False)
        assert detect_install_channel() == "pip"


def _ok_response(payload: dict, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    return resp


def test_pip_update_available():
    with patch(
        "requests.get",
        return_value=_ok_response({"info": {"version": "3.0.0b2"}}),
    ):
        result = check_for_updates(current_version="3.0.0b1", channel="pip")
    assert result.update_available is True
    assert result.latest_base == "3.0.0b2"
    assert "pip install" in (result.upgrade_command or "")
    assert result.error is None


def test_pip_up_to_date_and_dev_quiet():
    with patch(
        "requests.get",
        return_value=_ok_response({"info": {"version": "3.0.0b1"}}),
    ):
        same = check_for_updates(current_version="3.0.0b1", channel="pip")
        dev = check_for_updates(current_version="0.0.0", channel="pip")
    assert same.update_available is False
    assert dev.update_available is False


def test_conda_update_available():
    with patch(
        "requests.get",
        return_value=_ok_response({"latest_version": "3.0.0b2"}),
    ):
        result = check_for_updates(current_version="3.0.0b1", channel="conda")
    assert result.update_available is True
    assert result.upgrade_command == (
        "conda update -c conda-forge -c lca -c cmutel lca::activity-browser"
    )


def test_stand_alone_uses_github_tags_not_pypi():
    releases = [
        {"tag_name": "2.11.2", "html_url": "https://example/2.11.2"},
        {
            "tag_name": "3.0.0b202601011200-stand-alone",
            "html_url": "https://example/sa-old",
        },
        {
            "tag_name": "3.0.0b202603011200-stand-alone",
            "html_url": "https://example/sa-new",
        },
    ]
    with patch(
        "requests.get",
        return_value=_ok_response(releases),
    ) as get:
        result = check_for_updates(
            current_version="3.0.0b202601011200",
            channel="stand-alone",
        )
    assert result.update_available is True
    assert result.latest_base == "3.0.0b202603011200"
    assert result.latest_display == "3.0.0b202603011200-stand-alone"
    assert result.release_page_url == "https://example/sa-new"
    assert get.call_args.args[0].startswith("https://api.github.com/")


def test_stand_alone_not_behind_when_only_pypi_would_be_newer():
    """Installed stand-alone matches newest *-stand-alone tag even if AB2 Latest exists."""
    releases = [
        {"tag_name": "2.11.2", "html_url": "https://example/2.11.2"},
        {
            "tag_name": "3.0.0b202601011200-stand-alone",
            "html_url": "https://example/sa",
        },
    ]
    with patch(
        "requests.get",
        return_value=_ok_response(releases),
    ):
        result = check_for_updates(
            current_version="3.0.0b202601011200",
            channel="stand-alone",
        )
    assert result.update_available is False


def test_network_failure_is_soft():
    with patch(
        "requests.get",
        side_effect=OSError("offline"),
    ):
        result = check_for_updates(current_version="3.0.0b1", channel="pip")
    assert result.update_available is False
    assert result.error


def test_should_show_auto_prompt_respects_skipped_base():
    result = UpdateCheckResult(
        channel="pip",
        current_display="3.0.0b1",
        current_base="3.0.0b1",
        latest_display="3.0.0b2",
        latest_base="3.0.0b2",
        update_available=True,
    )
    assert should_show_auto_prompt(result, skipped_version=None, snoozed=False) is True
    assert should_show_auto_prompt(result, skipped_version="3.0.0b2", snoozed=False) is False
    assert should_show_auto_prompt(result, skipped_version="3.0.0b1", snoozed=False) is True
    assert should_show_auto_prompt(result, skipped_version="3.0.0b3", snoozed=False) is False
    assert should_show_auto_prompt(result, skipped_version=None, snoozed=True) is False


def test_should_show_auto_prompt_fails_closed_on_unparseable_skip():
    """Corrupt skipped_version must not re-open the automatic GUI prompt."""
    result = UpdateCheckResult(
        channel="pip",
        current_display="3.0.0b1",
        current_base="3.0.0b1",
        latest_display="3.0.0b2",
        latest_base="3.0.0b2",
        update_available=True,
    )
    assert should_show_auto_prompt(result, skipped_version="not-a-version", snoozed=False) is False


def test_pre_flight_checks_does_not_hit_the_network():
    """Startup version print must not block on update discovery."""
    from activity_browser import __main__ as ab_main

    with (
        patch("requests.get", side_effect=AssertionError("network during pre_flight")) as get,
        patch(
            "activity_browser.bwutils.updates.check_for_updates",
            side_effect=AssertionError("check during pre_flight"),
        ),
        patch.object(ab_main.metadata, "version", return_value="3.0.0b1"),
    ):
        ab_main.pre_flight_checks()
    get.assert_not_called()
