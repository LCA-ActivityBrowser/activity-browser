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

lmp = LinkedMetaProcessSystem()

# load meta-process database
dir = os.path.dirname(__file__)
filename = os.path.join(dir, 'transport_example_CC.pickle')
# filename = os.path.join(dir, 'Heat example.pickle')
print "\nLoading database:", filename
lmp.load_from_file(filename)
print "Processes: %s" % len(lmp.processes)
print lmp.processes
print lmp.get_process_names(mp_list=lmp.mp_list[:3])
print "Products: %s" % len(lmp.products)
print lmp.products

outfile = 'test_save.pickle'
print "\nSaving database:", outfile
lmp.save_to_file(outfile)

mp = lmp.mp_list[-1]
print "\nRemoving the meta-process:", mp.name
lmp.remove_mp([mp])
print lmp.processes
print "Adding it again..."
lmp.add_mp([mp])
print lmp.processes
print "And adding it again... (provoking an error as identical names are not allowed!)"
try:
    lmp.add_mp([mp])
except ValueError:
    print "Adding processes with the same name gives a ValueError."
print lmp.processes

matrix, process_dict, products_dict = lmp.get_pp_matrix()
print "\nMatrix:"
print matrix
print "Processes:"
print process_dict
print "Products:"
print products_dict


print "\nProduct-Process Map:"
print lmp.product_process_dict()

print "\nName map:"
print lmp.map_name_mp

print "\nEdges:"
print lmp.edges()

functional_unit = 'transport'
# functional_unit = 'Heat'

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
scores = lmp.lca_processes(method=method, process_names=process_list)
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
    print i+1, l['meta-processes']
    print l['LCA score']
    print l['process contribution']
    print l['relative process contribution']
tic = time_info(tic)

print "\nName Map:"
print lmp.name_map