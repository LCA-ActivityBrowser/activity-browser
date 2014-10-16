#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui
import brightway2 as bw2

class MyTableQWidgetItem(QtGui.QTableWidgetItem):
    def __init__(self, parent=None):
        super(MyTableQWidgetItem, self).__init__(parent)
        self.activity_or_database_key = None
        self.key_type = None
        # self.setFlags(QtCore.Qt.ItemIsEnabled)
        # self.setFlags(QtCore.Qt.ItemIsSelectable)
        # self.setFlags(QtCore.Qt.ItemIsEditable)

class MyStandardItem(QtGui.QStandardItem):
    def __init__(self, parent=None):
        super(MyStandardItem, self).__init__(parent)
        self.activity_or_database_key = None
        self.key_type = None
        self.setEditable(False)

class HelperMethods(object):
    def __init__(self):
        pass

    def update_table(self, table, data, keys):
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
            table.blockSignals(True)
            table.setRowCount(len(data))
            table.setColumnCount(len(keys))
            table.setHorizontalHeaderLabels(keys)
            for i, d in enumerate(data):
                for j in range(len(keys)):
                    mqtwi = MyTableQWidgetItem(str(d[keys[j]]))
                    mqtwi.activity_or_database_key = d["key"]
                    mqtwi.key_type = d["key_type"]
                    table.setItem(i, j, mqtwi)
            if 'quantity' in keys:
                table.setEditTriggers(QtGui.QTableWidget.DoubleClicked)
            else:
                table.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.resizeColumnsToContents()
            table.resizeRowsToContents()
            table.blockSignals(False)
            table.setSortingEnabled(True)
        return table

    def update_normal_table(self, table, data, keys):
        if not data:
            table.setRowCount(0)
            return table
        else:
            table.blockSignals(True)
            table.setRowCount(len(data))
            table.setColumnCount(len(keys))
            table.setHorizontalHeaderLabels(keys)
            for i, d in enumerate(data):
                for j in range(len(keys)):
                    qtwi = QtGui.QTableWidgetItem(str(d[keys[j]]))
                    table.setItem(i, j, qtwi)
            table.setAlternatingRowColors(True)
            table.resizeColumnsToContents()
            table.resizeRowsToContents()
            table.blockSignals(False)
            table.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
            table.setSortingEnabled(True)
        return table

class Styles(object):
    def __init__(self):
        # BIG FONT
        self.font_big = QtGui.QFont()
        self.font_big.setPointSize(12)
        self.font_big.setBold(True)


class BrowserStandardTasks(object):
    def __init__(self):
        self.history = []
        self.currentActivity = None
        self.db = None
        self.database = None
        self.database_version = None

    def updateEcoinventVersion(self, key=None):
        # set database version (2 or 3)
        if key:
            self.database_version = 2 if bw2.Database(key[0]).load()[key].get('linking', 'unknown') == 'unknown' else 3
        else:
            self.database_version = 2 if bw2.Database(self.currentActivity[0]).load()[self.currentActivity].get('linking', 'unknown') == 'unknown' else 3

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

    def getActivityData(self, key=None):
        if not key:
            # ds = self.database[self.currentActivity]
            key = self.currentActivity
        ds = bw2.Database(key[0]).load()[key]
        try:
            #  amount does not work for ecoinvent 2.2 multioutput as co-products are not in exchanges
            amount = [exc.get('amount', '') for exc in ds['exchanges'] if exc['type'] == "production"][0]
        except IndexError:
            print "Amount could not be determined. Perhaps this is a multi-output activity."
            amount = 0
        obj = {
            'name': ds['name'],
            'product': ds.get('reference product', ''),  # nur in v3
            'location': ds.get('location', 'unknown'),
            'amount': amount,
            'unit': ds.get('unit', 'unknown'),
            'database': key[0],
            'key': key,
            'key_type': 'activity',
        }
        return obj

    def get_exchanges(self, type=None):
        if not type:
            type = "technosphere"
        objs = []
        # for exc in self.database[self.currentActivity]["exchanges"]:
        for exc in bw2.Database(self.currentActivity[0]).load()[self.currentActivity]["exchanges"]:
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
                'dependencies': bw2.databases[db_name].get('depends', 'unknown'),
                'key': db_name,
                'key_type': 'database',
            })
        return objs

