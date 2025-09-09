from itertools import permutations, chain
import itertools
import functools
from collections import Counter, OrderedDict, defaultdict
from logging import getLogger
import math
import multiprocessing as mp
from time import time
from typing import Iterable, Optional
import pandas as pd
import numpy as np
import re
import sys


log = getLogger(__name__)


class SearchEngine:
    """
    A Search Engine class, takes a dataframe and makes it searchable.

    A search requires a string, and will return a list of unique identifiers in the dataframe.
    There are three options for search:
        SearchEngine.literal_search(): searches for exact matches of the search query
        SearchEngine.fuzzy_search(): searches for approximate matches of search query, sorted by relevance
        SearchEngine.search(): combines both of the above, literal matches are returned first, next all fuzzy results,
        but subsets sorted by relevance.
    It is recommended to always use searchEngine.search(), but the other options are there.

    Initialization takes:
        df: Dataframe that needs to be searchable.
        identifier_name: values in this column will be returned as search results, all values in this column need to be unique.
        searchable_columns: these columns need to be searchable, if none are given, all columns will be made searchable.

    Updating data is possible as well:
        add_identifier(): adds this identifier to the searchable data
        remove_identifier(): removes this identifier from the searchable data
        change_identifier(): changes this identifier (wrapper for remove_identifier and add_identifier)

    """

    def __init__(self, df: pd.DataFrame, identifier_name: str, searchable_columns: list = []):
        t = time()
        log.debug(f"SearchEngine initializing for {len(df)} items")

        # compile regex patterns for cleaning
        self.SUB_END_PATTERN = re.compile(r"[,.\"'`)\[\]}\\/\-−_:;+…]+(?=\s|$)")  # remove these from end of word
        self.SUB_START_PATTERN = re.compile(r"(?:^|\s)[,.\"'`(\[{\\/\-−_:;+]+")  # remove these from start of word
        self.ONE_SPACE_PATTERN = re.compile(r"\s+")  # remove these multiple whitespaces

        self.q = 2  # character length of q grams
        self.base_weight = 10  # base weighting for sorting results

        if identifier_name not in df.columns:  # make sure identifier col exist
            raise NameError(f"Identifier column {identifier_name} not found in dataframe. Use an existing column name.")
        if df[identifier_name].nunique() != df.shape[0]:  # make sure identifiers are all unique
            raise KeyError(
                f"Identifier column {identifier_name} must only contain unique values. Found {df[identifier_name].nunique()} unique values for length {df.shape[0]}")

        self.identifier_name = identifier_name

        # ensure columns given actually exist
        # always ensure "identifier" is present
        if searchable_columns == []:
            # if no list is given, assume all columns are searchable
            self.columns = list(df.columns)
        else:
            # create subset of columns to be searchable, discard rest
            self.columns = [col for col in searchable_columns if col in df.columns]
            if self.identifier_name not in self.columns:  # keep identifier col
                self.columns.append(self.identifier_name)
            df = df[self.columns]
        # set the identifier column as index
        df = df.set_index(self.identifier_name, drop=False)

        # convert all data to str
        df = df.astype(str)

        # find the self.identifier_name column index and store as int
        self.identifier_column = self.columns.index(self.identifier_name)

        # store all searchable column indices except the identifier
        self.searchable_columns = [i for i in range(len(self.columns)) if i != self.identifier_column]

        # initialize search index dicts and update df
        self.identifier_to_word = {}
        self.word_to_identifier = {}
        self.word_to_q_grams = {}
        self.q_gram_to_word = {}
        self.df = pd.DataFrame()

        self.update_index(df)

        log.debug(f"SearchEngine Initialized in {time() - t:.2f} seconds")

    #   +++ Utility functions

    def update_index(self, update_df: pd.DataFrame) -> None:
        """Update search index dicts and the df."""

        def update_dict(update_me: dict, new: dict) -> dict:
            """Update a dict of counters with new dict of counters."""
            # set to empty set if we know update_me is empty, otherwise, find set intersection
            update_keys = set() if len(update_me) == 0 else new.keys() & update_me.keys()
            if len(update_keys) == 0:
                new_data = new
            else:
                for update_key in update_keys:
                    update_me[update_key].update(new[update_key])
                new_data = {key: value for key, value in new.items() if key not in update_keys}
            # finally add any completely new data
            # update_me.update(new_data)
            update_me = update_me | new_data
            return update_me

        t = time()
        size_old = len(self.df)
        # identifier to word and df
        i2w, update_df = self.words_in_df(update_df)
        self.identifier_to_word = update_dict(self.identifier_to_word, i2w)
        self.df = pd.concat([self.df, update_df])
        # word to identifier
        w2i = self.reverse_dict_many_to_one(i2w)
        self.word_to_identifier = update_dict(self.word_to_identifier, w2i)
        # word to q-gram
        w2q = self.list_to_q_grams(w2i.keys())
        self.word_to_q_grams = update_dict(self.word_to_q_grams, w2q)
        # q-gram to word
        q2w = self.reverse_dict_many_to_one(w2q)
        self.q_gram_to_word = update_dict(self.q_gram_to_word, q2w)
        size_new = len(self.df)
        size_dif = size_new - size_old
        size_msg = (f"{size_dif} changed items at {int(round(size_dif/(time() - t), 0))} items/sec "
                    f"({size_new} items ({self.size_of_index()}) currently)") if size_dif > 1 \
            else f"1 changed item ({size_new} items ({self.size_of_index()}) currently)"
        log.debug(f"Search index updated in {time() - t:.2f} seconds for {size_msg}.")

    def clean_text(self, text: str):
        """Clean a string so it doesn't contain weird characters or multiple spaces etc."""
        text = text.lower()
        text = self.SUB_END_PATTERN.sub("", text)
        text = self.SUB_START_PATTERN.sub(" ", text)

        text = self.ONE_SPACE_PATTERN.sub(" ", text).strip()
        return text

    def text_to_positional_q_gram(self, text: str) -> list:
        """Return a positional list of q-grams for the given string.

        q-grams are n-grams on character level.
        q-grams at q=2 of "word" would be "wo", "or" and "rd"
        https://en.wikipedia.org/wiki/N-gram

        Note: these are technically _positional_ q-grams, but we don't use their positions currently.
        """
        q = self.q
        n = len(text)
        # just return a single-item list if the text is equal or shorter than q
        # else, generate q-grams
        if n <= q:
            return [text]
        return list(text[i:i + q] for i in range(n - q + 1))

    def df_clean_worker(self, df):
        """Clean the text in query_col."""
        df["query_col"] = df["query_col"].apply(self.clean_text)
        return df

    def df_clean(self, df):
        """Clean the text in query_col.

        apply multi-processing when the computer is able and its relevant
        """
        def chunk_dataframe(df: pd.DataFrame, chunk_size: int):
            """Split DataFrame into chunks of specified size."""
            return [df.iloc[i:i + chunk_size] for i in range(0, len(df), chunk_size)]

        max_cores = max(1, mp.cpu_count() - 1)  # leave at least 1 core for other processes
        min_chunk_size = 2500
        if max_cores > 1 and len(df) > min_chunk_size * 2:
            for i in range(max_cores, 0, -1):
                chunk_size = int(math.ceil(len(df) / i))
                if chunk_size >= min_chunk_size:
                    break
            use_cores = i
        else:
            use_cores = 1
        if use_cores == 1:
            return self.df_clean_worker(df)

        chunks = chunk_dataframe(df, chunk_size)
        with mp.Pool(processes=use_cores) as pool:
            results = pool.starmap(self.df_clean_worker, [(chunk,) for chunk in chunks])
        return pd.concat(results)

    def words_in_df(self, df: pd.DataFrame = None) -> tuple[dict, pd.DataFrame]:
        """Return a dict of {identifier: word} for df."""

        df = df if df is not None else self.df.copy()
        df = df.fillna("")  # avoid nan
        # assemble query_col
        df["query_col"] = df.iloc[:, self.searchable_columns].astype(str).agg(" | ".join, axis=1)
        # clean all text at once using vectorized operations
        df["query_col"] = self.df_clean(df.loc[:, ["query_col"]])
        # build the identifier_word_dict dictionary
        identifier_word_dict = df["query_col"].apply(lambda text: Counter(text.split(" "))).to_dict()
        return identifier_word_dict, df

    def reverse_dict_many_to_one(self, dictionary: dict) -> dict:
        """Reverse a dictionary of Counter objects."""
        reverse = defaultdict(Counter)
        for identifier, counter_object in dictionary.items():
            for countable, count in counter_object.items():
                reverse[countable][identifier] += count
        return dict(reverse)

    def list_to_q_grams(self, word_list: Iterable) -> dict:
        """Convert a list of unique words to a dict with Counter objects.

        Number will be the occurrences of that q-gram in that word.

        return = {
            "word": Counter(
                "wo": 1
                "or": 1
                "rd": 1
                ),
            ...
            }
        """
        text_to_q_gram = self.text_to_positional_q_gram
        return {
            word: Counter(text_to_q_gram(word))
            for word in word_list
        }

    def word_in_index(self, word: str) -> bool:
        """Convenience function to check if a single word is in the search index."""
        if " " in word:
            raise Exception(
                f"Given word '{word}' must not contain spaces.")
        return word in self.word_to_identifier.keys()

    def size_of_index(self):
        """return the size of the search index in MB or GB."""
        s_df = sys.getsizeof(self.df)
        s_i2w = sys.getsizeof(self.identifier_to_word)
        s_w2i = sys.getsizeof(self.word_to_identifier)
        s_w2q = sys.getsizeof(self.word_to_q_grams)
        s_q2w = sys.getsizeof(self.q_gram_to_word)
        size_bytes = s_df + s_i2w + s_w2i + s_w2q + s_q2w

        if size_bytes < 1024 ** 3:
            return f"{size_bytes / (1024 ** 2):.1f} MB"
        else:
            return f"{size_bytes / (1024 ** 3):.2f} GB"

    #   +++ Changes to searchable data

    def add_identifier(self, data: pd.DataFrame) -> None:
        """Add this data to the search index.

        identifier column is REQUIRED to be present
        ALL data in the given dataframe will be added, if columns should not be added, they should be removed before
        calling this function
        """

        # ensure we have identifier column
        if self.identifier_name not in data.columns:
            raise Exception(
                f"Identifier column '{self.identifier_name}' not in new data, impossible to add data without identifier")

        # make sure we the new identifiers do not yet exist
        existing_ids = set(self.df.index.to_list())
        for identifier in data[self.identifier_name]:
            if identifier in existing_ids:
                raise Exception(
                    f"Identifier '{identifier}' is already in use, use a different identifier or use the change_identifier function.")

        # make sure all new identifiers given are unique
        if data[self.identifier_name].nunique() != data.shape[0]:
            raise KeyError(
                f"Identifier column {self.identifier_name} must only contain unique values. Found {data[self.identifier_name].nunique()} unique values for length {data.shape[0]}")

        df_cols = self.columns
        # add cols to new data that are missing
        for col in df_cols:
            if col not in data.columns:
                data.loc[:, col] = [""] * len(data)
        # re-order cols, first existing, then new
        df_col_set = set(df_cols)
        new_cols = [col for col in data.columns if col not in self.columns if col not in df_col_set]
        data_cols = df_cols + new_cols
        data = data[data_cols]  # re-order new data to be in correct order

        # add cols from new data to correct places
        self.columns.extend(new_cols)
        self.searchable_columns.extend([i for i, col in enumerate(data_cols) if col in new_cols])

        # convert df
        data = data.set_index(self.identifier_name, drop=False)
        data = data.fillna("")
        data = data.astype(str)

        # update the search index data
        self.update_index(data)

    def remove_identifier(self, identifier, logging=True) -> None:
        """Remove this identifier from self.df and the search index.
        """
        if logging:
            t = time()

        # make sure the identifier exists
        if identifier not in self.df.index.to_list():
            raise Exception(
                f"Identifier '{identifier}' does not exist in the search data, cannot remove identifier that do not exist.")

        self.df = self.df.drop(identifier)

        # find words that may need to be removed
        words = self.identifier_to_word[identifier]
        for word in words:
            if len(self.word_to_identifier[word]) == 1:
                # this word is only found in this identifier,
                # remove the word and check for q grams
                del self.word_to_identifier[word]

                q_grams = self.word_to_q_grams[word]
                for q_gram in q_grams:
                    if len(self.q_gram_to_word[q_gram]) == 1:
                        # this q_gram is only used in this word,
                        #  remove it
                        del self.q_gram_to_word[q_gram]
                    elif len(self.q_gram_to_word[q_gram]) > 1:
                        # this q_gram is used in multiple words, only remove the word from the q_gram
                        del self.q_gram_to_word[q_gram][word]

                del self.word_to_q_grams[word]
            else:
                # this word is found in multiple identifiers
                # word_to_q_gram and q_gram_to_word do not need to be changed, the word still exists
                # remove the identifier the word in word_to_identifier
                del self.word_to_identifier[word][identifier]
        # finally, remove the identifier
        del self.identifier_to_word[identifier]

        if logging:
            log.debug(f"Search index updated in {time() - t:.2f} seconds "
                      f"for 1 removed item ({len(self.df)} items ({self.size_of_index()}) currently).")

    def change_identifier(self, identifier, data: pd.DataFrame) -> None:
        """Change this identifier.

        identifier must be an identifier that is in use
        data must be a dataframe of 1 row with all change data
        data is overwritten with the new data in 'data', columns not given remain unchanged
        """

        # make sure only 1 change item is given
        if len(data) > 1 or len(data) < 1:
            raise Exception(
                f"change data must be for exactly 1 identifier, but {len(data)} items were given.")
        # make sure correct use of identifier
        if identifier not in self.df.index.to_list():
            raise Exception(
                f"Identifier '{identifier}' does not exist in the search data, use an existing identifier or use the add_identifier function.")
        if self.identifier_name in data.columns and data[self.identifier_name].to_list() != [identifier]:
            raise Exception(
                "Identifier field cannot be changed, first remove item and then add new identifier")
        if "query_col" in data.keys():
            log.debug(
                f"Field 'query_col' is a protected field for search engine and will be ignored for changing {identifier}")


        # overwrite new data where relevant
        update_data = self.df.loc[[identifier], self.columns]
        data = data.reset_index(drop=True)
        for col in data.columns:
            value = data.loc[0, col]
            update_data[col] = [value]

        # remove the entry
        self.remove_identifier(identifier, logging=False)
        # add entry with updated data
        self.add_identifier(update_data)

    #   +++ Search

    def filter_dataframe(self, df: pd.DataFrame, pattern: str, search_columns: Optional[list] = None) -> pd.Series:
        """Filter the search columns of a dataframe on a pattern.

        Returns a mask (true/false) pd.Series with matching items."""

        search_columns = search_columns if search_columns else self.columns
        mask = functools.reduce(
            np.logical_or,
            [
                df[col].apply(lambda x: pattern in x.lower())
                for col in search_columns
            ],
        )
        return mask

    def literal_search(self, text, df: Optional[pd.DataFrame] = None) -> list:
        """Do literal search of the text in all original columns that were given."""

        if df is None:
            df = self.df.copy()

        identifiers = self.filter_dataframe(df, text)
        df = df.loc[identifiers]
        identifiers = df.index.to_list()
        return identifiers

    def osa_distance(self, word1: str, word2: str, cutoff: int = 0, cutoff_return: int = 1000) -> int:
        """Calculate the Optimal String Alignment (OSA) edit distance between two strings, return edit distance.

        Has additional cutoff variable, if cutoff is higher than 0 and if the words have
        a larger edit distance, return a large number (note: cutoff <= edit_dist, not cutoff < edit_dist)

        OSA is a restricted form of the Damerau–Levenshtein distance.
        https://en.wikipedia.org/wiki/Damerau%E2%80%93Levenshtein_distance#Optimal_string_alignment_distance

        The edit distance is how many operations (insert, delete, substitute or transpose a character) need to happen to convert one string to another.
        insert and delete are obvious operations, but substitute and transpose are explained:
            substitute: replace one character with another: e.g. word1='cat' word2='cab', 't'->'b' substitution is 1 operation
            transpose: swap the places of two adjacent characters with each other: e.g. word1='coal' word2='cola' 'al' -> 'la' transposition is 1 operation

        The minimum amount of edit operations (OSA edit distance) is returned.
        """
        if word1 == word2:
            # if the strings are the same, immediately return 0
            return 0

        len1, len2 = len(word1), len(word2)

        if 0 < cutoff <= abs(len1 - len2):
            # if the length difference between 2 words is over the cutoff,
            # just return instead of calculating the edit distance
            return cutoff_return

        if len1 == 0 or len2 == 0:
            # in case (at least) one of the strings is empty,
            # return the length of the longest string
            return max(len1, len2)

        if len1 < len2 and cutoff > 0:
            # make sure word1 is always the longest (required for early stopping with cutoff)
            word1, word2 = word2, word1
            len1, len2 = len2, len1

        # Initialize matrix
        distance = [[0] * len2 for _ in range(len1)]

        # calculate shortest edit distance
        for i in range(len1):
            for j in range(len2):
                cost = 0 if word1[i] == word2[j] else 1

                # Compute distances for insertion, deletion and substitution
                insertion = distance[i][j - 1] + 1 if j > 0 else i + 1
                deletion = distance[i - 1][j] + 1 if i > 0 else j + 1
                substitution = distance[i - 1][j - 1] + cost if i > 0 and j > 0 else max(i, j) + cost

                distance[i][j] = min(deletion, insertion, substitution)

                # Compute transposition when relevant
                if i > 0 and j > 0 and word1[i] == word2[j - 1] and word1[i - 1] == word2[j]:
                    transposition = distance[i - 2][j - 2] + 1 if i > 1 and j > 1 else max(i, j) - 1
                    distance[i][j] = min(distance[i][j], transposition)

            # stop early if we surpass cutoff
            if 0 < cutoff <= min(distance[i]):
                return cutoff_return
        return distance[i][j]

    def find_q_gram_matches(self, q_grams: set) -> pd.DataFrame:
        """Find which of the given q_grams exist in self.q_gram_to_word,
        return a sorted dataframe of best matching words.
        """
        n_q_grams = len(q_grams)

        matches = {}

        # find words that match our q-grams
        for q_gram in q_grams:
            if words := self.q_gram_to_word.get(q_gram, False):
                # q_gram exists in our search index
                for word in words:
                    matches[word] = matches.get(word, 0) + words[word]

        # if we find no results, return an empty dataframe
        if len(matches) == 0:
            return pd.DataFrame({"word": [], "matches": []})

        # otherwise, create a dataframe and
        # reduce search results to most relevant results
        matches = {"word": matches.keys(), "matches": matches.values()}
        matches = pd.DataFrame(matches)
        max_q = max(matches["matches"])  # this has the most matching q-grams

        # determine how many results we want to keep based on how good our results are
        min_q = min(max(max_q * 0.32,  # have at least a third of q-grams of best match or...
                        max(n_q_grams * 0.5,  # if more, at least half the q-grams in the query word?
                            1)),  # okay just do 1 q-gram if there are no more in the word
                    max_q)  # never have min_q be over max_q

        matches = matches[matches["matches"] >= min_q]
        matches = matches.sort_values(by="matches", ascending=False)
        matches = matches.reset_index(drop=True)

        return matches.iloc[:min(len(matches), 2500), :]  # return at most this many results

    def spell_check(self, text: str, skip_len=1) -> OrderedDict:
        """Create an OrderedDict of each word in the text (space separated)
        with as values possible alternatives.

        Alternatives are first found with q-grams, then refined with string edit distance

        We rank alternative words based on 1) edit distance 2) how often a word is used in an entry
        If too many results are found, we only keep edit distance 1,
        if we want more results, we keep with longer edit distance up to `never_accept_this`

        word_results = OrderedDict(
            "word": [work]
            )

        NOTE: only ALTERNATIVES are ever returned, this function returns empty list for item BOTH when
            1) the exact word is in the data
            2) when there are no suitable alternatives
        """
        count_occurence = lambda x: sum(self.word_to_identifier[x].values())  # count occurences of a word

        word_results = OrderedDict()

        matches_min = 3  # ideally we have at least this many alternatives
        matches_max = 10  # ideally don't much more than this many matches
        always_accept_this = 1  # values of this edit distance or lower always accepted
        never_accept_this = 4  # values this edit distance or over always rejected

        # make list of unique words
        text = self.clean_text(text)
        words = OrderedDict()
        for word in text.split(" "):
            if len(word) != 0:
                words[word] = False
        words = words.keys()

        for word in words:
            if len(word) <= skip_len:  # dont look for alternatives for text this short
                word_results[word] = []
                continue

            # reduce acceptable edit distance with short words
            dont_accept = int(round(max(1, min((len(word) * 0.66), never_accept_this)), 0))

            # first, find possible matches quickly
            q_grams = self.text_to_positional_q_gram(word)
            possible_matches = self.find_q_gram_matches(set(q_grams))

            first_matches = Counter()
            other_matches = {}

            # now, refine with edit distance
            for row in possible_matches.itertuples():

                edit_distance = self.osa_distance(word, row[1], cutoff=dont_accept)

                if edit_distance == 0:
                    continue  # we are looking for alternatives only, not the exact word
                elif edit_distance <= always_accept_this:
                    first_matches[row[1]] = count_occurence(row[1])
                elif edit_distance < dont_accept:
                    if not other_matches.get(edit_distance):
                        other_matches[edit_distance] = Counter()
                    other_matches[edit_distance][row[1]] = count_occurence(row[1])
                else:
                    continue

            # add matches in correct order:
            matches = [match for match, _ in first_matches.most_common()]
            # if we have fewer matches than goal, add more 'less good' matches
            if len(matches) < matches_min:
                for i in range(always_accept_this + 1, dont_accept):
                    # iteratively increase matches with 'worse' results so we hit goal of minimum alternatives
                    if new := other_matches.get(i):
                        prev_num = 10e100
                        for match, num in new.most_common():
                            if num == prev_num:
                                matches.append(match)
                            elif num != prev_num and len(matches) <= matches_max:
                                matches.append(match)
                            else:
                                break
                            prev_num = num

            word_results[word] = matches
        return word_results

    def build_queries(self, query_text) -> list:
        """Make all possible subsets of words in the query, including alternative words."""
        query_text = self.spell_check(query_text)

        # find all combinations of the query words as given
        queries = list(query_text.keys())
        subsets = list(chain.from_iterable(
            (itertools.combinations(
                queries, r) for r in range(1, len(queries) + 1))))
        all_queries = []

        for combination in subsets:
            # add the 'default' option
            all_queries.append(combination)
            # now add all options with all alternatives
            for i, word in enumerate(combination):
                for alternative in query_text.get(word, []):
                    alternative_combination = list(combination)
                    alternative_combination[i] = alternative
                    all_queries.append(alternative_combination)

        return all_queries

    def weigh_identifiers(self, identifiers: Counter, weight: int, weighted_ids: Counter) -> Counter:
        """Add weights to identifier counter for these identifiers times how often it occurs in identifier."""
        for identifier, occurrences in identifiers.items():
            weighted_ids[identifier] += (weight * occurrences)
        return weighted_ids

    def search_size_1(self, queries: list, original_words: set, orig_word_weight=5, exact_word_weight=1) -> dict:
        """Return a dict of {query_word: Counter(identifier)}.

        queries: is a list of len 1 tuple/lists of words that are a searched word or a 'spell checked' similar word
        original words: a list of words actually searched for (not including spellchecked)

        orig_word_weight: additional weight to add to original words
        exact_word_weight: additional weight to add to exact word matches (as opposed to be 'in' str)

        First, we find all matching words, creating a dict of words in 'queries' as keys and words matching that query word as list of values
        Next, we convert this to identifiers and add weights:
            Weight will be increased if matching 'orig_word_weight' or 'exact_word_weight'
        """
        matches = {}
        # add each word in search index if query_word in word
        for word in self.word_to_identifier.keys():
            for query in queries:
                # query is list/tuple of len 1
                query_word = query[0]  # only use the word
                if query_word in word:
                    words = matches.get(query_word, [])
                    words.extend([word])
                    matches[query_word] = words

        # now convert matched words to matched identifiers
        matched_identifiers = {}
        for word, matching_words in matches.items():
            for matched_word in matching_words:
                weight = self.base_weight
                id_counter = matched_identifiers.get(word, Counter())

                # add the word n times, where n is the weight, original search word is weighted higher than alternatives
                if matched_word in original_words:
                    weight += orig_word_weight  # increase weight for original word
                if matched_word == word:
                    weight += exact_word_weight  # increase weight for exact matching word

                id_counter = self.weigh_identifiers(self.word_to_identifier[matched_word], weight, id_counter)
                matched_identifiers[word] = id_counter

        return matched_identifiers

    def fuzzy_search(self, text: str, return_counter: bool = False) -> list:
        """Search the dataframe, finding approximate matches and return a list of identifiers,
        ranked by how well each identifier matches the search text.

        1. First, identifiers matching single words (and spell-checked alternatives) are found and weighted.
        2. If the search term consisted of multiple words, combinations of those words are checked next.
            2.1 Increasing in size (first two words, then three etc.), we look for identifiers that contain that set of
            words, these are also weighted, based on the sum of all one-word weights (from first step) and the length
            of the sequence.
            2.2 Next, we also look specifically for combinations occurring next to each other. And add more weight like
            the step above (2.1).
        We multiply the weighting of step 2 by the sequence length, based on the assumption that finding more search
        words will be a more relevant result than just finding a single word, and again if they are in the
        correct order.

        Finally, all found identifiers are sorted on their weight and returned.
        """
        text = text.strip()

        queries = self.build_queries(text)

        # make list of unique original words
        orig_words = OrderedDict()
        for word in text.split(" "):
            orig_words[word] = False
        orig_words = orig_words.keys()
        orig_words = {self.clean_text(word) for word in orig_words}

        # order the queries by the amount of words they contain
        # we do this because longer queries (more words) are harder to find, but we have many alternatives so we search in a smaller search space
        queries_by_size = OrderedDict()
        longest_query = max([len(q) for q in queries])
        for query_len in range(1, longest_query + 1):
            queries_by_size[query_len] = [q for q in queries if len(q) == query_len]

        # first handle queries of length 1
        query_to_identifier = self.search_size_1(queries_by_size[1], orig_words)

        # get all results into a df, we rank further later
        all_identifiers = set()
        for id_list in [id_list for id_list in query_to_identifier.values()]:
            all_identifiers.update(id_list)
        search_df = self.df.loc[list(all_identifiers)]

        # now, we search for combinations of query words and get only those identifiers
        # we then reduce de search_df further for only those matching identifiers
        # we then search the permutations of that set of words
        for q_len, query_set in queries_by_size.items():
            if q_len == 1:
                # we already did these above
                continue
            for query in query_set:
                # get the intersection of all identifiers
                # meaning, a set of identifiers that occur in ALL sets of len(1) for the individual words in the query
                # this ensures we only ever search data where ALL items occur to substantially reduce search-space
                # finally, make this a Counter (with each item=1) so we can properly weigh things later
                query_id_sets = [set(query_to_identifier.get(q_word)) for q_word in query if
                                 query_to_identifier.get(q_word, False)]
                if len(query_id_sets) == 0:
                    continue
                query_identifier_set = set.intersection(*query_id_sets)
                if len(query_identifier_set) == 0:
                    # there is no match for this combination of query words, skip
                    break

                # now we convert the query identifiers to a Counter of 'occurrence',
                # where we weigh queries with only original words higher
                query_identifiers = Counter()
                for identifier in query_identifier_set:
                    weight = 0
                    for query_word in query:
                        # if the query_word and identifier combination exist get score, otherwise 0
                        weight += query_to_identifier.get(query_word, {}).get(identifier, 0)

                    query_identifiers[identifier] = weight

                # we now add these identifiers to a counter for this query name,
                query_name = " ".join(query)

                weight = self.base_weight * q_len
                query_to_identifier[query_name] = self.weigh_identifiers(query_identifiers, weight, Counter())

                # now search for all permutations of this query combined with a space
                query_df = search_df[search_df[self.identifier_name].isin(query_identifiers)]
                for query_perm in permutations(query):
                    mask = self.filter_dataframe(query_df, " ".join(query_perm), search_columns=["query_col"])
                    new_df = query_df.loc[mask].reset_index(drop=True)
                    if len(new_df) == 0:
                        # there is no match for this permutation of words, skip
                        continue
                    new_id_list = new_df[self.identifier_name]

                    new_ids = Counter()
                    for new_id in new_id_list:
                        new_ids[new_id] = query_identifiers[new_id]

                    # we weigh a combination of words that is next also to each other even higher than just the words separately
                    query_to_identifier[query_name] = self.weigh_identifiers(new_ids, weight,
                                                                             query_to_identifier[query_name])
        # now finally, move to one object sorted list by highest score
        all_identifiers = Counter()
        for identifiers in query_to_identifier.values():
            all_identifiers += identifiers

        if return_counter:
            return all_identifiers
        # now sort on highest weights and make list type
        sorted_identifiers = [identifier for identifier, _ in all_identifiers.most_common()]
        return sorted_identifiers

    def search(self, text) -> list:
        """Search the dataframe on this text, return a sorted list of identifiers."""
        t = time()
        text = text.strip()

        if len(text) == 0:
            log.debug(f"Empty search, returned all items")
            return self.df.index.to_list()

        fuzzy_identifiers = self.fuzzy_search(text)
        if len(fuzzy_identifiers) == 0:
            log.debug(f"Found 0 search results for '{text}' in {len(self.df)} items in {time() - t:.2f} seconds")
            return []

        # take the fuzzy search sub-set of data and search it literally
        df = self.df.loc[fuzzy_identifiers].copy()

        literal_identifiers = self.literal_search(text, df)
        if len(literal_identifiers) == 0:
            log.debug(
                f"Found {len(fuzzy_identifiers)} search results for '{text}' in {len(self.df)} items in {time() - t:.2f} seconds")
            return fuzzy_identifiers

        # append any fuzzy identifiers that were not found in the literal search
        literal_id_set = set(literal_identifiers)
        remaining_fuzzy_identifiers = [
            _id for _id in fuzzy_identifiers if _id not in literal_id_set]
        identifiers = literal_identifiers + remaining_fuzzy_identifiers

        log.debug(
            f"Found {len(identifiers)} ({len(literal_identifiers)} literal) search results for '{text}' in {len(self.df)} items in {time() - t:.2f} seconds")
        return identifiers
