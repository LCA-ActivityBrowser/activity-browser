#!/usr/bin/env python
# -*- coding: utf-8 -*-

from processSubsystem import ProcessSubsystem
from utils import *
import json

class ProcessSubsystemCreator(BrowserStandardTasks):
    def __init__(self):
        self.pss_data = {'name': 'New Process Subsystem', 'outputs': [], 'chain': [], 'cuts': [], 'output_based_scaling': True}
        self.newProcessSubsystem(self.pss_data)
        self.name_map = {}  # remembers key: "name" information during a session

    def update_pss(self):
        self.pss = ProcessSubsystem(**self.pss_data)
        self.pss_data = self.pss.pss_data
        self.apply_name_map()
        # TODO: add custom information if available in name_map
        print "\nPSS DATA:"
        print self.pss.pss_data
        # print "INTERNAL EDGES (+CUTS):"
        # print self.pss.internal_edges_with_cuts

    def apply_name_map(self):
        # name map is applied only if a default name is present
        # otherwise custom names from other PSS might be overwritten
        for o in self.pss_data['outputs']:
            if o[0] in self.name_map and o[1] == "Unspecified Output":
                self.set_output_name(o[0], self.name_map[o[0]], "Unspecified Output", 1.0, update=False)
        for o in self.pss_data['cuts']:
            if o[0] in self.name_map and o[2] == "Unspecified Input":
                self.set_cut_name(o[0], self.name_map[o[0]], update=False)
        # TODO: the value to a key could be a list of already used names for this key.
        # The user could be given a drop down menu to select one of these

    def newProcessSubsystem(self, pss_data=None):
        if not pss_data:
            self.pss_data = {'name': 'New Process Subsystem', 'outputs': [], 'chain': [], 'cuts': [], 'output_based_scaling': True}
            self.pss = ProcessSubsystem(**self.pss_data)
        else:  # load with try, except
            self.pss_data = pss_data
            self.pss = ProcessSubsystem(**pss_data)

    def load_pss(self, pss):
        self.pss_data = pss
        self.update_pss()

    def add_output(self, key):
        self.pss_data['outputs'].append((key, "duplicate output", 1.0))
        self.update_pss()

    def remove_output(self, key, name, amount):
        for o in self.pss_data['outputs']:
            if o[0] == key and o[1] == name and o[2] == amount:
                self.pss_data['outputs'].remove(o)
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
                new_cuts = [(from_key, pcv[1], "Unspecified Input", pcv[2]) for pcv in self.pss.internal_scaled_edges_with_cuts if from_key == pcv[0]]
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

    def set_output_based_scaling(self, bool):
        self.pss_data['output_based_scaling'] = bool
        print "Set output based scaling to: " + str(bool)
        self.update_pss()

    def set_output_name(self, key, new_name, old_name, amount, update=True):
        for i, o in enumerate(self.pss_data['outputs']):
            if o[0] == key and o[1] == old_name and o[2] == amount:
                self.pss_data['outputs'][i] = tuple([o[0], new_name, o[2]])
        if update:
            self.name_map.update({key: new_name})
            self.update_pss()

    def set_output_quantity(self, key, text, name, amount):
        for i, o in enumerate(self.pss_data['outputs']):
            if o[0] == key and o[1] == name and o[2] == amount:
                self.pss_data['outputs'][i] = tuple([o[0], o[1], text])
        self.update_pss()

    def set_cut_name(self, key, name, update=True):
        for i, o in enumerate(self.pss_data['cuts']):
            if o[0] == key:
                self.pss_data['cuts'][i] = tuple([o[0], o[1], name, o[3]])
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
                'type': "suit",
                # 'edge_label': self.getActivityData(edge[0])['unit'],
            })
        # append connection to Process Subsystem
        for sa in self.pss.scaling_activities:
            graph_data.append({
                'source': self.getActivityData(sa)['name'],
                'target': self.pss.name,
                'type': "licensing",
                # 'edge_label': self.getActivityData(sa)['unit'],
            })
        return graph_data

    def getTreeData(self):
        # TODO: rewrite using ProcessSubsystem? To apply: self.internal_scaled_edges_with_cuts
        def get_nodes(node, child=None):
            d = {}
            if node == self.pss.name:
                d['name'] = node
            elif child == self.pss.name:
                d['name'] = self.getActivityData(node)['name']
                output_amount = [o[2] for o in self.pss.outputs]
                if output_amount:
                    d['output'] = " ".join(["{:10.2g}".format(output_amount[0]), self.getActivityData(node)['unit']])
            else:
                d['name'] = self.getActivityData(node)['name']
                # output amount
                output_amount = [edge[2] for edge in self.pss.internal_scaled_edges_with_cuts
                              if node == edge[0] and child == edge[1]]
                if len(output_amount) > 1:
                    print "WARNING, several outputs were found."
                elif output_amount:
                    d['output'] = " ".join(["{:10.2g}".format(output_amount[0]), self.getActivityData(node)['unit']])
            parents = get_parents(node)
            if parents:  # parents and children have the opposite meaning in this method and in the LCI database
                d['children'] = [get_nodes(parent, node) for parent in parents]
            return d

        def get_parents(node):
            return [x[0] for x in parents_children if x[1] == node]

        if not self.pss.chain:
            return []
        tree_data = []
        parents_children = [e[:2] for e in self.pss.internal_scaled_edges_with_cuts]  # not using amount yet
        head_nodes = self.pss.scaling_activities
        for head in head_nodes:
            parents_children.append((head, self.pss.name))

        tree_data.append(get_nodes(self.pss.name))
        return tree_data

    def get_dagre_data(self):
    # TODO: whenever a process has several inputs then only the amount of one is displayed instead of the sum
        def chunks(s, n):
            """Produce `n`-character chunks from `s`."""
            for start in range(0, len(s), n):
                yield s[start:start+n]

        def shorten(db, product, name, geo):
            # name_chunks = chunks(name, 20)
            # return "\\n".join(name_chunks)
            return name
            # return " ".join(name.split(" ")[:8]) + " (%s)" % geo

        def format_output(number, unit, product=''):
            if number:
                return " ".join(["{:.2g}".format(number), unit, product])
            else:
                return ''

        pss = self.pss
        graph = []
        # outputs
        for outp, name, value in pss.outputs:
            value_source = sum([o[2] for o in pss.outputs if o[0] == outp])
            outp_ad = self.getActivityData(outp)
            graph.append({
                'source': self.getActivityData(outp)['name'],
                'target': name,
                'source_in': '',
                'source_out': format_output(value_source, outp_ad['unit']),
                'target_in': '',
                'target_out': format_output(value, outp_ad['unit']),
                'class': 'output'
            })
        # cuts
        for inp, outp, name, value in pss.cuts:
            val_source_out = sum([edge[2] for edge in pss.internal_scaled_edges_with_cuts if outp == edge[1] and inp == edge[0]])
            value_output = sum([edge[2] for edge in pss.internal_scaled_edges_with_cuts if outp == edge[0]])
            inp_ad = self.getActivityData(inp)
            outp_ad = self.getActivityData(outp)
            graph.append({
                'source': inp_ad['name'],
                'target': outp_ad['name'],
                'source_product': inp_ad['product'],
                'target_product': outp_ad['product'],
                'source_in': '',
                'source_out': format_output(val_source_out, inp_ad['unit']),
                'target_in': '',
                'target_out': format_output(value_output, outp_ad['unit']),
                'class': 'cut'
            })
            if not [x for x in graph if x['source'] == name and x['target'] == outp_ad['name']]:
                graph.append({
                    'source': name,
                    'target': outp_ad['name'],
                    'class': 'substituted'
                })
        # chain
        for inp, outp, value in pss.internal_scaled_edges_with_cuts:
            value_output = sum([edge[2] for edge in pss.internal_scaled_edges_with_cuts if outp == edge[0]])
            inp_ad = self.getActivityData(inp)
            outp_ad = self.getActivityData(outp)
            if inp in pss.chain and outp in pss.chain:  # TODO: check necessary?
                graph.append({
                    'source': inp_ad['name'],
                    'target': outp_ad['name'],
                    'source_product': inp_ad['product'],
                    'target_product': outp_ad['product'],
                    'source_in': '',
                    'source_out': format_output(value, inp_ad['unit']),
                    'target_in': '',
                    'target_out': format_output(value_output, outp_ad['unit']),
                    'class': 'chain'
                })

        dagre_data = {
            'name': pss.name,
            'title': pss.name,
            'data': json.dumps(graph, indent=2)
        }
        return dagre_data

    def getHumanReadiblePSS(self, pss_data):
        # print pss_data

        def getData(key):
            try:
                ad = self.getActivityData(key)
                return (ad['database'], ad['product'], ad['name'], ad['location'])
            except:
                return key

        outputs = [(getData(o[0]), o[1], o[2]) for o in pss_data['outputs']]
        chain = [getData(o) for o in pss_data['chain']]
        cuts = [(getData(o[0]), getData(o[1]), o[2], o[3]) for o in pss_data['cuts']]
        # edges = [(getData(o[0]), getData(o[1])) for o in pss['edges']]
        pss_HR = {
            'name': pss_data['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
            # 'edges': edges,
        }
        # print "\nPSS (HUMAN READIBLE):"
        # print pss_HR
        return pss_HR

    def printEdgesToConsole(self, edges_data, message=None):
        if message:
            print message
        for i, pc in enumerate(edges_data):
            if self.custom_data['name'] in pc:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+pc[1]
            else:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+self.getActivityData(pc[1])['name']
