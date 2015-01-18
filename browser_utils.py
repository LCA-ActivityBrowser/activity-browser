#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtGui, QtCore
import brightway2 as bw2
from bw2analyzer import ContributionAnalysis
from bw2analyzer import SerializedLCAReport
from bw2data.utils import recursive_str_to_unicode
import numpy as np
import uuid
from copy import deepcopy
import multiprocessing
import xlsxwriter
import style

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

    def update_table(self, table, data, keys, edit_keys=None, bold=False):
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
                    # Color
                    mqtwi.setTextColor(QtGui.QColor(*style.colors_table_current_activity.get(
                        keys[j], (0, 0, 0))))
                    # Font
                    if bold:
                        font = QtGui.QFont()
                        font.setBold(True)
                        font.setPointSize(9)
                        mqtwi.setFont(font)
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

    def get_table_item(self, table, row_num, col_name):
        headercount = table.columnCount()
        for i in range(0, headercount):
            headertext = table.horizontalHeaderItem(i).text()
            if col_name == headertext:
                matchcol = i
                break
        return table.item(row_num, matchcol)

    def is_int(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def is_float(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def find_nearest(self, array, value):
        index = (np.abs(array-value)).argmin()
        return index

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

    LCIA_METHOD = (u'IPCC 2007', u'climate change', u'GWP 100a')

    def __init__(self):
        self.currentActivity = None
        self.db = None
        self.database = None
        self.database_version = None

        # Navigation
        self.history = set()
        self.last_activity = None
        self.backward_options = []
        self.forward_options = []

        # LCA data
        self.LCIA_calculations = {}  # used to store LCIA calculations
        self.LCIA_calculations_mc = {}


    def updateEcoinventVersion(self, key=None):
        # set database version (2 or 3)
        if key:
            self.database_version = 2 if bw2.Database(key[0]).load()[key].get('reference product', 'unknown') == 'unknown' else 3
        else:
            self.database_version = 2 if bw2.Database(self.currentActivity[0]).load()[self.currentActivity].get('reference product', 'unknown') == 'unknown' else 3

    def loadDatabase(self, db_name):
        self.db = bw2.Database(db_name)
        self.database = self.db.load()
        self.updateEcoinventVersion(self.db.random())  # random key as no activity has been selected at this stage

    def setNewCurrentActivity(self, key=None, record=True):
        # need to load new database in case the new activity is in another db...
        if not self.db:
            print "Need to load a database first"
            return
        if key is None or key == "":
            key = self.db.random()
            print "random activity key"
        print "\nNew current activity: ", bw2.Database(key[0]).load()[key].get('name', '')
        last_activity = self.currentActivity
        self.currentActivity = key
        self.updateEcoinventVersion()
        self.history.add(self.currentActivity)
        if record and last_activity:
            self.backward_options.append(last_activity)
        # reset forward options if gone forward and new current activity is not last forward option
        if record and self.forward_options:
            if self.currentActivity != self.forward_options.pop():
                self.forward_options = []

        # print "\nLast activity:", self.getActivityData(self.last_activity)['name']  # wrong first time as None --> getAD returns self.current...
        # print "History:", [self.getActivityData(key)['name'] for key in self.history]
        # print "Current activity:", self.getActivityData(self.currentActivity)['name']
        # print "Backward options:", [self.getActivityData(key)['name'] for key in self.backward_options]
        # print "Forward options:", [self.getActivityData(key)['name'] for key in self.forward_options]
        # print

    def go_backward(self):
        if self.backward_options:
            self.forward_options.append(self.currentActivity)
            self.setNewCurrentActivity(self.backward_options.pop(), record=False)

    def go_forward(self):
        if self.forward_options:
            self.backward_options.append(self.currentActivity)
            self.setNewCurrentActivity(self.forward_options.pop(), record=False)

    def getActivityData(self, key=None, values=None):
        if values:
            ds = values
        else:
            if not key:
                key = self.currentActivity
            ds = bw2.Database(key[0]).load()[key]
        try:
            #  amount does not work for ecoinvent 2.2 multioutput as co-products are not in exchanges
            amount = [exc.get('amount', '') for exc in ds.get('exchanges', []) if exc.get('type', None) == "production"][0]
        except IndexError:
            # print "Amount could not be determined. Perhaps this is a multi-output activity."
            amount = 0
        obj = {
            'name': ds.get('name', ''),
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
            exchanges = bw2.Database(key[0]).load()[key].get("exchanges", [])
        if not type:
            type = "technosphere"
        objs = []
        for exc in exchanges:
            if exc['type'] == type:
                ds = bw2.Database(exc.get('input', None)[0]).load()[exc.get('input', None)]
                objs.append({
                    'name': ds.get('name', ''),
                    'product': ds.get('reference product', ''),  # nur in v3
                    'location': ds.get('location', 'unknown'),
                    'amount': exc['amount'],
                    'unit': ds.get('unit', 'unknown'),
                    'database': exc.get('input', 'unknown')[0],
                    'key': exc.get('input', 'unknown'),
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
                            unit = bw2.Database(self.currentActivity[0]).load()[self.currentActivity].get('unit', 'unknown')
                        else:
                            unit = exc.get('unit', 'unknown')
                        excs.append({
                            'input': k,
                            'amount': exc.get('amount', 'unknown'),
                            'key': k,
                            'key_type': 'activity',
                            'name': v.get('name', ''),
                            'product': v.get('reference product', ''),  # exc.get('name', 'unknown'),
                            'unit': unit,  # v3: exc.get('unit', 'unknown')
                            'database': k[0],
                            'location': v.get('location', 'unknown')  # self.database[k]['location']
                        })
        excs.sort(key=lambda x: x['name'])
        return excs

    def search_activities(self, searchString=None):
        """
        Returns a list of dictionaries with activity data sorted by activity name
        for those activities that contain the search string in their name.
        Returns all keys in the database if no search string is supplied.
        :param searchString:
        :return:
        """
        objs = []
        if self.db:
            if searchString == "":
                objs = [self.getActivityData(key) for key in self.database.keys()]
                objs.sort(key=lambda x: x['name'])
            else:
                # querying: http://nbviewer.ipython.org/url/brightwaylca.org/tutorials/Searching-databases.ipynb
                results = self.db.query(bw2.Filter('name', 'has', searchString))
                for key in results:
                    objs.append(self.getActivityData(key))
                objs.sort(key=lambda x: x['name'])
        return objs

    def multi_search_activities(self, searchString1='', searchString2=''):
        """
        Returns a list of dictionaries with activity data sorted by activity name
        for those activities that contain the search string in their name.
        Returns all keys in the database if no search string is supplied.
        :param searchString1:
        :return:
        """
        if self.db:
            if not searchString1 and not searchString2:
                objs = [self.getActivityData(key) for key in self.database.keys()]
            elif searchString1 and searchString2:
                objs = [self.getActivityData(key) for key in self.database.keys()
                        if (searchString1 in self.database[key].get('name', '')
                            or searchString1 in self.database[key].get('reference product', ''))
                        and (searchString2 in self.database[key].get('name', '')
                             or searchString2 in self.database[key].get('reference product', ''))]
            else:
                searchstring = searchString1 or searchString2
                objs = [self.getActivityData(key) for key in self.database.keys()
                        if searchstring in self.database[key].get('name', '')
                        or searchstring in self.database[key].get('reference product', '')]
            objs.sort(key=lambda x: x['name'])
            return objs

    def search_methods(self, searchString=None, length=None, does_not_contain=None):
        """
        Returns all methods for which the search string is part of.
        Returns all methods if no search string is specified.
        If length is provided, results are reduced to those that have
        a length of x, i.e. x parts in the method tuple.
        :param searchString:
        :return:
        """
        output = []
        if searchString is None or searchString == "":
            output = bw2.methods
        else:
            for method in bw2.methods:
                for part in method:
                    if searchString in part:
                        output.append(method)
        if length:
            output = [out for out in output if len(out) == length]
        if does_not_contain:
            output = [out for out in output if does_not_contain not in [part for part in out]]
        return output

    def getHistory(self):
        return [self.getActivityData(key) for key in self.history]

    def list_databases(self):
        return bw2.databases.list

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
            BrowserStandardTasks.LCIA_METHOD = methods[0]
            print "LCIA method set to "+str(methods[0])
        else:
            BrowserStandardTasks.LCIA_METHOD = None
        return methods, method_parts

# LCA

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
            'top processes': ContributionAnalysis().annotated_top_processes(lca, names=False),  # self.pimp_contribution_analysis(ContributionAnalysis().annotated_top_processes(lca, names=False), lca.score),
            'top emissions': ContributionAnalysis().annotated_top_emissions(lca, names=False),  # self.pimp_contribution_analysis(ContributionAnalysis().annotated_top_emissions(lca, names=False), lca.score),
            'uuid_': uuid_,
        }
        self.LCIA_calculations.update({uuid_: lcia_data})
        return uuid_

    def monte_carlo_lcia(self, key=None, amount=1.0, method=(u'IPCC 2007', u'climate change', u'GWP 100a'),
                iterations=500, cpu_count=1, uuid_=None):
        if not key:
            key = self.currentActivity
        mc_data = SerializedLCAReport({key: amount}, method, iterations, cpu_count).get_monte_carlo()
        if uuid_:
            mc_data['iterations'] = iterations
            self.LCIA_calculations_mc.update({uuid_: mc_data})
        return mc_data

    def multi_lca(self, activities, methods):
        """
        Performs LCA for multiple activities and LCIA methods on multiple CPU cores.
        :param activities:
        :param methods:
        :return:
        """
        # TO BE APPLIED AS SOON AS .GEOMAPPING BRIGHTWAY PROBLEM IS SOLVED...

        # def helper_function(activities, method):
        #     output = np.zeros((len(activities),))
        #     # Create LCA object which will do all calculating
        #     lca = bw2.LCA({activities[0]: 1}, method=method)
        #     # Keep the LU factorized matrices for faster calculations
        #     # Only need to do this once for all activities
        #     lca.lci(factorize=True)
        #     lca.lcia()
        #     for index, activity_name in enumerate(activities):
        #         # Skip ecoinvent processes that have no exchanges (their score is 0)
        #         if bw2.mapping[activity_name] not in lca.technosphere_dict:
        #             continue
        #         lca.redo_lci({activity_name: 1})
        #         lca.lcia_calculation()
        #         output[index] = lca.score
        #     return (method, output)
        #
        # activities = activities
        # methods = methods
        # num_methods = len(methods)
        # num_processes = len(activities)
        #
        # pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        # jobs = [pool.apply_async(helper_function, (activities, method))
        #         for method in methods]
        # pool.close()
        # pool.join()  # Blocks until calculation is finished
        # results = dict([job.get() for job in jobs])
        #
        # # Create array to store calculated results
        # lca_scores = np.zeros((num_processes, num_methods), dtype=np.float32)
        #
        # for index, method in enumerate(methods):
        #     lca_scores[:, index] = results[method]
        #
        # return lca_scores, methods, activities

        # MEANWHILE USING THIS METHOD:
        lca_scores = np.zeros((len(activities), len(methods)))
        # Create LCA object which will do all calculating
        lca = bw2.LCA({activities[0]: 1}, method=methods[0])
        # Keep the LU factorized matrices for faster calculations
        # Only need to do this once for all activities
        lca.lci(factorize=True)
        lca.lcia()
        for index_a, activity in enumerate(activities):
            # Skip ecoinvent processes that have no exchanges (their score is 0)
            if bw2.mapping[activity] not in lca.technosphere_dict:
                continue
            lcia_scores_for_this_process = np.zeros((len(methods)))
            for index_m, method in enumerate(methods):
                lca.redo_lci({activity: 1})
                lca.method = method
                lca.lcia()
                lcia_scores_for_this_process[index_m] = lca.score
            lca_scores[index_a, :] = lcia_scores_for_this_process
        return lca_scores, methods, activities

# CREATE AND MODIFY DATABASES

    def add_database(self, name, data={}):
        db = bw2.Database(name)
        db.validate(data)
        if name not in bw2.databases:
            db.register()
            db.write(data)
            db.process()
            db.load()

    def delete_database(self, name):
        del bw2.databases[name]

# CREATE AND MODIFY ACTIVITIES

    def set_edit_activity(self, key):
        """
        Makes a copy of the original activity using deepcopy.
        :param key:
        :return:
        """
        self.editActivity_key = key
        self.editActivity_values = deepcopy(bw2.Database(key[0]).load()[key])

    def add_exchange(self, key):
        ds = deepcopy(bw2.Database(key[0]).load()[key])
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

# MODULE FUNCTIONS


def export_matrix_to_excel(row_names, col_names, matrix, filepath='export.xlsx', sheetname='Export'):
    workbook = xlsxwriter.Workbook(filepath)
    ws = workbook.add_worksheet(sheetname)
    # formatting
    # border
    format_border = workbook.add_format()
    format_border.set_border(1)
    format_border.set_font_size(9)
    # border + text wrap
    format_border_text_wrap = workbook.add_format()
    format_border_text_wrap.set_text_wrap()
    format_border_text_wrap.set_border(1)
    format_border_text_wrap.set_font_size(9)
    # set column width
    ws.set_column(0, 1, width=15, cell_format=None)
    ws.set_column(1, 50, width=9, cell_format=None)
    # write data
    for i, p in enumerate(col_names):  # process names
        ws.write(0, i+1, p, format_border_text_wrap)
    for i, p in enumerate(row_names):  # product names
        ws.write(i+1, 0, p, format_border)
    for i, row in enumerate(range(matrix.shape[0])):  # matrix
        ws.write_row(i+1, 1, matrix[i, :], format_border)
    workbook.close()