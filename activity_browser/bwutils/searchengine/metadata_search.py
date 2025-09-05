from itertools import permutations
from collections import Counter, OrderedDict
from logging import getLogger
from time import time
from typing import Optional
import pandas as pd

from activity_browser.bwutils.searchengine import SearchEngine


log = getLogger(__name__)


class MetaDataSearchEngine(SearchEngine):
    def database_id_manager(self, database):
        if not hasattr(self, "all_database_ids"):
            self.all_database_ids = {}

        if database_ids := self.all_database_ids.get(database):
            self.database_ids = database_ids
        elif database is not None:
            self.database_ids = set(self.df[self.df["database"] == database].index.to_list())
            self.all_database_ids[database] = self.database_ids
        else:
            self.database_ids = None
        return self.database_ids

    def reset_database_id_manager(self):
        if hasattr(self, "all_database_ids"):
            del self.all_database_ids
        if hasattr(self, "database_ids"):
            del self.database_ids

    def add_identifier(self, data: pd.DataFrame) -> None:
        super().add_identifier(data)
        self.reset_database_id_manager()


    def remove_identifiers(self, identifiers, logging=True) -> None:
        t = time()

        identifiers = set(identifiers)
        current_identifiers = set(self.df.index.to_list())
        identifiers = identifiers | current_identifiers  # only remove identifiers currently in the data
        if len(identifiers) == 0:
            return

        for identifier in identifiers:
            super().remove_identifier(identifier, logging=False)

        if logging:
            log.debug(f"Search index updated in {time() - t:.2f} seconds "
                      f"for {len(identifiers)} removed items ({len(self.df)} items ({self.size_of_index()}) currently).")
        self.reset_database_id_manager()

    def change_identifier(self, identifier, data: pd.DataFrame) -> None:
        super().change_identifier(identifier, data)
        self.reset_database_id_manager()

    def auto_complete(self, word: str, database: Optional[str] = None) -> list:
        """Based on spellchecker, make more useful for autocompletions
        """
        count_occurence = lambda x: sum(self.word_to_identifier[x].values())  # count occurences of a word
        if len(word) <= 1:
            return []

        self.database_id_manager(database)

        matches_min = 2  # ideally we have at least this many alternatives
        matches_max = 4  # ideally don't much more than this many matches
        never_accept_this = 5  # values this edit distance or over always rejected
        # or max 2/3 of len(word) if less than never_accept_this
        never_accept_this = int(round(min(never_accept_this, max(1, len(word) * (2 / 3))), 0))

        # first, find possible matches quickly
        q_grams = self.text_to_positional_q_gram(word)
        possible_matches = self.find_q_gram_matches(set(q_grams), return_all=True)

        first_matches = Counter()
        other_matches = {}
        probably_keys = Counter()  # if we suspect it's a key hash, dump it at the end of the list

        # now, refine with edit distance
        for row in possible_matches.itertuples():
            if len(word) > len(row[1]) or word == row[1]:
                continue
            # find edit distance of same size strings
            edit_distance = self.osa_distance(word, row[1][:len(word)], cutoff=never_accept_this)
            if len(row[1]) == 32 and edit_distance <= 1:
                probably_keys[row[1]] = 100 - edit_distance  # keys need to be sorted on edit distance, not on occurence
            elif edit_distance == 0:
                first_matches[row[1]] = count_occurence(row[1])
            elif edit_distance < never_accept_this:
                if not other_matches.get(edit_distance):
                    other_matches[edit_distance] = Counter()
                other_matches[edit_distance][row[1]] = count_occurence(row[1])
            else:
                continue

        # add matches in correct order:
        matches = [match for match, _ in first_matches.most_common()]
        # if we have fewer matches than goal, add more 'less good' matches
        if len(matches) < matches_min:
            for i in range(1, never_accept_this):
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

        matches = matches + [match for match, _ in probably_keys.most_common()]
        return matches

    def find_q_gram_matches(self, q_grams: set, return_all: bool = False) -> pd.DataFrame:
        """Overwritten for extra database specific reduction of results.
        """
        n_q_grams = len(q_grams)

        matches = {}

        # find words that match our q-grams
        for q_gram in q_grams:
            if words := self.q_gram_to_word.get(q_gram, False):
                # q_gram exists in our search index
                for word in words:
                    if isinstance(self.database_ids, set):
                        # DATABASE SPECIFIC now filter on whether word is in the database
                        in_db = False
                        for _id in self.word_to_identifier[word]:
                            if _id in self.database_ids:
                                in_db = True
                                break
                    else:
                        in_db = True
                    if in_db:
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
        if not return_all:
            min_q = min(max(max_q * 0.32,  # have at least a third of q-grams of best match or...
                            max(n_q_grams * 0.5,  # if more, at least half the q-grams in the query word?
                                1)),  # okay just do 1 q-gram if there are no more in the word
                        max_q)  # never have min_q be over max_q
        else:
            min_q = 0

        matches = matches[matches["matches"] >= min_q]
        matches = matches.sort_values(by="matches", ascending=False)
        matches = matches.reset_index(drop=True)

        return matches.iloc[:min(len(matches), 2500), :]  # return at most this many results

    def fuzzy_search(self, text: str, database: Optional[str] = None, return_counter: bool = False, logging: bool = True) -> list:
        """Overwritten for extra database specific reduction of results.
        """
        t = time()
        text = text.strip()

        if len(text) == 0:
            log.debug(f"Empty search, returned all items")
            return self.df.index.to_list()

        # DATABASE SPECIFIC get the set of ids that is in this database
        self.database_id_manager(database)

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

        # DATABASE SPECIFIC ensure all identifiers are in the database
        if isinstance(self.database_ids, set):
            new_q2i = {}
            for word, _ids in query_to_identifier.items():
                keep = set.intersection(set(_ids.keys()), self.database_ids)
                new_id_counter = Counter()
                for _id in keep:
                    new_id_counter[_id] = _ids[_id]
                if len(new_id_counter) > 0:
                    new_q2i[word] = new_id_counter
            query_to_identifier = new_q2i

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
                if len(query_id_sets) > 0:
                    query_identifier_set = set.intersection(*query_id_sets)
                else:
                    query_identifier_set = set()
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

        if logging:
            log.debug(
                f"Found {len(all_identifiers)} search results for '{text}' in {len(self.df)} items in {time() - t:.2f} seconds")
        if return_counter:
            return all_identifiers
        # now sort on highest weights and make list type
        sorted_identifiers = [identifier[0] for identifier in all_identifiers.most_common()]
        return sorted_identifiers

    def search(self, text, database: Optional[str] = None) -> list:
        """Search the dataframe on this text, return a sorted list of identifiers."""
        t = time()
        text = text.strip()

        if len(text) == 0:
            log.debug(f"Empty search, returned all items")
            return self.df.index.to_list()

        # get the set of ids that is in this database
        self.database_id_manager(database)

        fuzzy_identifiers = self.fuzzy_search(text, database=database, logging=False)
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
