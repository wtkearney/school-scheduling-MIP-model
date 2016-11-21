
import sys
from pyodbc import *


from Tkinter import Tk
from tkFileDialog import askopenfilename


def read_solution_file(filename):
	'''Parses Gurobi solution file, returns list (first item is name, second is objective value)'''
	# Check if file exists
	print "reading solution file"

	student_variables = {}
	staff_variables = {}
	try:
		with open(filename, 'r') as f:
			for line in f.readlines():
				# avoid comments
				if line[0] == "#":
					continue

				data = line.split(" ")	# split data into variable name and variable value
				var_name = data[0]
				var_value = int(round(float(data[1])))

				# check if this decision variable is activated
				if var_value == 1:
					# split the variable name (indices are seperated by periods)
					var_name = var.split(".")

					var_type = var_name[0]
					name = var_name[1]
					course = var_name[2]
					period = var_name[3]

					if var_type == 'x':	# student decision var
						student_variables[name, period] = course

					if var_type == 'y':	# staff decision var
						staff_variables[name, period] = course

	except IOError:
		print(filename + " does not exist. Exiting.")
		exit(0)

	print "Read solution."
	return student_variables, staff_variables

def main():
	"""Reads solution file, puts it into dictionary."""
	Tk().withdraw()
	filename = askopenfilename(title="Choose a solution file", initialdir="./")

	student_variables, staff_variables = read_solution_file(filename)

def build_solution_csv(variables):
	outputpath = asksaveasfilename(title="Choose an output file", defaultextension=".mps", initialdir="../models/")
	print("Writing model to {}".format(outputpath))

if __name__ == '__main__':
	if len(sys.argv) <= 1:
		print("Usage: parse_solution.py")
		exit(0)

	main()