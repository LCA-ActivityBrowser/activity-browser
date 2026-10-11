"""Align pandas 2.3 runtime with pandas 3 (Copy-on-Write and default strings)."""
import pandas as pd


def pandas_major_version() -> int:
    return int(str(pd.__version__).split(".")[0])


def apply_pandas_3_semantics() -> None:
    """On pandas 2.x, enable pandas 3 copy and string behaviour. No-op on 3+."""
    if pandas_major_version() >= 3:
        return
    pd.options.mode.copy_on_write = True
    pd.options.future.infer_string = True
