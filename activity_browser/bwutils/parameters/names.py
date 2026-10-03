"""Parameter name rules, as bw2parameters applies them on recalculation."""

from bw2parameters.interpreter import Interpreter
from bw2parameters.utils import isidentifier


def parameter_name_error(name: str) -> str | None:
    """Return why ``name`` cannot be used as a parameter name, or ``None`` if it can.

    bw2parameters only checks names when it recalculates, after a parameter has
    been saved, so an invalid name has to be caught before saving.
    """
    if not isidentifier(name):
        return (
            f"'{name}' is not a valid parameter name. Use only letters, digits and "
            "underscores, do not start with a digit, and do not use a Python "
            "keyword such as 'if' or 'in'."
        )
    if name in Interpreter().BUILTIN_SYMBOLS:
        return (
            f"'{name}' is already the name of a function or constant in formulas "
            "(for example 'max', 'pi' or 'e'). Please choose another name."
        )
    return None
