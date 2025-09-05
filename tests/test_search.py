import pytest
import pandas as pd
from activity_browser.bwutils import SearchEngine


def data_for_test():
    return pd.DataFrame([
        ["a", "coal production", "coal"],
        ["b", "coal production", "something"],
        ["c", "coal production", "coat"],
        ["d", "coal hello production", "something"],
        ["e", "dont zzfind me", "hello world"],
        ["f", "coat", "zzanother word"],
        ["g", "coalispartofthisword", "things"],
        ["h", "coal", "coal"],
    ],
    columns = ["id", "col1", "col2"])


# test standard init
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


# test internals
def test_reverse_dict():
    """Do test to reverse the special Counter dict."""
    df = data_for_test()
    se = SearchEngine(df, identifier_name="id")

    # reverse once and verify
    w2i = se.reverse_dict_many_to_one(se.identifier_to_word)
    assert w2i == se.word_to_identifier

    # reverse again and verify is same as original
    i2w = se.reverse_dict_many_to_one(w2i)
    assert i2w == se.identifier_to_word


def test_string_distance():
    """Do tests specifically for string distance function."""
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

    # two entirely different words (test of early stopping)
    assert se.osa_distance("brown", "jumped") == 6
    assert se.osa_distance("brown", "jumped", cutoff=6, cutoff_return=1000) == 1000
    assert se.osa_distance("brown", "jumped", cutoff=7, cutoff_return=1000) == 6


# test functionality
def test_in_index():
    """Do checks for checking if word is in the index."""
    df = data_for_test()
    se = SearchEngine(df, identifier_name="id")

    # use string with space
    with pytest.raises(Exception):
        se.word_in_index("coal and space")

    assert se.word_in_index("coal")
    assert not se.word_in_index("coa")


def test_spellcheck():
    """Do checks spell checking."""
    df = data_for_test()
    se = SearchEngine(df, identifier_name="id")

    checked = se.spell_check("coa productions something flintstones")
    # coal HAS to be first, it is found more often in the data
    assert checked["coa"] == ["coal", "coat"]
    # find production
    assert checked["productions"] == ["production"]
    # should be empty as there is no alternative (but this word occurs)
    assert checked["something"] == []
    # should be empty as there is no alternative (does not exist)
    assert checked["flintstones"] == []


def test_search_base():
    """Do checks for correct search ranking."""

    df = data_for_test()

    # init search class and two searches
    se = SearchEngine(df, identifier_name="id")
    # do search on specific term
    assert se.search("coal") == ["a", "h", "c", "b", "d", "g", "f"]
    # do search on other term
    assert se.search("coal production") == ["a", "c", "b", "d", "h", "f", "g"]
    # do search on typo
    assert se.search("cola") == ["a", "c", "h", "b", "d", "f", "g"]
    # do search on longer typo
    assert se.search("cola production") == ["c", "a", "b", "d", "h", "f", "g"]
    # do search on something we will definitely not find
    assert se.search("dontFindThis") == []

    # init search class with 1 col searchable
    se = SearchEngine(df, identifier_name="id", searchable_columns=["col2"])
    assert se.search("coal") == ["a", "h", "c"]


def test_search_add_identifier():
    """Do tests for adding identifier."""
    df = data_for_test()

    # create base item to add
    new_base_item = pd.DataFrame([
        ["i", "coal production", "coal production"],
    ],
        columns=["id", "col1", "col2"])

    # use existing identifier and fail
    se = SearchEngine(df, identifier_name="id")
    wrong_id = new_base_item.copy()
    wrong_id.iloc[0, 0] = "a"
    with pytest.raises(Exception):
        se.add_identifier(wrong_id)

    # add data without identifier column
    se = SearchEngine(df, identifier_name="id")
    no_id = new_base_item.copy()
    del no_id["id"]
    with pytest.raises(Exception):
        se.add_identifier(no_id)

    # use column more (and find data in new col)
    se = SearchEngine(df, identifier_name="id")
    col_more = new_base_item.copy()
    col_more["col3"] = ["potatoes"]
    se.add_identifier(col_more)
    assert se.search("potatoes") == ["i"]

    # use column less (should be filled with empty string)
    se = SearchEngine(df, identifier_name="id")
    col_less = new_base_item.copy()
    del col_less["col2"]
    se.add_identifier(col_less)
    assert se.df.loc["i", "col2"] == ""

    # do search, add item and verify results are different
    se = SearchEngine(df, identifier_name="id")
    assert se.search("coal production") == ["a", "c", "b", "d", "h", "f", "g"]
    se.add_identifier(new_base_item)
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

    # now search on something only in a column we later remove
    assert se.search("find") == ["e"]
    se.remove_identifier(identifier="e")
    assert se.search("find") == []



def test_search_change_identifier():
    """Do tests for changing identifier."""
    df = data_for_test()

    # create base item to add
    edit_data = pd.DataFrame([
        ["a", "cant find me anymore", "something different"],
    ],
        columns=["id", "col1", "col2"])

    # use non-existent identifier and fail
    se = SearchEngine(df, identifier_name="id")
    missing_id = edit_data.copy()
    missing_id["id"] = ["i"]
    with pytest.raises(Exception):
        se.change_identifier(identifier="i", data=missing_id)

    # use mismatched identifier and fail
    se = SearchEngine(df, identifier_name="id")
    wrong_id = edit_data.copy()
    wrong_id["id"] = ["i"]
    with pytest.raises(Exception):
        se.change_identifier(identifier="a", data=wrong_id)

    # do search, change item and verify results are different
    se = SearchEngine(df, identifier_name="id")
    assert se.search("coal production") == ["a", "c", "b", "d", "h", "f", "g"]
    se.change_identifier(identifier="a", data=edit_data)
    assert se.search("coal production") == ["c", "b", "d", "h", "f", "g"]
    # now change the same item partially and verify results are different
    new_edit_data = pd.DataFrame([
        ["a", "coal"],
    ],
        columns=["id", "col1"])
    se.change_identifier(identifier="a", data=new_edit_data)
    assert se.search("coal production") == ["c", "b", "d", "h", "a", "f", "g"]
