"""Machine-readable per-test duration logging for CI and local profiling.

Writes ``test-durations.tsv`` in the pytest rootdir and prints one grep-friendly
line per test after teardown:

    [test-duration] passed total=1.234s setup=0.100s call=1.100s teardown=0.034s path::test

Disable with ``AB_TEST_DURATION_LOG=0``. Set ``AB_TEST_DURATION_LOG=tsv`` to write
the file without console lines (default locally). CI sets ``AB_TEST_DURATION_LOG=1``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_ROWS: dict[str, dict[str, float | str]] = {}
_OUT_PATH: Path | None = None


def _mode() -> str:
    """``0`` off, ``tsv`` file only, ``1`` file + console."""
    raw = os.environ.get("AB_TEST_DURATION_LOG")
    if raw is None:
        return "1" if os.environ.get("CI") else "tsv"
    return raw.strip().lower()


def pytest_configure(config):
    global _OUT_PATH
    if _mode() == "0":
        _OUT_PATH = None
        return
    _OUT_PATH = Path(config.rootpath) / "test-durations.tsv"
    _ROWS.clear()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if _mode() == "0":
        return
    report = outcome.get_result()
    row = _ROWS.setdefault(
        report.nodeid,
        {"setup": 0.0, "call": 0.0, "teardown": 0.0, "outcome": ""},
    )
    row[report.when] = float(report.duration)
    if report.when in {"setup", "call"} and report.outcome != "passed":
        row["outcome"] = report.outcome
    elif report.when == "call":
        row["outcome"] = report.outcome


@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    if _mode() == "0" or report.when != "teardown":
        return
    row = _ROWS.get(report.nodeid)
    if row is None:
        return
    if not row["outcome"]:
        row["outcome"] = report.outcome
    setup = float(row["setup"])
    call = float(row["call"])
    teardown = float(row["teardown"])
    total = setup + call + teardown
    if _mode() == "1":
        # Leading newline: pytest -q progress dots share the current line.
        print(
            f"\n[test-duration] {row['outcome']} total={total:.3f}s "
            f"setup={setup:.3f}s call={call:.3f}s teardown={teardown:.3f}s "
            f"{report.nodeid}",
            flush=True,
        )


def pytest_sessionfinish(session, exitstatus):
    if _OUT_PATH is None or _mode() == "0":
        return
    lines = [
        "nodeid\toutcome\tsetup_s\tcall_s\tteardown_s\ttotal_s\n",
    ]
    for nodeid, row in sorted(
        _ROWS.items(),
        key=lambda item: -(
            float(item[1]["setup"])
            + float(item[1]["call"])
            + float(item[1]["teardown"])
        ),
    ):
        setup = float(row["setup"])
        call = float(row["call"])
        teardown = float(row["teardown"])
        total = setup + call + teardown
        lines.append(
            f"{nodeid}\t{row['outcome']}\t{setup:.6f}\t{call:.6f}\t"
            f"{teardown:.6f}\t{total:.6f}\n"
        )
    _OUT_PATH.write_text("".join(lines), encoding="utf-8")
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(
            f"Wrote per-test durations ({len(_ROWS)} tests) to {_OUT_PATH}"
        )
