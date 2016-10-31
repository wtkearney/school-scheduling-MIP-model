
from Tkinter import Tk
from tkFileDialog import askopenfilename, asksaveasfilename

import time
import cPickle as pickle
import string
import os

from gurobipy import *

# define some important fields
NUM_PERIODS_PER_DAY = 8
periods = tuple([x for x in range(1, NUM_PERIODS_PER_DAY+1)])

MAX_NUMBER_PERIODS_PER_TEACHER = 5

if NUM_PERIODS_PER_DAY == 7:
	lunch_periods = ["03", "04"]
elif NUM_PERIODS_PER_DAY == 8:
	lunch_periods = ["04", "05"]

NUM_DAYS = 3
days = tuple(list(string.ascii_uppercase)[0:NUM_DAYS])

BIG_M = 10000

print("Periods: {}".format(periods))
print("Days: {}".format(days))

def build_model():

	# get name of data file and output path
	Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
	data_filename = askopenfilename(title="Choose a pickled data object", initialdir="../data/")
	print("Loading data from {}".format(data_filename))
	data = pickle.load( open(data_filename, "r") )

	# localize data fields
	staff_list = data["staff_list"]
	courses = data["courses"]
	course_types = data["course_types"]
	students = data["students"]
	staff_course = data["staff_course"]
	student_course = data["student_course"]
	core = data["core"]
	PE = data["PE"]
	immersion = data["immersion"]
	ELL = data["ELL"]
	SPED = data["SPED"]
	gr05 = data["gr05"]
	max_class_size = data["max_class_size"]
	core_type_indicator = data["core_type_indicator"]


	X = {}			# decision variable for student assignments
	Y = {}			# decision variable for teacher assignments

	# create a new model instance
	model = Model("school-scheduling")

	print("Building decision variables")
	var_counter_actual = 0
	var_counter_removed = 0
	count = 0
	status = 0.0
	for course in courses:
		for period in periods:
			for student in students:
				X[student, course, period] = model.addVar(vtype=GRB.BINARY, name='X.{}.{}.{}'.format(student, course, period))
				var_counter_actual += 1

			for teacher in staff_list:
				# if a teacher isn't teaching a course, then they can't teach it (i.e don't create a variable). NOTE: this is a simplifing assumption
				if staff_course[teacher, course] == 0:
					Y[teacher, course, period] = 0
					var_counter_removed += 1
				else:
					Y[teacher, course, period] = model.addVar(vtype=GRB.BINARY, name='Y.{}.{}.{}'.format(teacher, course, period))
					var_counter_actual += 1

			print '{}%\r'.format(status),
			status = round((float(count) / float(len(courses)*len(periods))*100), 1)
			count += 1

	print "Var counter removed: {}".format(var_counter_removed)
	print "Var counter actual: {}".format(var_counter_actual)


	model.update()

	print("Adding constraints to ensure every student is fully scheduled.")
	for student in students:
		model.addConstr(
			quicksum(X[student, course, period] for course in courses for period in periods)
			== NUM_PERIODS_PER_DAY, name="every_student_fully_scheduled_{}".format(student))


	print("Adding constraint to limit one teacher per course/period")
	for course in courses:
		for period in periods:
			model.addConstr(
				quicksum(Y[teacher,course,period] for teacher in staff_list) <= 1,
				name='one_teacher_per_course_and_period_{}_{}'.format(course, period))

	print("Adding constraint to limit total number of courses each teacher is assigned")
	for teacher in staff_list:
		model.addConstr(
			quicksum(Y[teacher,course,period] for course in courses for period in periods) <= 5,
			name='limit_number_classes_per_teacher_{}'.format(teacher))


	print("Adding constraint to limit the number of students enrolled in each course")
	for course in courses:
		for period in periods:
			model.addConstr(
				quicksum(X[student,course,period] for student in students) <= max_class_size[course] * quicksum(Y[teacher,course,period] for teacher in staff_list),
				name='max_class_size_{}_{}'.format(course, period))

	print("Adding constraint to ensure each student takes at least one of each type of core class")
	for student in students:
		for course_type in course_types:
			model.addConstr(
				quicksum(X[student, course, period] * core_type_indicator[course, course_type] for course in courses for period in periods) >= 1,
				name='core_class_requirement_{}_{}'.format(student, course_type))


	print("Assign students and teachers to lunch")
	for student in students:
		model.addConstr(
			X[student, "Lunch1", lunch_periods[0]]
			+ X[student, "Lunch1", lunch_periods[1]]
			+ X[student, "Lunch2", lunch_periods[0]]
			+ X[student, "Lunch2", lunch_periods[1]] == 1,
			name="assign_student_lunch_{}".format(student))

	model.update()


	return model


def save_as_mps(model):
	outputpath = asksaveasfilename(title="Choose an output file", defaultextension=".mps", initialdir="../model/")
	print("Writing model to {}".format(outputpath))
	model.write(outputpath)

if __name__ == '__main__':
	model = build_model()

	save_as_mps(model)