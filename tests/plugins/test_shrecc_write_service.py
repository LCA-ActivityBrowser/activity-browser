"""SHRECC write service unit tests."""
from ab_shrecc.write_service import (
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
    assert [(t.year, t.database_name, t.will_overwrite) for t in targets] == [
        (2021, "shrecc_a", True),
        (2025, "shrecc_b", False),
    ]
    assert needs_overwrite_confirm(targets)


def test_write_targets_use_override_output_names():
    handle = _FakeHandle()
    targets = write_targets(
        handle,
        ["renamed_2021"],
        output_names={2021: "renamed_2021", 2025: "renamed_2025"},
        summary_rows=[
            {
                "year": 2021,
                "source": "energy_charts",
                "background_db": "bg",
            }
        ],
    )
    assert targets[0].database_name == "renamed_2021"
    assert targets[0].will_overwrite is True
    assert targets[0].source == "energy_charts"
    assert targets[0].background_db == "bg"
    assert targets[1].will_overwrite is False


def test_apply_output_database_names():
    from ab_shrecc.write_service import apply_output_database_names

    handle = _FakeHandle()
    apply_output_database_names(handle, {2021: "new_a", 2025: "new_b"})
    assert handle.database_names == {2021: "new_a", 2025: "new_b"}


def test_run_write_returns_written_names():
    handle = _FakeHandle()
    result = run_write(handle)
    assert result.succeeded
    assert result.written == {2021: "shrecc_a"}
    assert handle.write_calls == 1


def test_run_write_returns_partial_on_failure():
    handle = _FakeHandle(fail_on_year=2025)
    result = run_write(handle)
    assert not result.succeeded
    assert result.written == {2021: "shrecc_a"}
    assert "strict match failed" in (result.error or "")
