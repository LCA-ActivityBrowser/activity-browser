"""Startup helper: pandas 2.3 matches pandas 3 Copy-on-Write and string inference."""
import pandas as pd
import pytest

from activity_browser.bwutils import pandas_semantics as sem


@pytest.mark.filterwarnings("ignore:The 'mode.copy_on_write' option is deprecated")
def test_apply_pandas_3_semantics_on_pandas_2_enables_cow_and_infer_string(monkeypatch):
    monkeypatch.setattr(sem, "pandas_major_version", lambda: 2)
    sem.apply_pandas_3_semantics()
    assert pd.options.mode.copy_on_write is True
    assert pd.options.future.infer_string is True


def test_apply_pandas_3_semantics_on_pandas_3_leaves_infer_string_alone(monkeypatch):
    monkeypatch.setattr(sem, "pandas_major_version", lambda: 3)
    infer_before = pd.options.future.infer_string
    sem.apply_pandas_3_semantics()
    assert pd.options.future.infer_string == infer_before
