#!/usr/bin/env python

"""
DOCSTRING


"""


import pickle
from Tkinter import Tk
from tkFileDialog import askopenfilename, asksaveasfilename
import time

from gurobipy import *


def main(argv):
	"""Interprets command line arguments and either builds or solves MIP model."""

	Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
	model_filename = askopenfilename(title="Choose a model", initialdir="../models/")
	outputpath = asksaveasfilename(title="Choose an output file", defaultextension=".sol", initialdir="../models/")

	m = read(model_filename)

	# do IIS
	print('Computing IIS')
	removed = []

	# Loop until we reduce to a model that can be solved
	while True:

		m.computeIIS()
		print('\nThe following constraint cannot be satisfied:')
		for c in m.getConstrs():
			if c.IISConstr:
				print('%s' % c.constrName)
				# Remove a single constraint from the model
				removed.append(str(c.constrName))
				m.remove(c)
				break
		print('')

		m.optimize()
		status = m.status

		if status == GRB.Status.UNBOUNDED:
			print('The model cannot be solved because it is unbounded')
			exit(0)
		if status == GRB.Status.OPTIMAL:
			break
		if status != GRB.Status.INF_OR_UNBD and status != GRB.Status.INFEASIBLE:
			print('Optimization was stopped with status %d' % status)
			exit(0)

	print('\nThe following constraints were removed to get a feasible LP:')
	print(removed)

	print "Writing model to " + outputpath
	m.write(outputpath)

if __name__ == "__main__":
   main(sys.argv[1:])
