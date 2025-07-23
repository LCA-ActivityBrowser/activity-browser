import pytest
import pandas as pd
from activity_browser.bwutils.search import SearchEngine


def data_for_test():
    return pd.DataFrame([
        ["a", "coal production", "coal"],
        ["b", "coal production", "something"],
        ["c", "coal production", "coat"],
        ["d", "coal hello production", "something"],
        ["e", "dont find me", "hello world"],
        ["f", "coat", "another word"],
        ["g", "coalispartofthisword", "things"],
        ["h", "coal", "coal"],
    ],
    columns = ["id", "col1", "col2"])


def test_search_init():
    """Do initialization tests."""
    df = data_for_test()

    # init search class with non-existent identifier col and fail
    with pytest.raises(Exception):
        _ = SearchEngine(df, identifier_name="non_existent_col_name")
    # init search class with non-unique identifiers and fail
    df2 = df.copy()
    df2.iloc[0, 0] = "b"
    with pytest.raises(Exception):
        _ = SearchEngine(df2, identifier_name="id")
    # init search class correctly
    se = SearchEngine(df, identifier_name="id")


def test_search_base():
    """Do checks for search ranking."""

    df = data_for_test()

    # init search class and two searches
    se = SearchEngine(df, identifier_name="id")
    # do search on specific term
    assert se.search("coal") == ["a", "h", "c", "b", "d", "g", "f"]
    # do search on other term
    assert se.search("coal production") == ["a", "c", "b", "d", "h", "f", "g"]

    # init search class with 1 col searchable
    se = SearchEngine(df, identifier_name="id", searchable_columns=["col2"])
    assert se.search("coal") == ["a", "h", "c"]


def test_search_add_identifier():
    """Do tests for adding identifier."""
    df = data_for_test()

    # create base item to add
    new_base_item = {
        "id": "i",
        "col1": "coal production",
        "col2": "coal production"
    }

    # use mismatched identifier and fail
    se = SearchEngine(df, identifier_name="id")
    with pytest.raises(Exception):
        se.add_identifier(identifier="j", data=new_base_item)

    # use existing identifier and fail
    se = SearchEngine(df, identifier_name="id")
    wrong_id = new_base_item.copy()
    wrong_id["id"] = "a"
    with pytest.raises(Exception):
        se.add_identifier(identifier="a", data=wrong_id)

    # use column too many (should be removed)
    se = SearchEngine(df, identifier_name="id")
    col_more = new_base_item.copy()
    col_more["col3"] = "word"
    se.add_identifier(identifier="i", data=col_more)
    assert "col3" not in se.df.columns

    # use column less (should be filled with empty string)
    se = SearchEngine(df, identifier_name="id")
    col_less = new_base_item.copy()
    del col_less["col2"]
    se.add_identifier(identifier="i", data=col_less)
    assert se.df.loc["i", "col2"] == ""

    # do search, add item and verify results are different
    se = SearchEngine(df, identifier_name="id")
    assert se.search("coal production") == ["a", "c", "b", "d", "h", "f", "g"]
    se.add_identifier(identifier="i", data=new_base_item)
    assert se.search("coal production") == ["i", "a", "c", "b", "d", "h", "f", "g"]


def test_search_remove_identifier():
    """Do tests for removing identifier."""
    df = data_for_test()

    # use non-existent identifier and fail
    se = SearchEngine(df, identifier_name="id")
    with pytest.raises(Exception):
        se.remove_identifier(identifier="i")

    # do search, remove item and verify results are different
    se = SearchEngine(df, identifier_name="id")
    assert se.search("coal production") == ["a", "c", "b", "d", "h", "f", "g"]
    se.remove_identifier(identifier="a")
    assert se.search("coal production") == ["c", "b", "d", "h", "f", "g"]


def test_search_change_identifier():
    """Do tests for changing identifier."""
    df = data_for_test()

    # create base item to add
    edit_data = {
        "id": "a",
        "col1": "cant find me anymore",
        "col2": "something different"
    }

    # use non-existent identifier and fail
    se = SearchEngine(df, identifier_name="id")
    missing_id = edit_data.copy()
    missing_id["id"] = "i"
    with pytest.raises(Exception):
        se.change_identifier(identifier="i", data=missing_id)

    # use mismatched identifier and fail
    se = SearchEngine(df, identifier_name="id")
    wrong_id = edit_data.copy()
    wrong_id["id"] = "i"
    with pytest.raises(Exception):
        se.change_identifier(identifier="a", data=wrong_id)

    # do search, change item and verify results are different
    se = SearchEngine(df, identifier_name="id")
    assert se.search("coal production") == ["a", "c", "b", "d", "h", "f", "g"]
    se.change_identifier(identifier="a", data=edit_data)
    assert se.search("coal production") == ["c", "b", "d", "h", "f", "g"]
    # now change the same item partially and verify results are different
    new_edit_data = {
        "id": "a",
        "col1": "coal"
    }
    se.change_identifier(identifier="a", data=new_edit_data)
    assert se.search("coal production") == ["c", "b", "d", "h", "a", "f", "g"]


def test_string_distance():
    """Do tests specifically for string distance function"""
    df = data_for_test()
    se = SearchEngine(df, identifier_name="id")

    # same word
    assert se.osa_distance("coal", "coal") == 0
    # empty string is length of other word
    assert se.osa_distance("coal", "") == 4

    # insert
    assert se.osa_distance("coal", "coa") == 1
    # delete
    assert se.osa_distance("coal", "coall") == 1
    # substitute
    assert se.osa_distance("coal", "coat") == 1
    # transpose
    assert se.osa_distance("coal", "cola") == 1

    # longer edit distance
    assert se.osa_distance("coal", "chocolate") == 6
    # reverse order gives same result
    assert se.osa_distance("coal", "chocolate") == se.osa_distance("chocolate", "coal")
    # cutoff
    assert se.osa_distance("coal", "chocolate", cutoff=5, cutoff_return=1000) == 1000
    assert se.osa_distance("coal", "chocolate", cutoff=6, cutoff_return=1000) == 1000
    assert se.osa_distance("coal", "chocolate", cutoff=7, cutoff_return=1000) == 6
    # length cutoff
    assert se.osa_distance("coal", "coallongword") == 8
    assert se.osa_distance("coal", "coallongword", cutoff=5, cutoff_return=1000) == 1000
