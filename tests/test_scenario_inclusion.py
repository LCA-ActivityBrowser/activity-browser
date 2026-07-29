"""Pure scenario inclusion algebra (set S)."""

from activity_browser.bwutils.superstructure.inclusion import (
    MODE_ADDITION,
    MODE_PRODUCT,
    all_included,
    check_name,
    derive_file_flags,
    extend_universe,
    product_universe,
    reconcile_included,
    toggle_combination,
    uncheck_name,
)


def test_product_universe_joins_with_pipe():
    axes = [["A", "B"], ["X", "Y"]]
    assert product_universe(axes) == [
        "A | X",
        "A | Y",
        "B | X",
        "B | Y",
    ]


def test_extend_universe_intersection_preserves_first_file_order():
    axes = [["A", "B", "C"], ["C", "A", "B"]]
    assert extend_universe(axes) == ["A", "B", "C"]
    assert extend_universe([["A", "B"], ["A", "C"]]) == ["A"]


def test_uncheck_name_product_removes_slice():
    axes = [["A", "B"], ["X", "Y"]]
    included = all_included(axes, MODE_PRODUCT)
    after = uncheck_name(included, axes, 0, "A", MODE_PRODUCT)
    assert after == ["B | X", "B | Y"]
    assert derive_file_flags(after, axes, MODE_PRODUCT) == [
        [False, True],
        [True, True],
    ]


def test_check_name_product_adds_slice_without_resurrecting_cleared_other():
    axes = [["A", "B"], ["X", "Y"]]
    included = all_included(axes, MODE_PRODUCT)
    included = uncheck_name(included, axes, 0, "A", MODE_PRODUCT)
    included = uncheck_name(included, axes, 1, "X", MODE_PRODUCT)
    # Only B|Y left; A off, X off
    assert included == ["B | Y"]
    included = check_name(included, axes, 0, "A", MODE_PRODUCT)
    assert included == ["A | Y", "B | Y"]
    assert "A | X" not in included


def test_toggle_combination():
    axes = [["A", "B"], ["X", "Y"]]
    included = ["A | X", "A | Y"]
    assert toggle_combination(included, "A | X", axes, MODE_PRODUCT) == ["A | Y"]
    assert toggle_combination(["A | Y"], "B | X", axes, MODE_PRODUCT) == [
        "A | Y",
        "B | X",
    ]


def test_included_stays_in_universe_order_after_mutations():
    axes = [["A", "B", "C"], ["X", "Y"]]
    included = all_included(axes, MODE_PRODUCT)
    included = uncheck_name(included, axes, 0, "B", MODE_PRODUCT)
    included = check_name(included, axes, 0, "B", MODE_PRODUCT)
    assert included == product_universe(axes)


def test_extend_uncheck_syncs_logical_name():
    axes = [["A", "B", "C"], ["A", "B", "C"]]
    included = all_included(axes, MODE_ADDITION)
    after = uncheck_name(included, axes, 0, "A", MODE_ADDITION)
    assert after == ["B", "C"]
    assert derive_file_flags(after, axes, MODE_ADDITION) == [
        [False, True, True],
        [False, True, True],
    ]


def test_extend_check_name_adds_everywhere():
    axes = [["A", "B"], ["A", "B"]]
    included = uncheck_name(
        all_included(axes, MODE_ADDITION), axes, 0, "A", MODE_ADDITION
    )
    after = check_name(included, axes, 1, "A", MODE_ADDITION)
    assert after == ["A", "B"]
    assert derive_file_flags(after, axes, MODE_ADDITION) == [
        [True, True],
        [True, True],
    ]


def test_reconcile_mismatch_resets_to_full():
    saved_axes = [["A", "B"], ["X"]]
    current_axes = [["A", "B"], ["X", "Y"]]
    result = reconcile_included(
        ["A | X"], saved_axes, current_axes, MODE_PRODUCT
    )
    assert result.mismatched is True
    assert result.included == all_included(current_axes, MODE_PRODUCT)


def test_reconcile_compatible_keeps_intersection():
    axes = [["A", "B"], ["X", "Y"]]
    result = reconcile_included(
        ["A | X", "gone"], axes, axes, MODE_PRODUCT
    )
    assert result.mismatched is False
    assert result.included == ["A | X"]
