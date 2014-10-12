# -*- coding: utf-8 -*-
from brightway2 import *
import copy


class FormatConverter(object):
    """Convert a python datastructure from SimaPro names to Ecoinvent names."""
    def __init__(self, data, messages=0):
        self.messages = messages # 0/1: 1 prints out error messages
        self.data = data
        # no need to have the user define databases again...
        self.databases = list(set([c[0] for act in self.data for c in act["chain"]]))
        self.db = {}
        # Create cache when object is instantiated
        for db in self.databases:
            self.db.update(**Database(db).load())
        # self.lookup_dict = dict([
        #     ((value["name"], value["location"].lower()), key) \
        #     for key, value in self.db.iteritems()])
        self.lookup_dict = self.construct_lookup_dict()

    def construct_lookup_dict(self):
        """Creates a dictionary that maps 
        user input: (database name / process name / product / geography) 
        to a brightway2 key: (database / process key)

        Args:
            * none (uses self.db)

        Returns:
            Mapping dictionary 

        """
        lookup_dict = {}
        missing_entries = []
        for key, value in self.db.iteritems():
            name = value["name"]
            location = value["location"].lower()
            db_name = key[0]
            # product
            if [exc for exc in value['exchanges'] if exc['type'] == "production"]:
                if "name" in exc: # v3
                    product = [exc for exc in value['exchanges'] if exc['type'] == "production"][0]["name"]
                else: # v2.2
                    product = value["name"] # process name = product name
            else: # v2.2 multioutput
                 product = value["name"] # use, for now: process name = product name  
            # add lookup dictionary entry
            if (db_name, name, product, location) in lookup_dict: # check for double/conflicting entries in the dictionary
                missing_entries.append( [key, (db_name, name, product, location)] )
            else:
                lookup_dict[(db_name, name, product, location)] = key
        
        if self.messages == 1: # Print checks and user output (probably disable in the future)
            print "Lookup dictionary created with %s out of %s database entries." % (len(lookup_dict), len(self.db))
            if len(missing_entries) == 9: # 9 datasets from ecoinvent v2.2 differ only by unit
                print "WARNING: Missed %s entries (seems like the known v2.2 key problems: 9 processes differ only by unit)." %len(missing_entries)
            elif missing_entries:
                print "Warning: Missed %s entries (identical keys):" %len(missing_entries)
                for dd in missing_entries:
                    print "Key: %s Value: %s" %(dd[0], dd[1])
            
        return lookup_dict

    def convert(self):
        for dataset in self.data:
            dataset["outputs"] = [(self.find_in_databases(*o[0]), o[1], o[2] if len(o) == 3 else 1.
                ) for o in dataset["outputs"]]
            dataset["chain"] = [self.find_in_databases(*x) \
                for x in dataset["chain"]]
            dataset["cuts"] = [(
                self.find_in_databases(*o[0]),
                self.find_in_databases(*o[1]),
                o[2]) for o in dataset["cuts"]]
        return self.data

    def find_in_databases(self, db_name, name, product, location):
        return self.lookup_dict[(db_name, name, product, location.lower())]


def converted_test_data(data):
    return FormatConverter(copy.deepcopy(data)).convert()


