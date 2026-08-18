"""Selection history for Tree/Sankey RF–IC–scenario combos (no Qt)."""

from activity_browser.ui.selection_history import IndexSelectionHistory


def test_push_back_returns_previous_selection():
    hist = IndexSelectionHistory()
    hist.push((0, 0, None))
    hist.push((1, 0, None))
    assert hist.can_back()
    assert hist.back() == (0, 0, None)
    assert not hist.can_back()
    assert hist.can_forward()


def test_back_does_not_push_when_suppressed():
    hist = IndexSelectionHistory()
    hist.push((0, 0, None))
    hist.push((1, 0, None))
    hist.suppress_push()
    hist.push((0, 0, None))
    hist.resume_push()
    assert hist.back() == (0, 0, None)
    assert hist.forward() == (1, 0, None)


def test_duplicate_current_selection_is_not_pushed():
    hist = IndexSelectionHistory()
    hist.push((0, 1, 0))
    hist.push((0, 1, 0))
    assert not hist.can_back()


def test_forward_cleared_after_new_push():
    hist = IndexSelectionHistory()
    hist.push((0, 0, None))
    hist.push((1, 0, None))
    hist.back()
    hist.push((2, 0, None))
    assert not hist.can_forward()
    assert hist.back() == (0, 0, None)


def test_seed_then_push_allows_back_to_initial():
    hist = IndexSelectionHistory()
    hist.seed((0, 0, None))
    assert not hist.can_back()
    hist.push((1, 0, None))
    assert hist.can_back()
    assert hist.back() == (0, 0, None)
    assert hist.can_forward()


def test_seed_replaces_existing_stack():
    hist = IndexSelectionHistory()
    hist.push((0, 0, None))
    hist.push((1, 0, None))
    hist.seed((2, 1, None))
    assert not hist.can_back()
    hist.push((3, 1, None))
    assert hist.back() == (2, 1, None)
