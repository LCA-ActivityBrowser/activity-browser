#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui, QtCore
import brightway2 as bw2
from bw2analyzer import ContributionAnalysis
from bw2data.utils import recursive_str_to_unicode
import uuid

class MyQTableWidgetItem(QtGui.QTableWidgetItem):
    def __init__(self, parent=None):
        super(MyQTableWidgetItem, self).__init__(parent)
        self.activity_or_database_key = None
        self.key_type = None
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)  # existing flags, but not editable
        self.path = None  # TODO: need a more generic data store
        self.uuid_ = None

class MyStandardItem(QtGui.QStandardItem):
    def __init__(self, parent=None):
        super(MyStandardItem, self).__init__(parent)
        self.activity_or_database_key = None
        self.key_type = None
        self.setEditable(False)

class MyTreeWidgetItem(QtGui.QTreeWidgetItem):
    def __init__(self, parent=None, *args):
        super(MyTreeWidgetItem, self).__init__(parent, *args)
        self.activity_or_database_key = None
        self.key_type = None
        self.setFlags(self.flags() & ~QtCore.Qt.ItemIsEditable)

class HelperMethods(object):
    def __init__(self):
        pass

    def update_table(self, table, data, keys, edit_keys=None):
        """
        A generic method to fill a QTableWidget
        :param table: QTableWidget object
        :param data: list of dictionaries
        :param keys: dictionary keys that are to be displayed
        :return: QTableWidget object
        """
        if not data:
            table.setRowCount(0)
            return table
        else:
            table.setSortingEnabled(False)
            table.blockSignals(True)
            table.setRowCount(len(data))
            table.setColumnCount(len(keys))
            table.setHorizontalHeaderLabels(keys)

            for i, d in enumerate(data):
                for j in range(len(keys)):
                    mqtwi = MyQTableWidgetItem(str(d[keys[j]]))
                    if "key" in d:
                        mqtwi.activity_or_database_key = d["key"]
                        mqtwi.key_type = d["key_type"]
                    if 'path' in d:
                        mqtwi.path = d['path']
                    if 'uuid_' in d:
                        mqtwi.uuid_ = d['uuid_']
                    if edit_keys and keys[j] in edit_keys:
                        mqtwi.setFlags(mqtwi.flags() | QtCore.Qt.ItemIsEditable)
                    table.setItem(i, j, mqtwi)
            if edit_keys:
                table.setEditTriggers(QtGui.QTableWidget.AllEditTriggers)
            else:
                table.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.resizeColumnsToContents()
            table.resizeRowsToContents()
            table.blockSignals(False)
            table.setSortingEnabled(True)
        return table

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

class Styles(object):
    def __init__(self):
        # BIG FONT
        self.font_big = QtGui.QFont()
        self.font_big.setPointSize(10)
        self.font_big.setBold(True)
        # FAT
        self.font_bold = QtGui.QFont()
        self.font_bold.setPointSize(9)
        self.font_bold.setBold(True)

class Checks(object):
    pass

class BrowserStandardTasks(object):
    def __init__(self):
        self.history = []
        self.currentActivity = None
        self.db = None
        self.database = None
        self.database_version = None
        self.LCIA_calculations = {}  # used to store LCIA calculations
        self.LCIA_method = None

    def updateEcoinventVersion(self, key=None):
        # set database version (2 or 3)
        if key:
            self.database_version = 2 if bw2.Database(key[0]).load()[key].get('reference product', 'unknown') == 'unknown' else 3
        else:
            self.database_version = 2 if bw2.Database(self.currentActivity[0]).load()[self.currentActivity].get('reference product', 'unknown') == 'unknown' else 3

    def loadDatabase(self, db_name):
        self.db = bw2.Database(db_name)
        self.database = self.db.load()
        # self.currentActivity = None
        self.updateEcoinventVersion(self.db.random())  # random key as no activity has been selected at this stage

    def setNewCurrentActivity(self, key=None):
        # need to load new database in case the new activity is in another db...
        if not self.db:
            print "Need to load a database first"
        self.record_history()
        if key:
            print "activity requested:", bw2.Database(key[0]).load()[key]['name']  # self.database[key]["name"]
        else:
            print "activity requested:", key
        if key is None or key == "":
            key = self.db.random()
            print "new random activity key: ", self.database[key]["name"]
        self.currentActivity = key
        self.updateEcoinventVersion()

    def record_history(self):
        # self.history.append(self.currentActivity)
        if self.currentActivity:
            if self.history:
                if self.history != self.currentActivity:
                    self.history.append(self.currentActivity)
            else:
                self.history.append(self.currentActivity)

    def goBack(self):
        pass
        #     print "HISTORY:"
        # for key in self.lcaData.history:
        #     print key, self.lcaData.database[key]["name"]
        #
        # if self.lcaData.history:
        #     self.newActivity(self.lcaData.history.pop())
        # else:
        #     print "Cannot go further back."

    def getActivityData(self, key=None, values=None):
        if values:
            ds = values
        else:
            if not key:
                key = self.currentActivity
            ds = bw2.Database(key[0]).load()[key]
        try:
            #  amount does not work for ecoinvent 2.2 multioutput as co-products are not in exchanges
            amount = [exc.get('amount', '') for exc in ds['exchanges'] if exc['type'] == "production"][0]
        except IndexError:
            # print "Amount could not be determined. Perhaps this is a multi-output activity."
            amount = 0
        obj = {
            'name': ds['name'],
            'product': ds.get('reference product', ''),  # only in v3
            'location': ds.get('location', 'unknown'),
            'amount': amount,
            'unit': ds.get('unit', 'unknown'),
            'database': key[0] if key else 'unknown',
            'key': key if key else 'unknown',
            'key_type': 'activity',
        }
        return obj

    def get_exchanges(self, key=None, type=None, exchanges=None):
        if not exchanges:
            if not key:
                key = self.currentActivity
            exchanges = bw2.Database(key[0]).load()[key]["exchanges"]
        if not type:
            type = "technosphere"
        objs = []
        for exc in exchanges:
            if exc['type'] == type:
                ds = bw2.Database(exc['input'][0]).load()[exc['input']]
                objs.append({
                    'name': ds['name'],
                    'product': ds.get('reference product', ''),  # nur in v3
                    'location': ds.get('location', 'unknown'),
                    'amount': exc['amount'],
                    'unit': ds.get('unit', 'unknown'),
                    'database': exc['input'][0],
                    'key': exc['input'],
                    'key_type': 'activity',
                })
        objs.sort(key=lambda x: x['name'])
        return objs

    def get_downstream_exchanges(self, activity=None):
        """Get the exchanges that consume this activity's product"""
        if activity is None:
            activity = self.currentActivity
        db_name = activity[0]
        dbs = [db_name]
        excs = []

        for db in bw2.databases:
            if db_name in bw2.databases[db]['depends']:
                dbs.append(db)
        for db in dbs:
            for k, v in bw2.Database(db).load().iteritems():
                if k == activity:  # do nothing for this activity (but what if it has an inputs of itself??)
                    continue
                for exc in v.get('exchanges', []):
                    if activity == exc['input']:
                        if self.database_version == 2:
                            # unit = self.database[self.currentActivity]['unit']
                            unit = bw2.Database(self.currentActivity[0]).load()[self.currentActivity]['unit']
                        else:
                            unit = exc.get('unit', 'unknown')
                        excs.append({
                            'input': k,
                            'amount': exc['amount'],
                            'key': k,
                            'key_type': 'activity',
                            'name': v['name'],
                            'product': v.get('reference product',''),  # exc.get('name', 'unknown'),
                            'unit': unit,  # v3: exc.get('unit', 'unknown')
                            'database': k[0],
                            'location': v.get('location', 'unknown')  # self.database[k]['location']
                        })
        excs.sort(key=lambda x: x['name'])
        return excs

    def get_search_results(self, searchString=None):
        if searchString is None or searchString == "":
            print "Invalid search string"
        else:
            objs = []
            # querying: http://nbviewer.ipython.org/url/brightwaylca.org/tutorials/Searching-databases.ipynb
            results = self.db.query(bw2.Filter('name', 'has', searchString))
            for key in results:
                objs.append(self.getActivityData(key))
            objs.sort(key=lambda x: x['name'])
        return objs

    def getHistory(self):
        return [self.getActivityData(key) for key in self.history]

    def getDatabases(self):
        objs = []
        for db_name in bw2.databases.list:
            objs.append({
                'name': db_name,
                'activities': bw2.databases[db_name].get('number', 'unknown'),
                'dependencies': ", ".join(bw2.databases[db_name].get('depends', [])),
                'key': db_name,
                'key_type': 'database',
            })
        return objs

    def get_selectable_LCIA_methods(self, preselection=None):
        methods = [m for m in bw2.methods if len(m) == 3]  # consider only methods with three parts
        if preselection:
            for i, ps in enumerate(preselection):
                if ps:
                    methods = [m for m in methods if m[i] == ps]
        # get three parts individually as sets
        method_parts = [[m[i] for m in methods] for i in range(3)]
        method_parts = [sorted(set(p), key=lambda item: (int(item.partition(' ')[0])
                                   if item[0].isdigit() else float('inf'), item)) for p in method_parts]
        # set LCIA method if possible
        if len(methods) == 1:
            self.LCIA_method = methods[0]
            print "LCIA method set to "+str(self.LCIA_method)
        else:
            self.LCIA_method = None
        return methods, method_parts

    def lcia(self, key=None, amount=1.0, method=(u'IPCC 2007', u'climate change', u'GWP 100a')):
        # TODO add factorization / redo lci...
        if not key:
            key = self.currentActivity
        lca = bw2.LCA({key: amount}, method)
        lca.lci()
        lca.lcia()
        uuid_ = unicode(uuid.uuid4().urn[9:])
        lcia_data = {
            'key': key,
            'functional unit': amount,
            'method': method,
            'lca': lca,
            'score': lca.score,
            'top processes': self.pimp_contribution_analysis(ContributionAnalysis().annotated_top_processes(lca), lca.score),
            'top emissions': self.pimp_contribution_analysis(ContributionAnalysis().annotated_top_emissions(lca), lca.score),
            'uuid_': uuid_,
        }
        self.LCIA_calculations.update({uuid_: lcia_data})
        return uuid_

    def pimp_contribution_analysis(self, top_list, lca_score):
        pimped_CA = []
        for row in top_list:
            pimped_CA.append([row[0], 100*row[0]/lca_score, row[1]])
        return pimped_CA


# CREATE AND MODIFY ACTIVITIES

    def set_edit_activity(self, key):
        self.editActivity_key = key
        self.editActivity_values = bw2.Database(key[0]).load()[key]

    def add_exchange(self, key):
        ds = bw2.Database(key[0]).load()[key]
        exchange = {
            'input': key,
            'name': ds.get('reference product', '') or ds.get('name', ''),
            'amount': 1.0,
            'unit': ds.get('unit', ''),
            'type': "biosphere" if key in bw2.Database('biosphere').load().keys()
                                or key in bw2.Database('biosphere3').load().keys()
                                else "technosphere",
        }
        print "\nAdding Exchange: " + str(exchange)
        self.editActivity_values['exchanges'].append(exchange)

    def remove_exchange(self, key):
        for exc in self.editActivity_values['exchanges']:
            if exc['input'] == key:
                self.editActivity_values['exchanges'].remove(exc)

    def change_activity_value(self, value, type=None):
        if type == "name":
            self.editActivity_values['name'] = value
        elif type == "product":
            self.editActivity_values['reference product'] = value
        elif type == "unit":
            self.editActivity_values['unit'] = value
        elif type == "location":
            self.editActivity_values['location'] = value
        elif type == "amount":
            for e in self.editActivity_values['exchanges']:
                if e['type'] == "production":
                    e['amount'] = float(value)
        else:
            print "Unkown type: " + str(type)

    def change_exchange_value(self, key, value, type="amount"):
        for exc in self.editActivity_values['exchanges']:
            if exc['input'] == key:
                if type == "amount":
                    exc['amount'] = float(value)

    def save_activity_to_database(self, key, values, production_exchange_data=None):
        # first remove existing production exchange
        for exc in self.editActivity_values['exchanges']:
            if exc['type'] == "production":
                self.editActivity_values['exchanges'].remove(exc)
        # append new production exchange
        if production_exchange_data:
            values['exchanges'].append(production_exchange_data)
        db_name = key[0]
        db = bw2.Database(db_name)
        if db_name not in bw2.databases:
            db.register()
            data = {}
        else:
            data = db.load()
        data[key] = values
        db.write(recursive_str_to_unicode(data))
        db.process()
        print "saved %s to %s. (key: %s)" % (bw2.Database(key[0]).load()[key]['name'], db_name, str(key))

    def delete_activity(self, key):
        db_name = key[0]
        db = bw2.Database(db_name)
        data = db.load()
        del data[key]
        db.write(recursive_str_to_unicode(data))
        db.process()
        print "deleted activity: %s" % (str(key))

