#!/usr/bin/env python
# -*- coding: utf-8 -*-

from metaprocess import MetaProcess
from utils import *
import json

class MetaProcessCreator(BrowserStandardTasks):
    def __init__(self):
        self.mp_data = {'name': 'New Meta-Process', 'outputs': [], 'chain': [], 'cuts': []}
        self.newMetaProcess(self.mp_data)
        self.name_map = {}  # remembers key: "name" information during a session

    def update_mp(self):
        self.mp = MetaProcess(**self.mp_data)
        self.mp_data = self.mp.mp_data
        self.apply_name_map()
        # TODO: add custom information if available in name_map
        print "\nMP DATA:"
        print self.mp.mp_data

    def apply_name_map(self):
        # name map is applied only if a default name is present
        # otherwise custom names from other MP might be overwritten
        for o in self.mp_data['outputs']:
            if o[0] in self.name_map and o[1] == "Unspecified Output":
                self.set_output_name(o[0], self.name_map[o[0]], "Unspecified Output", 1.0, update=False)
        for o in self.mp_data['cuts']:
            if o[0] in self.name_map and o[2] == "Unspecified Input":
                self.set_cut_name(o[0], self.name_map[o[0]], update=False)
        # TODO: the value to a key could be a list of already used names for this key.
        # The user could be given a drop down menu to select one of these

    def newMetaProcess(self, mp_data=None):
        if not mp_data:
            self.mp_data = {'name': 'New Meta-Process', 'outputs': [], 'chain': [], 'cuts': [], 'output_based_scaling': True}
            self.mp = MetaProcess(**self.mp_data)
        else:  # load with try, except
            self.mp_data = mp_data
            self.mp = MetaProcess(**mp_data)

    def load_mp(self, mp):
        self.mp_data = mp
        self.update_mp()

    def add_output(self, key):
        self.mp_data['outputs'].append((key, "duplicate output", 1.0))
        self.update_mp()

    def remove_output(self, key, name, amount):
        for o in self.mp_data['outputs']:
            if o[0] == key and o[1] == name and o[2] == amount:
                self.mp_data['outputs'].remove(o)
        self.update_mp()

    def add_to_chain(self, key):
        self.mp_data['chain'].append(key)
        self.update_mp()

    def delete_from_chain(self, key):
        if not self.mp.internal_edges_with_cuts:  # top processes (no edges yet)
            self.mp_data['chain'].remove(key)
            print "Removed key from chain: " + str(key)
            self.update_mp()
        else:  # there are already edges
            parents, children, value = zip(*self.mp.internal_edges_with_cuts)
            if key in children:
                print "\nCannot remove activity as as other activities still link to it."
            elif key in parents:  # delete from chain
                self.mp_data['chain'].remove(key)
                print "Removed key from chain: " + str(key)
                self.update_mp()
            else:
                print "WARNING: Key not in chain. Key: " + self.getActivityData(key)['name']

    def add_cut(self, from_key):
        # TODO: add custom information if available in name_map
        if not self.mp.internal_edges_with_cuts:
            print "Nothing to cut from."
        else:
            parents, children, value = zip(*self.mp.internal_edges_with_cuts)
            if from_key in children:
                print "Cannot add cut. Activity is linked to by another activity."
            else:
                new_cuts = [(from_key, pcv[1], "Unspecified Input", pcv[2]) for pcv in self.mp.internal_scaled_edges_with_cuts if from_key == pcv[0]]
                self.mp_data['cuts'] = list(set(self.mp_data['cuts'] + new_cuts))
                print "cutting: " + str(new_cuts)
                self.update_mp()

    def delete_cut(self, from_key):
        print "FROM KEY...."
        print from_key
        for cut in self.mp_data['cuts']:
            if from_key == cut[0]:
                self.mp_data['cuts'].remove(cut)
        self.update_mp()
        # add deleted cut to chain again...
        self.add_to_chain(from_key)

    def set_mp_name(self, name):
        self.mp_data['name'] = name
        self.update_mp()

    def set_output_based_scaling(self, bool):
        self.mp_data['output_based_scaling'] = bool
        print "Set output based scaling to: " + str(bool)
        self.update_mp()

    def set_output_name(self, key, new_name, old_name, amount, update=True):
        for i, o in enumerate(self.mp_data['outputs']):
            if o[0] == key and o[1] == old_name and o[2] == amount:
                self.mp_data['outputs'][i] = tuple([o[0], new_name, o[2]])
        if update:
            self.name_map.update({key: new_name})
            self.update_mp()

    def set_output_quantity(self, key, text, name, amount):
        for i, o in enumerate(self.mp_data['outputs']):
            if o[0] == key and o[1] == name and o[2] == amount:
                self.mp_data['outputs'][i] = tuple([o[0], o[1], text])
        self.update_mp()

    def set_cut_name(self, key, name, update=True):
        for i, o in enumerate(self.mp_data['cuts']):
            if o[0] == key:
                self.mp_data['cuts'][i] = tuple([o[0], o[1], name, o[3]])
        if update:
            self.name_map.update({key: name})
            self.update_mp()

    # VISUALIZATION

    def getGraphData(self):
        graph_data = []
        for edge in self.mp.internal_edges_with_cuts:
            graph_data.append({
                'source': self.getActivityData(edge[0])['name'],
                'target': self.getActivityData(edge[1])['name'],
                'type': "suit",
                # 'edge_label': self.getActivityData(edge[0])['unit'],
            })
        # append connection to Meta-Process
        for sa in self.mp.scaling_activities:
            graph_data.append({
                'source': self.getActivityData(sa)['name'],
                'target': self.mp.name,
                'type': "licensing",
                # 'edge_label': self.getActivityData(sa)['unit'],
            })
        return graph_data

    def getTreeData(self):
        # TODO: rewrite using MetaProcess? To apply: self.internal_scaled_edges_with_cuts
        def get_nodes(node, child=None):
            d = {}
            if node == self.mp.name:
                d['name'] = node
            elif child == self.mp.name:
                d['name'] = self.getActivityData(node)['name']
                output_amount = [o[2] for o in self.mp.outputs]
                if output_amount:
                    d['output'] = " ".join(["{:10.2g}".format(output_amount[0]), self.getActivityData(node)['unit']])
            else:
                d['name'] = self.getActivityData(node)['name']
                # output amount
                output_amount = [edge[2] for edge in self.mp.internal_scaled_edges_with_cuts
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

        if not self.mp.chain:
            return []
        tree_data = []
        parents_children = [e[:2] for e in self.mp.internal_scaled_edges_with_cuts]  # not using amount yet
        head_nodes = self.mp.scaling_activities
        for head in head_nodes:
            parents_children.append((head, self.mp.name))

        tree_data.append(get_nodes(self.mp.name))
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

        mp = self.mp
        graph = []
        # outputs
        for outp, name, value in mp.outputs:
            value_source = sum([o[2] for o in mp.outputs if o[0] == outp])
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
        for inp, outp, name, value in mp.cuts:
            val_source_out = sum([edge[2] for edge in mp.internal_scaled_edges_with_cuts if outp == edge[1] and inp == edge[0]])
            value_output = sum([edge[2] for edge in mp.internal_scaled_edges_with_cuts if outp == edge[0]])
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
        for inp, outp, value in mp.internal_scaled_edges_with_cuts:
            value_output = sum([edge[2] for edge in mp.internal_scaled_edges_with_cuts if outp == edge[0]])
            inp_ad = self.getActivityData(inp)
            outp_ad = self.getActivityData(outp)
            if inp in mp.chain and outp in mp.chain:  # TODO: check necessary?
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
            'name': mp.name,
            'title': mp.name,
            'data': json.dumps(graph, indent=2)
        }
        return dagre_data

    def getHumanReadibleMP(self, mp_data):

        def getData(key):
            try:
                ad = self.getActivityData(key)
                return (ad['database'], ad['product'], ad['name'], ad['location'])
            except:
                return key

        outputs = [(getData(o[0]), o[1], o[2]) for o in mp_data['outputs']]
        chain = [getData(o) for o in mp_data['chain']]
        cuts = [(getData(o[0]), getData(o[1]), o[2], o[3]) for o in mp_data['cuts']]
        mp_HR = {
            'name': mp_data['name'],
            'outputs': outputs,
            'chain': chain,
            'cuts': cuts,
        }
        return mp_HR

    def printEdgesToConsole(self, edges_data, message=None):
        if message:
            print message
        for i, pc in enumerate(edges_data):
            if self.custom_data['name'] in pc:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+pc[1]
            else:
                print str(i)+". "+self.getActivityData(pc[0])['name']+" --> "+self.getActivityData(pc[1])['name']
