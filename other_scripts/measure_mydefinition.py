# this script studies the measurements of the graphs with transitive relations
# in-  and out- degree distribution


import gzip

from hdt import HDTDocument, IdentifierPosition
import numpy as np
import datetime
import pickle
import time
import networkx as nx
from networkx.algorithms import community
# import pymetis
import sys
import csv
# from z3 import *
import matplotlib.pyplot as plt
import tldextract
import json
import random
# from tarjan import tarjan
from collections import Counter
from bidict import bidict
import math
PATH_LOD = "/scratch/wbeek/data/LOD-a-lot/data.hdt"
hdt = HDTDocument(PATH_LOD)





c1=[
"http://dbpedia.org/ontology/predecessor",
"http://dbpedia.org/ontology/successor",
"http://dbpedia.org/ontology/previousWork",
"http://dbpedia.org/ontology/subsequentWork" ]


c2=[
"http://rdfs.org/sioc/ns#parent_of",
"http://dbpedia.org/ontology/parent"]

c3 =[
"http://www.w3.org/2000/01/rdf-schema#subClassOf",
"http://www.w3.org/2004/02/skos/core#broader",
"http://www.w3.org/2004/02/skos/core#narrower", # Counter({2: 3, 4: 1, 3: 1, 6: 1, 5: 1})
# "http://purl.org/dc/terms/hasPart", #  Counter({2: 332, 3: 49, 4: 13, 5: 4, 7: 2, 6: 2, 8: 1})
# "http://purl.org/dc/terms/isPartOf",  # Counter({2: 327, 3: 40, 4: 17, 6: 2, 5: 2, 8: 1})
"http://dbpedia.org/ontology/isPartOf"
]

predicate_to_study = c1 +c2 +c3
# predicate_to_study = c3[-2:]


def get_domain_and_label(t):
	# domain = tldextract.extract(t).domain
	domain =  None
	if 'dbpedia' in t:
		domain = 'dbo'
	elif 'skos' in t:
		domain = 'skos'
	elif 'dc' in t:
		domain = 'dc'
	elif 'rdf-schema' in t:
		domain = 'rdfs'
	elif 'sioc' in t:
		domain = 'sioc'
	else:
		domain = tldextract.extract(t).domain

	name1 = t.rsplit('/', 1)[-1]
	name2 = t.rsplit('#', 1)[-1]
	if len(name2) < len(name1):
		return (domain, name2)
	else:
		return (domain, name1)



def compute_SCC_graphs(p):
	graph = nx.DiGraph()
	t_triples, t_cardinality = hdt.search_triples("", p, "")

	for (l, p, r) in t_triples:
		graph.add_edge(l,r)

	overall_nodes = graph.number_of_nodes()
	overall_edges = graph.number_of_edges()
	nx_sccs = nx.strongly_connected_components(graph)
	filter_nx_sccs = [x for x in nx_sccs if len(x)>1]
	nx_ct = Counter()
	for f in filter_nx_sccs:
		nx_ct[len(f)] += 1

	print ('SCC info by original nx : ', nx_ct)
	# end = time.time()
	# hours, rem = divmod(end-start, 3600)
	# minutes, seconds = divmod(rem, 60)
	# print("Time taken original: {:0>2}:{:0>2}:{:05.2f}".format(int(hours),int(minutes),seconds))


	# obtain the corresponding scc graphs

	scc_graphs = []
	for s in filter_nx_sccs:
		g = graph.subgraph(s).copy()
		scc_graphs.append(g)

	# list(map( (lambda x: x+1), l ))
	lst = list (map (lambda x: x. number_of_edges(), scc_graphs))
	id = lst.index(max (lst))
	print ('Largest at index ', id)
	largest_scc = scc_graphs[id]
	print ('Largest number of edges ', largest_scc.number_of_edges())
	return overall_nodes, overall_edges, filter_nx_sccs, scc_graphs, largest_scc

def compute_alpha_beta (scc_graphs):
	num_all_scc_edges = 0
	num_of_size_two_cycle_edges = 0
	num_edges_left_in_new_SCC = 0

	resulting_graph  = nx.DiGraph() # the resuling graph after computing SCC

	for s in scc_graphs:
		resulting_graph.add_edges_from(list(s.edges()))
		num_all_scc_edges += s.number_of_edges()
		edges_to_remove = set()
		for (l,r) in s.edges():
			if (r,l) in s.edges():
				edges_to_remove.add((l,r))
				edges_to_remove.add((r,l))

		num_of_size_two_cycle_edges += len (edges_to_remove)
		resulting_graph.remove_edges_from(list(edges_to_remove))

	sccs = nx.strongly_connected_components(resulting_graph)
	filter_scc = [x for x in sccs if len(x)>1]

	for f in filter_scc:
		num_edges_left_in_new_SCC += resulting_graph.subgraph(f).number_of_edges()

	# print ('num_all_edges               = ', num_all_scc_edges )
	# print ('num_of_size_two_cycle_edges = ',  num_of_size_two_cycle_edges )
	# print ('num_edges_left_in_new_SCC   = ', num_edges_left_in_new_SCC )

	alpha = num_of_size_two_cycle_edges / num_all_scc_edges
	beta = num_edges_left_in_new_SCC / num_all_scc_edges

	return (alpha, beta)

# def compute_gamma_delta (sccs):
# 	ct = Counter()
# 	for f in sccs:
# 		ct[len(f)] += 1
# 	gamma = 0
# 	delta = 0
#
# 	for s in ct.keys():
# 		gamma += math.log10(ct[s]) / s
# 		delta += math.log10(s) / ct[s]
#
# 	return (gamma, delta)

def compute_scc_gamma_delta (scc):
	alpha, beta = compute_alpha_beta([scc])
	gamma = (1- alpha + beta)/ 2 * (alpha +beta)
	delta = gamma * scc.number_of_edges()
	return gamma, delta

def compute_delta(sccs):
	# for each s in sccs, compute gamma
	delta_acc = 0
	for s in sccs:
		g, d = compute_scc_gamma_delta(s)
		delta_acc += d
	return delta_acc


file_name_reduced = 'measure_output'
outputfile_reduced =  open(file_name_reduced, 'w', newline='')
writer_reduced = csv.writer(outputfile_reduced, delimiter='\t')



# now we deal with each predicate
measures = {}
for p in predicate_to_study:
	print ('\n\n\n\n now dealing with p = ', p)
	overall_nodes, overall_edges, sccs, scc_graphs, largest = compute_SCC_graphs(p)
	# print ('total SCCs', len(sccs))
	edge_acc = 0
	for scc in scc_graphs:
		edge_acc +=  scc.number_of_edges()
	nodes_acc = 0
	for scc in scc_graphs:
		nodes_acc +=  scc.number_of_nodes()

	print ('SCCs edges', edge_acc)
	print ('SCCs nodes = ', nodes_acc)
	largest_nodes = largest.number_of_nodes()
	largest_edges = largest.number_of_edges()
	print ('the largest scc has ', largest_nodes, ' nodes, and ', largest_edges, ' edges')
	print ('that is ', largest.number_of_edges()/ edge_acc, ' (portion) of number of edges')
	# how many are size-two cycles?
	size_two_sccs = 0
	num_sccs = len (scc_graphs)
	for scc in scc_graphs:
		if scc.number_of_nodes() == 2:
			size_two_sccs += 1
	print ('the number of size two SCCs: ', size_two_sccs)
	# =======  Alpha , Beta  ========
	print ('======== Now Alpha + Beta ======== ')
	(alpha, beta) = compute_alpha_beta(scc_graphs)
	print ('Entire graph     : alpha = ', alpha, ' beta =', beta)
	(alpha_max, beta_max) = compute_alpha_beta([largest])
	print ('Only largest SCC : alpha = ', alpha_max, ' beta =', beta_max)
	# ======== Gamma, Delta =======
	gamma, delta = compute_scc_gamma_delta(largest)
	print ('largest:  gamma = ', gamma , ' and delta = ', delta)
	delta_overall = compute_delta(scc_graphs)
	print ('overall delta = ', delta_overall)
	# (gamma, delta) = compute_gamma_delta(sccs)
	# print ('gamma = ', gamma, ' delta ', delta)
	# print ('\n\n')
	# measures [p] = (alpha, beta, gamma, delta)
	d, l = get_domain_and_label(p)
	p = d + ':' +l
# print ("{%.2f & %d}" % (3.456, 23))
	print ('%s & %d & %d & %d & %d & %d & %.2f & %.2f & %.2f & %d & %d &  %.2f &  %.2f & %.2f & %.2f \\\\ ' % (p, overall_edges, overall_nodes, edge_acc, nodes_acc, num_sccs, alpha, beta, delta_overall, largest_edges, largest_nodes, alpha_max, beta_max, gamma, delta))
	writer_reduced.writerow([p, overall_edges, overall_nodes, edge_acc, nodes_acc, num_sccs, alpha, beta, delta_overall, largest_edges, largest_nodes, alpha_max, beta_max, gamma, delta])
