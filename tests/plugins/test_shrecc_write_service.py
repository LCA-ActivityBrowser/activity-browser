"""SHRECC write service unit tests."""


from ab_shrecc.write_service import (
    WriteTarget,
    needs_overwrite_confirm,
    run_write,
    write_targets,
)


class _FakeHandle:
    years = [2021, 2025]
    database_names = {2021: "shrecc_a", 2025: "shrecc_b"}
    written_database_names = {}

    def __init__(self, *, fail_on_year=None):
        self._fail_on_year = fail_on_year
        self.write_calls = 0

    def write(self):
        self.write_calls += 1
        self.written_database_names = {2021: "shrecc_a"}
        if self._fail_on_year == 2025:
            raise ValueError("strict match failed for 2025")


def test_write_targets_marks_existing_databases():
    handle = _FakeHandle()
    targets = write_targets(handle, ["shrecc_a", "other"])
    assert targets == [
        WriteTarget(year=2021, database_name="shrecc_a", will_overwrite=True),
        WriteTarget(year=2025, database_name="shrecc_b", will_overwrite=False),
    ]
    assert needs_overwrite_confirm(targets)


def test_run_write_calls_after_database_write_for_each_name():
    handle = _FakeHandle()
    refreshed: list[str] = []

    result = run_write(handle, refreshed.append)

    assert result.succeeded
    assert result.written == {2021: "shrecc_a"}
    assert refreshed == ["shrecc_a"]
    assert handle.write_calls == 1


def test_run_write_returns_partial_on_failure():
    handle = _FakeHandle(fail_on_year=2025)
    refreshed: list[str] = []

    result = run_write(handle, refreshed.append)

    assert not result.succeeded
    assert result.written == {2021: "shrecc_a"}
    assert "strict match failed" in (result.error or "")
    assert refreshed == ["shrecc_a"]
