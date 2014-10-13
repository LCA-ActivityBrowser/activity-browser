#!/usr/bin/env python
# -*- coding: utf-8 -*-

from standardTasks import BrowserStandardTasks
import json

class ProcessSubsystem(BrowserStandardTasks):
    def __init__(self):
        self.parents_children = []  # flat: [(parent, child),...]
        self.tree_data = []  # hierarchical
        self.graph_data = []  # source --> target
        self.process_subsystem = {
            'outputs': [],  # parent keys
            'chain': [],  # unique chain item keys
            'cuts': [],  # key tuples (parent, child)
        }
        self.custom_data = {
            'name': 'Default Process Subsystem',
            'output names': {},  # dict that map activity key to *name*
            'output quantities': {},  # dict that map activity key to *amount*
            'cut names': {},  # dict that map activity key to *name*
        }
        self.pss = {}

    def newProcessSubsystem(self):
        self.parents_children = []
        self.tree_data = []
        self.graph_data = []
        self.updateData()

    def loadPSS(self, pss):
        self.newProcessSubsystem()  # clear existing data
        self.custom_data['name'] = pss['name']
        for o in pss['outputs']:
            self.process_subsystem['outputs'].append(o[0])
            self.custom_data['output names'].update({o[0]: o[1]})
            self.custom_data['output quantities'].update({o[0]: o[2]})
        for c in pss['chain']:
            self.process_subsystem['chain'].append(c)
        for c in pss['cuts']:
            self.process_subsystem['cuts'].append((c[0], c[1]))
            self.custom_data['cut names'].update({c[0]: c[2]})
        self.parents_children = pss['edges']
        self.updateData()
        # print self.process_subsystem
        # print self.custom_data

    def addProcess(self, parent_key, child_key):
        new_edge = (parent_key, child_key)
        if new_edge not in self.parents_children:
            self.parents_children.append((parent_key, child_key))
        self.updateData()

    def linkToProcessSubsystemHead(self, key):
        # links a node to current Process Subsystem, IF that node is a head (has no further downstream processes)
        parents, children = zip(*self.parents_children)
        if not key in parents:
            self.parents_children.append((key, self.custom_data['name']))
            self.process_subsystem['outputs'].append(key)
            self.updateData()
        else:
            print "Cannot be defined as input to the Process Subsystem Head. " \
                  "Perhaps it is not a head of the current system."

    def deleteProcessFromOutputs(self, key):
        if not self.parents_children:
            print "No outputs to be removed."
        else:
            self.parents_children.remove((key, self.custom_data['name']))
            print "Removed output: "+self.getActivityData(key)['name']
            self.updateData()

    def deleteProcessFromChain(self, key):
        if self.parents_children:
            self.printEdgesToConsole(self.parents_children, "Chain before delete:")
            parents, children = zip(*self.parents_children)
            if key in children:
                print "\nCannot remove activity as as other activities still link to it."
            elif key in parents:  # delete from chain
                for pc in self.parents_children:
                    if key in pc:
                        self.parents_children.remove(pc)
                self.printEdgesToConsole(self.parents_children, "Chain after edge removal:")
                self.updateData()
            else:
                print "WARNING: Key not in chain. Key: " + self.getActivityData(key)['name']

    def set_PSS_name(self, name):
        print "New PSS name: "+name
        # first need to update self.parents_children with new name
        old_name = self.custom_data['name']
        for pc in self.parents_children:
            if old_name in pc:
                new_pc = (pc[0], name)
                self.parents_children.remove(pc)
                self.parents_children.append(new_pc)
        self.custom_data['name'] = name
        self.updateData()

    def setOutputName(self, key, name):
        self.custom_data['output names'].update({
            key: name
        })
        print "\nCustom Data:"
        print self.custom_data

    def setOutputQuantity(self, key, text):
        self.custom_data['output quantities'].update({
            key: text
        })
        print "\nCustom Data:"
        print self.custom_data

    def setCutName(self, key, name):
        # cut names only get added, but not removed right now when process is removed from PSS
        # advantage: custom names are already defined, when process is added again;
        # disadvantage: this might then not make sense
        self.custom_data['cut names'].update({
            key: name
        })
        print "UPDATED CUT NAME: " + name

    def updateData(self):
        # PSS
        self.updateOutputs()
        self.updateChain()
        self.updateCuts()
        # D3
        self.graph_data = self.getGraphData()
        self.tree_data = self.getTreeData()
        # Console output
        self.printEdgesToConsole(self.parents_children, "\nList of parents / children:")
        self.printEdgesToConsole(self.process_subsystem['cuts'], "\nCuts:")
        # print self.process_subsystem['cuts']
        # print "Tree Data:"
        # print json.dumps(self.tree_data, indent=2)

    def updateOutputs(self):
        if not self.parents_children:
            self.process_subsystem['outputs'] = []
        else:
            outputs = []
            for pc in self.parents_children:
                if pc[1] == self.custom_data['name']:
                    outputs.append(pc[0])
            self.process_subsystem['outputs'] = outputs

    def updateChain(self):
        if not self.parents_children:
            self.process_subsystem['chain'] = []
        else:
            parents, children = zip(*self.parents_children)
            uniqueKeys = set(parents+children)
            self.process_subsystem['chain'] = list(uniqueKeys)

    def updateCuts(self):
        if not self.parents_children:
            # print "from updateCuts(): No Chain."
            self.process_subsystem['cuts'] = []
        else:
            parents, children = zip(*self.parents_children)
            cuts_from = [x for x in parents if x not in children]
            cuts_from_to = []
            for cut_from in cuts_from:
                for pc in self.parents_children:
                    if cut_from in pc:
                        cuts_from_to.append(pc)
            self.process_subsystem['cuts'] = cuts_from_to

    def getGraphData(self):
        # TODO: move to GUI / visualization
        graph_data = []
        for pc in self.parents_children:
            source = self.getActivityData(pc[0])['name']  # bw2.Database(pc[0][0]).load()[pc[0]]['name']
            if pc[1] != self.custom_data['name']:
                target = self.getActivityData(pc[1])['name']
            else:
                target = self.custom_data['name']
            graph_data.append({
                'source': source,
                'target': target,
                'type': "suit"
            })
        # print graph_data
        return graph_data

    def getTreeData(self):
        """
        :param parents_children: like this: [(key0,key1),...]
        :return: hierarchical data
        """
        if not self.parents_children:
            return []
        def get_nodes(node):
            d = {}
            if node == self.custom_data['name']:
                d['name'] = node
            else:
                # print "NODE: " + str(node)
                d['name'] = self.getActivityData(node)['name']
            parents = get_parents(node)
            if parents:
                d['children'] = [get_nodes(parent) for parent in parents]
            return d
        def get_parents(node):
            return [x[0] for x in parents_children if x[1] == node]

        # self.printEdgesToConsole()
        # print "\nCalculating Tree Data from Parents/Children"
        parents_children = self.parents_children
        parents, children = zip(*parents_children)
        # find the nodes that are not linked to - they represent a "head"
        head_nodes = {x for x in children if x not in parents}
        tree_data = []
        for head in head_nodes:
            tree_data.append(get_nodes(head))
        # print json.dumps(tree_data, indent=2)
        return tree_data

    def printEdgesToConsole(self, edges_data, message=None):
        if message:
            print message
        for i, pc in enumerate(edges_data):
            if self.custom_data['name'] in pc:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+pc[1]
            else:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+self.getActivityData(pc[1])['name']

    def submitPSS(self):
        pss = {}
        outputs = []
        for i, key in enumerate(self.process_subsystem['outputs']):
            name = self.custom_data['output names'][key] if key in self.custom_data['output names'] else 'Output'+str(i)
            quantity = float(self.custom_data['output quantities'][key]) if key in self.custom_data['output quantities'] else 1.0
            outputs.append((key, name, quantity))
        chain = []
        for key in self.process_subsystem['chain']:
            if key != self.custom_data['name']:  # only real keys, not the head
                chain.append(key)
        cuts = []
        for i, cut in enumerate(self.process_subsystem['cuts']):
            parent, child = cut[0], cut[1]
            name = self.custom_data['cut names'][parent] if parent in self.custom_data['cut names'] else 'Cut'+str(i)
            cuts.append((parent, child, name))

        pss.update({
            'name': self.custom_data['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
            'edges': self.parents_children
        })
        print "\nPSS as SP:"
        print pss
        # print json.dumps(pss, indent=2)
        self.pss = pss
        # self.submitPSS_dagre()

    def submitPSS_dagre(self):
        SP = {}
        # TODO: include database name? (technically not really needed anymore)
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