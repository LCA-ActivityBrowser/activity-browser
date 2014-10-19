#!/usr/bin/env python
# -*- coding: utf-8 -*-

from processSubsystem import ProcessSubsystem
from utils import *
import json

class ProcessSubsystemCreator(BrowserStandardTasks):
    def __init__(self):
        self.pss_data = {'name': 'New Process Subsystem', 'outputs': [], 'chain': [], 'cuts': []}
        self.newProcessSubsystem(self.pss_data)
        self.name_map = {}  # remembers key: "name" information during a session

    def update_pss(self):
        self.pss = ProcessSubsystem(**self.pss_data)
        self.pss_data = self.pss.pss_data
        self.apply_name_map()
        # TODO: add custom information if available in name_map
        print "\nPSS DATA:"
        print self.pss.pss_data
        print "INTERNAL EDGES (+CUTS):"
        print self.pss.internal_edges_with_cuts

    def apply_name_map(self):
        # name map is applied only if a default name is present
        # otherwise custom names from other PSS might be overwritten
        for o in self.pss_data['outputs']:
            if o[0] in self.name_map and o[1] == "Unspecified Output":
                self.set_output_name(o[0], self.name_map[o[0]], update=False)
        for o in self.pss_data['cuts']:
            if o[0] in self.name_map and o[2] == "Unspecified Input":
                self.set_cut_name(o[0], self.name_map[o[0]], update=False)

    def newProcessSubsystem(self, pss_data=None):
        if not pss_data:
            self.pss_data = {'name': 'New Process Subsystem', 'outputs': [], 'chain': [], 'cuts': []}
            self.pss = ProcessSubsystem(**self.pss_data)
        else:  # load with try, except
            self.pss_data = pss_data
            self.pss = ProcessSubsystem(**pss_data)

    def load_pss(self, pss):
        self.pss_data = pss
        self.update_pss()

    def add_to_chain(self, key):
        self.pss_data['chain'].append(key)
        self.update_pss()

    def delete_from_chain(self, key):
        if not self.pss.internal_edges_with_cuts:  # top processes (no edges yet)
            self.pss_data['chain'].remove(key)
            print "Removed key from chain: " + str(key)
            self.update_pss()
        else:  # there are already edges
            parents, children, value = zip(*self.pss.internal_edges_with_cuts)
            if key in children:
                print "\nCannot remove activity as as other activities still link to it."
            elif key in parents:  # delete from chain
                self.pss_data['chain'].remove(key)
                print "Removed key from chain: " + str(key)
                self.update_pss()
            else:
                print "WARNING: Key not in chain. Key: " + self.getActivityData(key)['name']

    def add_cut(self, from_key):
        # TODO: add custom information if available in name_map
        if not self.pss.internal_edges_with_cuts:
            print "Nothing to cut from."
        else:
            parents, children, value = zip(*self.pss.internal_edges_with_cuts)
            if from_key in children:
                print "Cannot add cut. Activity is linked to by another activity."
            else:
                new_cuts = [(from_key, pcv[1], "Unspecified Input") for pcv in self.pss.internal_edges_with_cuts if from_key == pcv[0]]
                self.pss_data['cuts'] = list(set(self.pss_data['cuts'] + new_cuts))
                print "cutting: " + str(new_cuts)
                self.update_pss()

    def delete_cut(self, from_key):
        print "FROM KEY...."
        print from_key
        for cut in self.pss_data['cuts']:
            if from_key == cut[0]:
                self.pss_data['cuts'].remove(cut)
        self.update_pss()
        # add deleted cut to chain again...
        self.add_to_chain(from_key)

    def set_pss_name(self, name):
        self.pss_data['name'] = name
        self.update_pss()

    def set_output_name(self, key, name, update=True):
        for i, o in enumerate(self.pss_data['outputs']):
            if o[0] == key:
                self.pss_data['outputs'][i] = tuple([o[0], name, o[2]])
        if update:
            self.name_map.update({key: name})
            self.update_pss()

    def set_output_quantity(self, key, quantity):
        for i, o in enumerate(self.pss_data['outputs']):
            if o[0] == key:
                self.pss_data['outputs'][i] = tuple([o[0], o[1], quantity])
        self.update_pss()

    def set_cut_name(self, key, name, update=True):
        for i, o in enumerate(self.pss_data['cuts']):
            if o[0] == key:
                self.pss_data['cuts'][i] = tuple([o[0], o[1], name])
        if update:
            self.name_map.update({key: name})
            self.update_pss()

    # VISUALIZATION

    def getGraphData(self):
        graph_data = []
        for edge in self.pss.internal_edges_with_cuts:
            graph_data.append({
                'source': self.getActivityData(edge[0])['name'],
                'target': self.getActivityData(edge[1])['name'],
                'type': "suit"
            })
        # append connection to Process Subsystem
        for sa in self.pss.scaling_activities:
            graph_data.append({
                'source': self.getActivityData(sa)['name'],
                'target': self.pss.name,
                'type': "suit"
            })
        return graph_data

    def getTreeData(self):
        # TODO: rewrite using ProcessSubsystem? To apply: self.internal_scaled_edges_with_cuts
        def get_nodes(node):
            d = {}
            if node == self.pss.name:
                d['name'] = node
            else:
                d['name'] = self.getActivityData(node)['name']
            parents = get_parents(node)
            if parents:
                d['children'] = [get_nodes(parent) for parent in parents]
            return d

        def get_parents(node):
            return [x[0] for x in parents_children if x[1] == node]

        if not self.pss.chain:
            return []
        tree_data = []
        parents_children = [e[:2] for e in self.pss.internal_edges_with_cuts]  # not using amount yet
        head_nodes = self.pss.scaling_activities
        for head in head_nodes:
            parents_children.append((head, self.pss.name))

        tree_data.append(get_nodes(self.pss.name))
        return tree_data

    def getHumanReadiblePSS(self, pss):
        print pss

        def getData(key):
            try:
                ad = self.getActivityData(key)
                return (ad['database'], ad['product'], ad['name'], ad['location'])
            except:
                return key

        outputs = [(getData(o[0]), o[1]) for o in pss['outputs']]
        chain = [getData(o) for o in pss['chain']]
        cuts = [(getData(o[0]), getData(o[1]), o[2]) for o in pss['cuts']]
        # edges = [(getData(o[0]), getData(o[1])) for o in pss['edges']]
        pss_HR = {
            'name': pss['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
            # 'edges': edges,
        }
        print "\nPSS (HUMAN READIBLE):"
        print pss_HR
        return pss_HR

    def printEdgesToConsole(self, edges_data, message=None):
        if message:
            print message
        for i, pc in enumerate(edges_data):
            if self.custom_data['name'] in pc:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+pc[1]
            else:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+self.getActivityData(pc[1])['name']
