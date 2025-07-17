from activity_browser.utils import sort_semantic_versions


def test_semantic_sort():
    """Test the semantic sorting function."""
    test_versions = ["1.2.3", "2.0.0", "1.1.1", "2.1.0", "1.0.0"]

    sorted_dsc = sort_semantic_versions(test_versions)
    assert sorted_dsc == ["2.1.0", "2.0.0", "1.2.3", "1.1.1", "1.0.0"]

    sorted_asc = sort_semantic_versions(test_versions, highest_to_lowest=False)
    assert sorted_asc == ["1.0.0", "1.1.1", "1.2.3", "2.0.0", "2.1.0"]
