
import sys
from pyodbc import *


from Tkinter import Tk
from tkFileDialog import askopenfilename, asksaveasfilename


def read_solution_file(filename):
	'''Parses Gurobi solution file, returns list (first item is name, second is objective value)'''
	# Check if file exists
	print "Reading solution file"

	student_variables = {}
	staff_variables = {}
	with open(filename, 'r') as f:
		for line in f.readlines():
			# avoid comments
			if line[0] == "#" or not (line[0] == 'X' or line[0] == 'Y'):
				continue

			data = line.split(" ")	# split data into variable name and variable value
			var_name = data[0]
			var_value = int(round(float(data[1])))

			# print(var_name)

			# check if this decision variable is activated
			if var_value == 1:
				# split the variable name (indices are seperated by periods)
				var_name = var_name.split(".")

				var_type = var_name[0]
				name = var_name[1]
				course = var_name[2]
				period = var_name[3]

				if var_type == 'X':	# student decision var
					student_variables[name, period] = course

				elif var_type == 'Y':	# staff decision var
					staff_variables[name, period] = course

	print "Read solution."
	return student_variables, staff_variables

def save_solution_csv(variables, title="Choose an output file"):
	outputpath = asksaveasfilename(title=title, defaultextension=".csv", initialdir="./")
	print("Writing csv file to {}".format(outputpath))

	with open(outputpath, 'w+') as f:
		f.write("name,period,course\n")

		for key,course in variables.iteritems():
			f.write(str(key[0]) + ",")
			f.write(str(key[1]) + ",")
			f.write(str(course) + "\n")

def main():
	"""Reads solution file, puts it into dictionary."""
	Tk().withdraw()
	filename = askopenfilename(title="Choose a solution file", initialdir="./")

	student_variables, staff_variables = read_solution_file(filename)

	save_solution_csv(student_variables, title="Output file for student solution file")
	save_solution_csv(staff_variables, title="Output file for staff solution file")

if __name__ == '__main__':

	main()