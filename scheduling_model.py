
from Tkinter import Tk
from tkFileDialog import askopenfilename, asksaveasfilename

import time
import cPickle as pickle
import string
import os

from gurobipy import *

# define some important fields
NUM_PERIODS_PER_DAY = 8
periods = tuple([str(x) for x in range(1, NUM_PERIODS_PER_DAY+1)])

NUM_CORE_CLASSES = 5

MAX_NUMBER_PERIODS_PER_TEACHER = 5

if NUM_PERIODS_PER_DAY == 7:
	lunch_periods = ["3", "4"]
elif NUM_PERIODS_PER_DAY == 8:
	lunch_periods = ["4", "5"]

NUM_DAYS = 3
days = tuple(list(string.ascii_uppercase)[0:NUM_DAYS])

BIG_M = 10000

print("Periods: {}".format(periods))
print("Days: {}".format(days))

def build_model():

	# get name of data file and output path
	Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing
	data_filename = askopenfilename(title="Choose a pickled data object", initialdir="./data/")
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
	FTE = data["FTE"]
	numPeriods = data["numPeriods"]
	grade = data["grade"]

	X = {}			# decision variable for student assignments
	Y = {}			# decision variable for teacher assignments

	# create a new model instance
	model = Model("school-scheduling")

	print("Building decision variables")
	count = 0
	status = 0.0
	for course in courses:
		for period in periods:
			for student in students:
				X[student, course, period] = model.addVar(vtype=GRB.BINARY, name='X.{}.{}.{}'.format(student, course, period))

			for teacher in staff_list:
				# if a teacher isn't teaching a course, then they can't teach it (i.e don't create a variable). NOTE: this is a simplifing assumption
				if staff_course[teacher, course] == 0:
					Y[teacher, course, period] = 0
				else:
					Y[teacher, course, period] = model.addVar(vtype=GRB.BINARY, name='Y.{}.{}.{}'.format(teacher, course, period))

			print '{}%\r'.format(status),
			status = round((float(count) / float(len(courses)*len(periods))*100), 1)
			count += 1

	model.update()

	print("Adding constraints to ensure every student is fully scheduled.")
	for student in students:
		for period in periods:
			model.addConstr(
				quicksum(X[student, course, period] for course in courses)
				== 1, name="every_student_fully_scheduled_{}_{}".format(student, period))

	print("Adding constraint to ensure one teacher per course/period")
	for teacher in staff_list:
		for period in periods:
			model.addConstr(
				quicksum(Y[teacher,course,period] for course in courses) <= 1,
				name='one_teacher_per_course_and_period_{}_{}'.format(teacher, period))

	print("Ensure student can't take a given class more than once")
	for student in students:
		for course in courses:
			model.addConstr(
				quicksum(X[student, course, period] for period in periods) <= 1,
				name='cant_take_class_more_than_once_{}_{}'.format(student, course))

	print("Adding constraint to limit total number of courses each teacher is assigned")
	for teacher in staff_list:
		if FTE[teacher] >= 0.99:
			maxNumPeriods = NUM_PERIODS_PER_DAY - 1
		else:
			maxNumPeriods = int(FTE[teacher]*NUM_PERIODS_PER_DAY)
		model.addConstr(
			quicksum(Y[teacher,course,period] for course in courses for period in periods) <= maxNumPeriods,
			name='upper_limit_number_classes_per_teacher_{}'.format(teacher))
		model.addConstr(
			quicksum(Y[teacher,course,period] for course in courses for period in periods) >= 1,
			name='lower_limit_number_classes_per_teacher_{}'.format(teacher))

	print("Adding constraint to limit the number of students enrolled in each course")
	for course in courses:
		for period in periods:
			model.addConstr(
				quicksum(X[student,course,period] for student in students) <= max_class_size[course] * quicksum(Y[teacher,course,period] for teacher in staff_list),
				name='max_class_size_{}_{}'.format(course, period))

	# print("Adding constraint to ensure each student takes at least one of each type of core class")
	# for student in students:
	# 	# for course_type in course_types:
	# 	for course_type in ["MSMath"]:
	# 		model.addConstr(
	# 			quicksum(X[student, course, period] * core_type_indicator[course, course_type] for course in courses for period in periods) >= 1,
	# 			name='core_class_requirement_{}_{}'.format(student, course_type))

	# print("Ensure each student takes at least {} core classes".format(NUM_CORE_CLASSES))
	# for student in students:
	# 	model.addConstr(
	# 		quicksum(X[student, course, period]*core[course] for course in courses for period in periods) == NUM_CORE_CLASSES,
	# 		name='core_class_requirement_{}'.format(student))

	print("Ensure each student gets assigned the core classes in which they're currently enrolled")
	for student in students:
		for course in courses:
			# check if this student is currently taking this course and it's a core course
			if student_course[student, course] == 1 and core[course] == 1:
				model.addConstr(
					quicksum(X[student, course, period] for period in periods) == 1,
					name='same_core_class_assignment_{}_{}'.format(student, course))

	print("Assign students and teachers to lunch in either period {} or {}".format(lunch_periods[0], lunch_periods[1]))
	for student in students:
		model.addConstr(
			X[student, "Lunch1", lunch_periods[0]]
			+ X[student, "Lunch1", lunch_periods[1]]
			+ X[student, "Lunch2", lunch_periods[0]]
			+ X[student, "Lunch2", lunch_periods[1]] == 1,
			name="assign_student_lunch_{}".format(student))

	for teacher in staff_list:
		# only one teacher is currently teaching lunch; thus the model is infeasible if this if statement
		# is removed because they're the only one who _can_ teach lunch, and thus have to teach both sections
		if staff_course[teacher, "Lunch1"] != 1 and staff_course[teacher, "Lunch2"] != 1:
			model.addConstr(
				quicksum(Y[teacher, course, lunch_periods[0]] +
					Y[teacher, course, lunch_periods[1]] for course in courses) <= 1,
					name="assign_teacher_lunch_break_{}".format(teacher))

	# print("Ensure each student takes PE once a day")
	# for student in students:
	# 	if grade[student] == 6:
	# 		PE_courseName = "PE6"
	# 	elif grade[student] == 7:
	# 		PE_courseName = "PE7"
	# 	elif grade[student] == 8:
	# 		PE_courseName = "PE8"
	# 	elif grade[student] == 5:
	# 		continue
	# 	else:
	# 		print grade[student]
	# 	model.addConstr(
	# 		quicksum(X[student, PE_courseName, period] for period in periods) == 1,
	# 		name='PE_requirement_{}'.format(student))

	numCurrentElectives = {}
	for student in students:
		numCurrentElectives[student] = model.addVar(lb=0,vtype=GRB.INTEGER,name='numCurrentElectives_{}'.format(student))
	for student in students:
		model.addConstr(numCurrentElectives[student] ==
			quicksum(X[student, course, period] * (1-core[course]) * student_course[student,course] for course in courses for period in periods),
			name='link_num_current_electives_{}'.format(student))

	print("Creating class size minimax variables")
	maxClassSize = {}
	for course in courses:
		maxClassSize[course] = model.addVar(lb=0,ub=max_class_size[course],vtype=GRB.INTEGER,
			name='maxClassSize_{}'.format(course))
	
	for course in courses:
		for period in periods:
			model.addConstr(
				maxClassSize[course] >= quicksum(X[student, course, period] for student in students),
				name='minimax_classSize_link_{}_{}'.format(course, period))


	# print("Ensure student can't take a given class type more than twice per day")
	# for student in students:
	# 	for course_type in course_types:
	# 		model.addConstr(
	# 			quicksum(X[student, course, period] for period in periods for course in courses if core_type_indicator[course, course_type] == 1) <= 2,
	# 			name='cant_take_core_class_type_more_than_once_{}_{}'.format(student, course_type))

	# print("Force current students/class assignments")
	# for student in students:
	# 	for course in courses:
	# 		if student_course[student, course] == 1:
	# 			model.addConstr(
	# 				quicksum(X[student, course, period] for period in periods) == 1,
	# 				name='force_class_assignment_{}_{}'.format(student, course))

	print("Building objective function")
	objectiveList = []

	totalElectiveCountWeight = -1
	totalElectiveCount = model.addVar(vtype=GRB.INTEGER, name='totalElectiveCount')
	model.addConstr(totalElectiveCount == quicksum(numCurrentElectives[student] for student in students),
		name='linkTotalElectiveCount')
	objectiveList.append((totalElectiveCountWeight, totalElectiveCount))

	# totalMinimaxClassSizeWeight = 1
	# totalMinimaxClassSize = model.addVar(vtype=GRB.INTEGER, name='totalMinimaxClassSize')
	# model.addConstr(totalMinimaxClassSize == quicksum(maxClassSize[course] for course in courses),
	# 	name='linkTotalMinimaxClassSize')
	# objectiveList.append((totalMinimaxClassSizeWeight, totalMinimaxClassSize))

	# add the objective variables to the gurobi model
	model.setObjective(quicksum(weight*var for (weight,var) in objectiveList))
	model.ModelSense = GRB.MINIMIZE

	model.update()

	print "\nObjective:"
	print model.getObjective()

	return model


def save_as_mps(model):
	outputpath = asksaveasfilename(title="Choose an output file", defaultextension=".mps", initialdir="../model/")
	print("Writing model to {}".format(outputpath))
	model.write(outputpath)

if __name__ == '__main__':
	model = build_model()

	save_as_mps(model)