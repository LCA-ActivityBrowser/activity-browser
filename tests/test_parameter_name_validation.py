"""Invalid parameter names are refused before anything is saved (#1549)."""
import bw2data as bd
import pytest
from bw2data.parameters import DatabaseParameter, ProjectParameter
from bw2data.tests import bw2test
from qtpy import QtWidgets

from activity_browser import app
from activity_browser.bwutils.utils import Parameter

# A space, a leading digit, a Python keyword and two names that the formula
# interpreter reserves for built-ins.
INVALID_NAMES = ["my param", "2nd", "if", "max", "e"]
SCOPES = {
    "project": ("project", ProjectParameter),
    "database": ("db", DatabaseParameter),
}


@pytest.fixture
def dialogs(monkeypatch):
    shown = {"warning": [], "critical": []}
    for kind in shown:
        monkeypatch.setattr(
            QtWidgets.QMessageBox,
            kind,
            staticmethod(lambda *args, _kind=kind, **kwargs: shown[_kind].append(args)),
        )
    return shown


def _new(scope: str, name: str, amount: float = 1.0) -> None:
    group, _ = SCOPES[scope]
    app.actions.ParameterNewFromParameter.run(
        Parameter(name=name, group=group, amount=amount, param_type=scope, data={})
    )


@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("name", INVALID_NAMES)
@bw2test
def test_invalid_name_is_refused_with_a_clear_message(qapp, dialogs, scope, name):
    bd.Database("db").register()
    _, model = SCOPES[scope]

    _new(scope, name)

    assert [p.name for p in model.select()] == []
    assert dialogs["critical"] == []
    assert len(dialogs["warning"]) == 1
    assert f"'{name}'" in dialogs["warning"][0][2]

    # The project's parameters still recalculate: a valid name goes through.
    _new(scope, "valid_name", amount=2.0)
    assert [(p.name, p.amount) for p in model.select()] == [("valid_name", 2.0)]


@pytest.mark.parametrize("name", INVALID_NAMES)
@bw2test
def test_rename_to_invalid_name_is_refused_with_a_clear_message(qapp, dialogs, name):
    _new("project", "a")

    app.actions.ParameterRename.run(("project", "a"), name)

    assert [p.name for p in ProjectParameter.select()] == ["a"]
    assert dialogs["critical"] == []
    assert len(dialogs["warning"]) == 1
    assert f"'{name}'" in dialogs["warning"][0][2]
