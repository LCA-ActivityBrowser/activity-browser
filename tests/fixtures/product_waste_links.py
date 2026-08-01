"""Shared expectations for product/waste drop-link LCA cases."""

from __future__ import annotations

# Own CO2 + linked P(10)/W(5) contribution
EXPECTED_SCORES = {
    "A": 6.0,    # production; add waste treatment W
    "Aw": -4.0,  # production; substitute waste treatment W
    "B": 7.0,    # waste treatment; add waste treatment W
    "Bw": -3.0,  # waste treatment; substitute waste treatment W
    "C": 11.0,   # production; consume product p
    "Cw": -9.0,  # production; substitute production of p
    "D": 12.0,   # waste treatment; consume product p
    "Dw": -8.0,  # waste treatment; substitute production of p
}

# (host_code, dragged_code, drop_on_output)
# drop_on_output=True means Output table; False means Input table
LINK_SPECS = (
    ("A", "W", True),    # add waste treatment
    ("Aw", "W", False),  # substitute waste treatment
    ("B", "W", True),
    ("Bw", "W", False),
    ("C", "P", False),   # consume product
    ("Cw", "P", True),   # substitute production
    ("D", "P", False),
    ("Dw", "P", True),
)

CO2_OWN = {
    "P": 10.0,
    "W": 5.0,
    "A": 1.0,
    "Aw": 1.0,
    "B": 2.0,
    "Bw": 2.0,
    "C": 1.0,
    "Cw": 1.0,
    "D": 2.0,
    "Dw": 2.0,
}

# Hosts that are waste treatments (functional input / negative production)
WASTE_HOSTS = frozenset({"W", "B", "Bw", "D", "Dw"})
