"""Tests for MDSSearcher cross-database functionality."""
import pytest
import pandas as pd
from activity_browser.bwutils.metadata.searcher import MDSSearcher
from activity_browser.bwutils.metadata.metadata import MetaDataStore


@pytest.fixture
def multi_db_mds():
    """Create a MetaDataStore with multiple databases."""
    test_data = pd.DataFrame([
        [1, "db1", "coal production", "coal", "process", "", "", "", ""],
        [2, "db1", "coal mining", "coal", "process", "", "", "", ""],
        [3, "db1", "steel production", "steel", "process", "", "", "", ""],
        [4, "db2", "coal transport", "transport", "process", "", "", "", ""],
        [5, "db2", "electricity from coal", "electricity", "process", "", "", "", ""],
        [6, "db3", "coal combustion", "heat", "process", "", "", "", ""],
        [7, "db3", "gas production", "gas", "process", "", "", "", ""],
    ], columns=["id", "database", "name", "reference product", "type", "location", "unit", "comment", "tags"])

    mds = MetaDataStore()
    mds.dataframe = test_data
    return mds


def test_search_single_database(multi_db_mds):
    """Test searching within a single database."""
    searcher = MDSSearcher(multi_db_mds)

    # Search for "coal" in db1
    results = searcher.search("coal", database="db1")
    assert len(results) == 2
    assert set(results) == {1, 2}

    # Search for "coal" in db2
    results = searcher.search("coal", database="db2")
    assert len(results) == 2
    assert set(results) == {4, 5}

    # Search for "coal" in db3
    results = searcher.search("coal", database="db3")
    assert len(results) == 1
    assert set(results) == {6}


def test_search_all_databases(multi_db_mds):
    """Test searching across all databases when database=None."""
    searcher = MDSSearcher(multi_db_mds)

    # Search for "coal" across all databases
    results = searcher.search("coal", database=None)
    assert len(results) == 5
    assert set(results) == {1, 2, 4, 5, 6}

    # Search for "production" across all databases
    results = searcher.search("production", database=None)
    assert len(results) == 3
    assert set(results) == {1, 3, 7}


def test_fuzzy_search_all_databases(multi_db_mds):
    """Test fuzzy search across all databases."""
    searcher = MDSSearcher(multi_db_mds)

    # Fuzzy search for "coal" across all databases
    results = searcher.fuzzy_search("coal", database=None)
    assert len(results) >= 5

    # Fuzzy search for "production" across all databases
    results = searcher.fuzzy_search("production", database=None)
    assert len(results) >= 3


def test_search_cache_separation(multi_db_mds):
    """Test that search cache properly separates single-db and all-db searches."""
    searcher = MDSSearcher(multi_db_mds)

    # Do searches to populate cache
    results_db1 = searcher.search("coal", database="db1")
    results_all = searcher.search("coal", database=None)

    # Verify results are different
    assert len(results_db1) == 2
    assert len(results_all) == 5
    assert set(results_db1).issubset(set(results_all))

    # Search again to use cached results
    results_3ached = searcher.search("coal", database="db1")
    results_all_cached = searcher.search("coal", database=None)

    # Verify cached results match original
    assert results_db1 == results_3ached
    assert results_all == results_all_cached


def test_auto_complete_all_databases(multi_db_mds):
    """Test autocomplete across all databases."""
    searcher = MDSSearcher(multi_db_mds)

    # Autocomplete for "coa" across all databases
    completions = searcher.auto_complete("coa", database=None)
    assert "coal" in completions

    # Autocomplete for "prod" in specific database
    completions_db1 = searcher.auto_complete("prod", database="db1")
    assert "production" in completions_db1

    # Autocomplete for "prod" across all databases
    completions_all = searcher.auto_complete("prod", database=None)
    assert "production" in completions_all


def test_empty_search_all_databases(multi_db_mds):
    """Test empty search returns all items when database=None."""
    searcher = MDSSearcher(multi_db_mds)

    results = searcher.search("", database=None)
    assert len(results) == 7  # All items in all databases

