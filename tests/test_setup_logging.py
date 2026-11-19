"""setup_logging must tolerate windowed frozen builds where stderr is None."""
import sys

from activity_browser import setup_logging


def test_setup_logging_with_none_stderr(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(
        "platformdirs.user_log_dir",
        lambda **kwargs: str(tmp_path / "logs"),
    )
    setup_logging()  # must not raise TypeError
