#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *
import json

class ProcessSubsystemCreator(BrowserStandardTasks):
    def __init__(self):
        self.parents_children = []  # flat: [(parent, child),...]
        self.outputs = []  # child keys
        self.chain = []  # unique chain item keys
        self.cuts = []  # key tuples (parent, child)
        self.custom_data = {
            'name': 'Default Process Subsystem',
            'output names': {},  # map activity key to *name*
            'output quantities': {},  # map activity key to *amount*
            'cut names': {},  # map activity key to *name*
        }
        self.pss = {}
        self.tree_data = []  # hierarchical
        self.graph_data = []  # source --> target

    def update(self):
        if not self.parents_children:
            self.outputs, self.chain, self.cuts = [], [], []
        else:
            # outputs
            self.outputs = self.getHeads()
            # chain
            parents, children = zip(*self.parents_children)
            self.chain = list(set(parents+children))
            # cuts
            if self.cuts:
                # remove false cuts (e.g. previously a cut, but now another parent node was added)
                for false_cut in [c for c in self.cuts if c[0] in children]:
                    self.cuts.remove(false_cut)
                    print "Removed cut (new parent node was added that links to this cut): "+str(false_cut)
        # pss
        self.pss = self.format_data_as_pss()
        # D3
        self.graph_data = self.getGraphData()
        self.tree_data = self.getTreeData()

    def getHeads(self):
        if self.parents_children:
            parents, children = zip(*self.parents_children)
            return list(set([c for c in children if c not in parents]))
        else:
            return []

    def newProcessSubsystem(self):
        self.parents_children, self.tree_data, self.graph_data = [], [], []
        self.update()

    def loadPSS(self, pss):
        print "Loading PSS:" + pss['name']
        # clear existing data
        self.newProcessSubsystem()
        # load and update new data (outputs, chain, cuts are determined from the edges)
        self.parents_children = pss['edges'][:]  # TODO? get edges from ProcessSubsystem self.internal_edges_with_cuts
        # load custom data
        self.custom_data['name'] = pss['name']
        for o in pss['outputs']:
            self.custom_data['output names'].update({o[0]: o[1]})
            self.custom_data['output quantities'].update({o[0]: o[2]})
        for c in pss['cuts']:
            self.cuts.append((c[0], c[1]))
            self.custom_data['cut names'].update({c[0]: c[2]})
        self.update()

    def addProcess(self, parent_key, child_key):
        if (parent_key, child_key) not in self.parents_children:
            self.parents_children.append((parent_key, child_key))
        self.update()

    def deleteProcessFromChain(self, key):
        self.printEdgesToConsole(self.parents_children, "Chain before delete:")
        parents, children = zip(*self.parents_children)
        if key in children:
            print "\nCannot remove activity as as other activities still link to it."
        elif key in parents:  # delete from chain
            for pc in self.parents_children:
                if key in pc:
                    self.parents_children.remove(pc)
            self.update()
            self.printEdgesToConsole(self.parents_children, "Chain after removal:")
        else:
            print "WARNING: Key not in chain. Key: " + self.getActivityData(key)['name']

    def addCut(self, from_key):
        parents, children = zip(*self.parents_children)
        if from_key in children:
            print "Cannot add cut. Activity is linked to by another activity."
        else:
            self.cuts = list(set(self.cuts + [pc for pc in self.parents_children if from_key == pc[0]]))
            self.update()

    def deleteCut(self, from_key):
        for cut in self.cuts:
            if from_key == cut[0]:
                self.cuts.remove(cut)
                self.update()

    def set_PSS_name(self, name):
        self.custom_data['name'] = name
        self.update()

    def setOutputName(self, key, name):
        self.custom_data['output names'].update({key: name})
        self.update()

    def setOutputQuantity(self, key, text):
        self.custom_data['output quantities'].update({key: text})
        self.update()

    def setCutName(self, key, name):
        self.custom_data['cut names'].update({key: name})
        self.update()

    def format_data_as_pss(self):
        outputs = []
        for i, key in enumerate(self.outputs):
            name = self.custom_data['output names'][key] if key in self.custom_data['output names'] else 'Output '+str(i)
            quantity = float(self.custom_data['output quantities'][key]) if key in self.custom_data['output quantities'] else 1.0
            outputs.append((key, name, quantity))
        # self.chain elements contain also cut parents.
        # They need to be removed for the ProcessSubsystem as this leads to wrong LCA results.
        chain_without_cuts = [key for key in self.chain if not key in [cut[0] for cut in self.cuts]]
        cuts = []
        for i, cut in enumerate(self.cuts):
            parent, child = cut[0], cut[1]
            name = self.custom_data['cut names'][parent] if parent in self.custom_data['cut names'] else 'Cut '+str(i)
            cuts.append((parent, child, name))
        pss = {
            'name': self.custom_data['name'],
            'outputs': outputs,
            'chain': chain_without_cuts,
            'cuts': cuts,
            'edges': self.parents_children,
        }
        return pss

    # VISUALIZATION

    def getGraphData(self):
        graph_data = []
        for pc in self.parents_children:
            graph_data.append({
                'source': self.getActivityData(pc[0])['name'],
                'target': self.getActivityData(pc[1])['name'],
                'type': "suit"
            })
        # append connection to Process Subsystem
        for head in self.getHeads():
            graph_data.append({
                'source': self.getActivityData(head)['name'],
                'target': self.custom_data['name'],
                'type': "suit"
            })
        return graph_data

    def getTreeData(self):
        # TODO: rewrite using ProcessSubsystem? To apply: self.internal_scaled_edges_with_cuts
        if not self.parents_children:
            return []
        def get_nodes(node):
            d = {}
            if node == self.custom_data['name']:
                d['name'] = node
            else:
                d['name'] = self.getActivityData(node)['name']
            parents = get_parents(node)
            if parents:
                d['children'] = [get_nodes(parent) for parent in parents]
            return d
        def get_parents(node):
            return [x[0] for x in parents_children if x[1] == node]

        parents_children = self.parents_children[:]  # mutable type, therefore needs slicing
        head_nodes = self.getHeads()
        for head in head_nodes:
            parents_children.append((head, self.custom_data['name']))
        tree_data = []
        tree_data.append(get_nodes(self.custom_data['name']))
        return tree_data

    def printEdgesToConsole(self, edges_data, message=None):
        if message:
            print message
        for i, pc in enumerate(edges_data):
            if self.custom_data['name'] in pc:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+pc[1]
            else:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+self.getActivityData(pc[1])['name']

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
        edges = [(getData(o[0]), getData(o[1])) for o in pss['edges']]
        pss_HR = {
            'name': pss['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
            'edges': edges,
        }
        print "\nPSS (HUMAN READIBLE):"
        print pss_HR
        return pss_HR

# TODO: remove?
    def format_data_as_pss_dagre(self):
        SP = {}
        outputs = []
        for i, key in enumerate(self.process_subsystem['outputs']):
            name = self.custom_data['output names'][key] if key in self.custom_data['output names'] else 'Output'+str(i)
            quantity = float(self.custom_data['output quantities'][key]) if key in self.custom_data['output quantities'] else 1.0
            outputs.append((self.getActivityData(key)['name'], name, quantity))
        chain = []
        for key in self.process_subsystem['chain']:
            if key != self.custom_data['name']:  # only real keys, not the head
                chain.append(self.getActivityData(key)['name'])
        cuts = []
        for i, cut in enumerate(self.process_subsystem['cuts']):
            parent, child = cut[0], cut[1]
            name = self.custom_data['cut names'][parent] if parent in self.custom_data['cut names'] else 'Cut'+str(i)
            cuts.append((self.getActivityData(parent)['name'], self.getActivityData(child)['name'], name))

        SP.update({
            'name': self.custom_data['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
        })
        print "\nPSS as SP (HUMAN READIBLE):"
        print SP
        print json.dumps(SP, indent=2)
        self.SP_dagre = SP
