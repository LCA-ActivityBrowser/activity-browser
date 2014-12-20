#!/usr/bin/env python
# -*- coding: utf-8 -*-

from linkedmetaprocess import LinkedMetaProcessSystem
from metaprocess import MetaProcess
import pickle
import time
import os

def time_info(tic):
    print " -- Step/Total time: {:.2f} / {:.2f} seconds. --".format(time.clock()-tic, time.clock())
    return time.clock()

tic = time.clock()
# load meta-process database
dir = os.path.dirname(__file__)
filename = os.path.join(dir, 'transport_example_CC.pickle')
print "Test database:", filename
# filename = os.path.join(os.getcwd(), "transport_example_CC.pickle")
# filename = 'transport_example_CC.pickle'
with open(filename, 'r') as input:
    MP_DB = pickle.load(input)

mp_list = [MetaProcess(**pss) for pss in MP_DB]

lmp = LinkedMetaProcessSystem(mp_list)

print "Processes: %s" % len(lmp.processes)
print lmp.processes
print "Processes: %s" % len(lmp.products)
print lmp.products
print "Matrix:"
print lmp.pp_matrix

print "\nProduct-Process Map:"
print lmp.product_process_dict()

print "\nName map:"
print lmp.map_name_mp

print "\nEdges:"
print lmp.edges()

functional_unit = 'transport'

print "\nUpstream processes and products:"
proc, prod = lmp.upstream_products_processes(functional_unit)
print proc
print prod

print "\nAll pathways for: %s" % functional_unit
for i, p in enumerate(lmp.all_pathways(functional_unit)):
    print i+1, p

print "\nGet custom PP-Matrix:"
# mp_selection = ['Electricity production', 'NG production', 'Transport electric car']
mp_selection = ['NG production', 'Transport electric car']
matrix_sel, process_map, products_map = lmp.get_pp_matrix(mp_selection)
print matrix_sel
print process_map
print products_map

print "\nScaling vector and foreground demand:"
# mp_selection = ['Electricity production', 'NG production', 'Transport electric car']
mp_selection = ['Transport, natural gas car', 'NG production']
demand = {
    'transport': 1.0,
}
scaling_dict = lmp.scaling_vector_foreground_demand(mp_selection, demand)
print scaling_dict
# print foreground_demand
tic = time_info(tic)


# LCA for
print "\n1. specific processes: lca_scores"
print "LCA scores:"
method = (u'IPCC 2007', u'climate change', u'GWP 100a')
process_list = ['Transport, natural gas car', 'Transport, natural gas car_2', 'NG production']
scores = lmp.lca_processes(method=method, process_list=process_list)
for k, v in scores.items():
    print "{0}: {1:.2g}".format(k, v)
tic = time_info(tic)

print "\n2. A specific demand from linked meta-process system"
print "LCA score:"
demand = {'transport': 1.0}
print "demand:", demand
mp_selection = ['Transport, natural gas car', 'NG production']
print lmp.lca_linked_processes(method, mp_selection, demand)
# check with meta-process that does NOT have 1 on the diagonal
mp_selection = ['Transport, natural gas car_2', 'NG production']
print lmp.lca_linked_processes(method, mp_selection, demand)
tic = time_info(tic)

print "\n3. LCA results for all combinations for a given functional unit"
print "LCA scores:"
demand = {'transport': 1.0}
print "demand:", demand
lca_results = lmp.lca_alternatives(method, demand)
for i, l in enumerate(lca_results):
    print
    print i+1, l['path']
    print l['lca results']
tic = time_info(tic)