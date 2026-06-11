"""Shared basename construction for Activity Browser exports."""


def lca_export_basename(*fields) -> str:
    """Join export name parts into a safe default basename.

    Used across LCA Results tabs with the pattern
    ``{cs}_{tab label}_{functional unit}_{method}_{scenario}`` (omit empty parts).
    """
    name = "_".join(str(x) for x in fields if x is not None and str(x) != "")
    return name.replace(",", "").replace("'", "").replace("/", "")
