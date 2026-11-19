"""Channel-local Activity Browser update checks (no Qt)."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Literal

from packaging.version import InvalidVersion, Version
InstallChannel = Literal["pip", "conda", "stand-alone"]
STAND_ALONE_SUFFIX = "-stand-alone"
GITHUB_RELEASES_PAGE = (
    "https://github.com/LCA-ActivityBrowser/activity-browser/releases"
)
GITHUB_RELEASES_API = (
    "https://api.github.com/repos/LCA-ActivityBrowser/activity-browser/releases"
)
_DOCS = (
    "https://lca-activitybrowser.github.io/activity-browser/"
    "getting-started/installation.html"
)
_FETCH_ERROR = "Could not fetch latest Activity Browser version"

# Registry channels: URL, docs anchor, upgrade command, latest-version extractor.
_REGISTRY = {
    "pip": (
        "https://pypi.org/pypi/activity-browser/json",
        f"{_DOCS}#installing-from-pypi",
        "pip install --upgrade activity-browser",
        lambda data: data["info"]["version"],
    ),
    "conda": (
        "https://api.anaconda.org/package/lca/activity-browser",
        f"{_DOCS}#installing-from-anaconda",
        "conda update -c conda-forge -c lca -c cmutel lca::activity-browser",
        lambda data: data["latest_version"],
    ),
}


@dataclass(frozen=True)
class UpdateCheckResult:
    channel: InstallChannel
    current_display: str
    current_base: str
    latest_display: str | None = None
    latest_base: str | None = None
    update_available: bool = False
    upgrade_command: str | None = None
    release_page_url: str | None = None
    docs_url: str | None = None
    error: str | None = None


def detect_install_channel() -> InstallChannel:
    if getattr(sys, "frozen", False):
        return "stand-alone"
    if os.environ.get("CONDA_DEFAULT_ENV"):
        return "conda"
    return "pip"


def normalize_base_version(version: str) -> str:
    """Comparable AB version (strips a trailing ``-stand-alone`` tag/display suffix)."""
    text = (version or "").strip()
    if text.endswith(STAND_ALONE_SUFFIX):
        return text[: -len(STAND_ALONE_SUFFIX)]
    return text


def display_version(version: str, *, stand_alone: bool | None = None) -> str:
    """AB version for UI/terminal; appends ``-stand-alone`` for frozen installs."""
    base = normalize_base_version(version)
    if stand_alone if stand_alone is not None else getattr(sys, "frozen", False):
        return f"{base}{STAND_ALONE_SUFFIX}"
    return base


def _parse(version: str) -> Version | None:
    try:
        return Version(normalize_base_version(version))
    except InvalidVersion:
        return None


def should_show_auto_prompt(
    result: UpdateCheckResult,
    *,
    skipped_version: str | None,
    snoozed: bool,
) -> bool:
    if snoozed or not result.update_available or not result.latest_base:
        return False
    if not skipped_version:
        return True
    skipped, latest = _parse(skipped_version), _parse(result.latest_base)
    # Fail closed: corrupt skip/latest must not re-open the automatic GUI prompt.
    if skipped is None or latest is None:
        return False
    return latest > skipped

def check_for_updates(
    *,
    current_version: str,
    channel: InstallChannel | None = None,
    timeout: float = 10.0,
) -> UpdateCheckResult:
    channel = channel or detect_install_channel()
    current_base = normalize_base_version(current_version)
    current_display = display_version(
        current_version, stand_alone=(channel == "stand-alone")
    )
    docs = (
        _REGISTRY[channel][1]
        if channel in _REGISTRY
        else f"{_DOCS}#stand-alone-installers"
    )
    base = UpdateCheckResult(
        channel=channel,
        current_display=current_display,
        current_base=current_base,
        docs_url=docs,
    )
    if current_base == "0.0.0":
        return base

    try:
        if channel == "stand-alone":
            return _check_stand_alone(base, timeout)
        return _check_registry(base, timeout)
    except Exception as exc:  # noqa: BLE001 — soft failure for startup/UI
        return UpdateCheckResult(
            channel=channel,
            current_display=current_display,
            current_base=current_base,
            docs_url=docs,
            error=str(exc) or _FETCH_ERROR,
        )


def _check_registry(base: UpdateCheckResult, timeout: float) -> UpdateCheckResult:
    import requests

    url, docs, command, pick_latest = _REGISTRY[base.channel]
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        return UpdateCheckResult(
            channel=base.channel,
            current_display=base.current_display,
            current_base=base.current_base,
            docs_url=docs,
            error=_FETCH_ERROR,
        )
    latest = pick_latest(response.json())
    latest_base = normalize_base_version(latest)
    current_v, latest_v = _parse(base.current_base), _parse(latest_base)
    available = (
        current_v is not None and latest_v is not None and latest_v > current_v
    )
    return UpdateCheckResult(
        channel=base.channel,
        current_display=base.current_display,
        current_base=base.current_base,
        latest_display=latest,
        latest_base=latest_base,
        update_available=available,
        upgrade_command=command if available else None,
        docs_url=docs,
    )


def _check_stand_alone(base: UpdateCheckResult, timeout: float) -> UpdateCheckResult:
    import requests

    docs = f"{_DOCS}#stand-alone-installers"
    response = requests.get(
        GITHUB_RELEASES_API,
        timeout=timeout,
        headers={"Accept": "application/vnd.github+json"},
        params={"per_page": 100},
    )
    if response.status_code != 200:
        return UpdateCheckResult(
            channel="stand-alone",
            current_display=base.current_display,
            current_base=base.current_base,
            docs_url=docs,
            release_page_url=GITHUB_RELEASES_PAGE,
            error=_FETCH_ERROR,
        )

    best_base = best_tag = best_url = None
    best_parsed: Version | None = None
    for release in response.json():
        tag = release.get("tag_name") or ""
        if not tag.endswith(STAND_ALONE_SUFFIX):
            continue
        parsed = _parse(tag)
        if parsed is None:
            continue
        if best_parsed is None or parsed > best_parsed:
            best_parsed = parsed
            best_base = normalize_base_version(tag)
            best_tag = tag
            best_url = release.get("html_url")

    if best_base is None:
        return UpdateCheckResult(
            channel="stand-alone",
            current_display=base.current_display,
            current_base=base.current_base,
            docs_url=docs,
            release_page_url=GITHUB_RELEASES_PAGE,
            error="No stand-alone releases found",
        )

    current_v = _parse(base.current_base)
    available = current_v is not None and best_parsed > current_v
    return UpdateCheckResult(
        channel="stand-alone",
        current_display=base.current_display,
        current_base=base.current_base,
        latest_display=best_tag,
        latest_base=best_base,
        update_available=available,
        release_page_url=(best_url or GITHUB_RELEASES_PAGE)
        if available
        else GITHUB_RELEASES_PAGE,
        docs_url=docs,
    )


def format_terminal_notice(result: UpdateCheckResult) -> str | None:
    """Colored terminal message when an update is available; otherwise ``None``."""
    if not result.update_available:
        return None
    lines = [
        f"There is an update available for the Activity Browser "
        f"({result.current_display} → {result.latest_display}).",
    ]
    if result.upgrade_command:
        lines.append(f"Please update using:\n{result.upgrade_command}")
    elif result.channel == "stand-alone":
        lines.append(
            "Download the newest stand-alone build from:\n"
            f"{result.release_page_url or GITHUB_RELEASES_PAGE}"
        )
    if result.docs_url:
        lines.append(f"\nInstallation instructions:\n{result.docs_url}")
    return "\033[1;31m" + "\n".join(lines) + "\033[0m"
