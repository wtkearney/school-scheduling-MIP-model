

import time
import cPickle as pickle
import string
import os

from gurobipy import *
import data_utilities

DATA_FILEPATH = './data/course_scheduling_data.p'

# define some important fields
NUM_PERIODS_PER_DAY = 6
periods = tuple([x for x in range(1, NUM_PERIODS_PER_DAY+1)])

NUM_DAYS = 3
days = tuple(list(string.ascii_uppercase)[0:NUM_DAYS])

print("Periods: {}".format(periods))
print("Days: {}".format(days))

def main():

	# get the data; if it doesn't exist on disk, get it from drive and pickle it for later
	if os.path.isfile(DATA_FILEPATH):
		data = pickle.load( open(DATA_FILEPATH, "r"))
	else:
		print("Data does not exist on disk; retreiving from Google Drive")
		data = data_utilities.get_data()
		pickle.dump(data, open(DATA_FILEPATH, "w"))

	# localize data fields

if __name__ == '__main__':
	main()