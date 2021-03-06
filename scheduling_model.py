
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

if NUM_PERIODS_PER_DAY == 7:
	lunch_periods = ["3", "4"]
elif NUM_PERIODS_PER_DAY == 8:
	lunch_periods = ["4", "5"]

# NUM_DAYS = 3
# days = tuple(list(string.ascii_uppercase)[0:NUM_DAYS])

BIG_M = 10000

print("Periods: {}".format(periods))

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
	max_class_size = data["max_class_size"]
	min_class_size = data["min_class_size"]
	core_type_indicator = data["core_type_indicator"]
	FTE = data["FTE"]
	numPeriods = data["numPeriods"]
	grade = data["grade"]
	grade_low = data["grade_low"]
	grade_high = data["grade_high"]
	PE_teacher = data["PE_teacher"]
	dance_teacher = data["dance_teacher"]
	PE_courses = ["PE6", "PE7", "PE8"]

	X = {}			# decision variable for student assignments
	Y = {}			# decision variable for teacher assignments
	
	# create a new model instance
	model = Model("school-scheduling")

	print("Building student/teacher decision variables")
	count = 0
	status = 0.0
	for course in courses:
		for period in periods:
			for student in students:
				# don't create lunch assignments outside of lunch periods
				if course in ["Lunch1", "Lunch2"] and period not in lunch_periods:
					X[student, course, period] = 0
				else:
					X[student, course, period] = model.addVar(vtype=GRB.BINARY, name='X.{}.{}.{}'.format(student, course, period))

			for teacher in staff_list:
				# if a teacher isn't teaching a course, then they can't teach it (i.e don't create a variable). NOTE: this is a simplifing assumption
				if staff_course[teacher, course] == 0 and course != "Lunch1" and course != "Lunch2":
					Y[teacher, course, period] = 0
				# don't create lunch assignments outside of lunch periods
				elif course in ["Lunch1", "Lunch2"] and period not in lunch_periods:
					Y[teacher, course, period] = 0
				else:
					Y[teacher, course, period] = model.addVar(vtype=GRB.BINARY, name='Y.{}.{}.{}'.format(teacher, course, period))

			print '{}%\r'.format(status),
			status = round((float(count) / float(len(courses)*len(periods))*100), 1)
			count += 1

	model.update()

	print("Adding teacher indicator variables")
	Z = {}			# decision variable if teacher is teaching or not
	for teacher in staff_list:
		Z[teacher] = model.addVar(vtype=GRB.BINARY, name='Z.{}'.format(teacher))

	print("Adding constraints to ensure every student is fully scheduled.")
	for student in students:
		for period in periods:
			model.addConstr(
				quicksum(X[student, course, period] for course in courses)
				== 1, name="every_student_fully_scheduled_{}_{}".format(student, period))

	print("Adding constraint to prevent teachers from being double-booked")
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

		# if they're not a PE teacher, they must be scheduled (i.e. current state)
		if (PE_teacher[teacher] == 0 and dance_teacher[teacher] == 0) or teacher == 'africanPorcupine':
			model.addConstr(Z[teacher] == 1, name='force_non_PE_to_teach_{}'.format(teacher))

		if FTE[teacher] >= 0.99:
			# one unallocated period for lunch, and one for a planning period
			maxNumPeriods = NUM_PERIODS_PER_DAY - 1
		else:
			maxNumPeriods = int(FTE[teacher]*NUM_PERIODS_PER_DAY)

		model.addConstr(
			quicksum(Y[teacher,course,period] for course in courses for period in periods) <= maxNumPeriods*Z[teacher],
			name='upper_limit_number_classes_per_teacher_{}'.format(teacher))
		model.addConstr(
			quicksum(Y[teacher,course,period] for course in courses for period in periods) >= Z[teacher],
			name='lower_limit_number_classes_per_teacher_{}'.format(teacher))

	print("Adding constraint to limit the number of students enrolled in each course")
	for course in courses:
		for period in periods:
			# model.addConstr(
			# 	quicksum(X[student,course,period] for student in students) <=
			# 	(max_class_size[course]+(max_class_size[course]*0.1)) * quicksum(Y[teacher,course,period] for teacher in staff_list),
			# 	name='max_class_size_{}_{}'.format(course, period))

			model.addConstr(
				quicksum(X[student,course,period] for student in students) <=
				max_class_size[course] * quicksum(Y[teacher,course,period] for teacher in staff_list),
				name='max_class_size_{}_{}'.format(course, period))

			model.addConstr(
				quicksum(X[student,course,period] for student in students) >=
				min_class_size[course] * quicksum(Y[teacher,course,period] for teacher in staff_list),
				name='min_class_size_{}_{}'.format(course, period))

			model.addConstr(
					quicksum(X[student,course,period] for student in students) <=
					30 * quicksum(Y[teacher,course,period] for teacher in staff_list),
					name='max_class_size_30_{}_{}'.format(course, period))

	print("Ensure each student gets assigned exclusively to the core classes in which they're currently enrolled")
	for student in students:
		for course in courses:
			# check if this student is currently taking this course and it's a core course
			if student_course[student, course] == 1 and core[course] == 1:
				model.addConstr(
					quicksum(X[student, course, period] for period in periods) == 1,
					name='same_core_class_assignment_{}_{}'.format(student, course))

			elif student_course[student, course] == 0 and core[course] == 1:
				for period in periods:
					model.addConstr(
						X[student, course, period] == 0,
						name='exclusive_core_class_assignment_{}_{}_{}'.format(student, course, period))


	print("Assign students and teachers to lunch in either period {} or {}".format(lunch_periods[0], lunch_periods[1]))
	for student in students:
		model.addConstr(
			X[student, "Lunch1", lunch_periods[0]]
			+ X[student, "Lunch1", lunch_periods[1]]
			+ X[student, "Lunch2", lunch_periods[0]]
			+ X[student, "Lunch2", lunch_periods[1]] == 1,
			name="assign_student_lunch_{}".format(student))

	for teacher in staff_list:
		model.addConstr(
			Y[teacher, "Lunch1", lunch_periods[0]]
			+ Y[teacher, "Lunch1", lunch_periods[1]]
			+ Y[teacher, "Lunch2", lunch_periods[0]]
			+ Y[teacher, "Lunch2", lunch_periods[1]] == Z[teacher],
			name="assign_teacher_lunch_{}".format(teacher))


	print("Adding indicator variable for each teacher and period")
	teacherScheduled = {}
	for teacher in staff_list:
		for period in periods:
			teacherScheduled[teacher,period] = model.addVar(vtype=GRB.BINARY,
				name='teacherScheduled_{}_{}'.format(teacher, period))
	for teacher in staff_list:
		for period in periods:
			model.addConstr(teacherScheduled[teacher, period] == quicksum(Y[teacher, course, period] for course in courses),
				name='link_teacherScheduled_{}_{}'.format(teacher, period))

	print("Adding constraint so part-time teachers are only scheduled in consecutive periods")
	w = {}		# 1 if node/period i is a sink for teacher t
	flow = {}	# flow from node/period i to j
	for teacher in staff_list:
		if FTE[teacher] < 0.99:
			for period1 in periods:
				w[teacher, period1] = model.addVar(vtype=GRB.BINARY, name='sinkIndicator_{}_{}'.format(teacher,period1))

				# only create flow variables for adjacent periods
				adjPeriods = [x for x in periods if abs(int(x) - int(period1)) <= 1]
				for period2 in adjPeriods:
					flow[teacher, period1, period2] = model.addVar(lb=0,vtype=GRB.INTEGER,
						name='flow_{}_{}_{}'.format(teacher, period1, period2))

	for teacher in staff_list:
		if FTE[teacher] < 0.99:
			M = int(FTE[teacher]*NUM_PERIODS_PER_DAY)
			for period1 in periods:
				adjPeriods = [x for x in periods if abs(int(x) - int(period1)) <= 1]

				model.addConstr(quicksum(flow[teacher, period1, period2] for period2 in adjPeriods) -
					quicksum(flow[teacher, period2, period1] for period2 in adjPeriods) >=
					teacherScheduled[teacher, period1] - M*w[teacher,period1],
					name='netOutflow_{}_{}'.format(teacher, period1))

				model.addConstr(quicksum(flow[teacher,period1, period2] for period2 in adjPeriods) <=
					(M - 1)*teacherScheduled[teacher, period1],
					name='flowControl_{}_{}'.format(teacher, period1))

				model.addConstr(teacherScheduled[teacher, period1] >= w[teacher, period1],
					name='if_sink_then_period_activated_{}_{}'.format(teacher,period1))

			model.addConstr(quicksum(w[teacher,period] for period in periods) <= 1,
				name='maxOneSink_{}'.format(teacher))

	print("Ensure each student takes PE once a day")
	for student in students:
		model.addConstr(
			quicksum(X[student, course, period]*PE[course] for course in courses for period in periods) == 1,
			name='PE_requirement_{}'.format(student))

		# this ensures each PE class is in the right grade range
		for course in PE_courses:
			if grade[student] != grade_low[course]:
				for period in periods:
					model.addConstr(X[student, course, period] == 0, name='restrict_PE_grade_range_{}_{}_{}'.format(student, course, period))

	print("Ensure PE isn't double book around and during lunch periods and during first period")
	before_lunch = str(int(lunch_periods[0]) - 1)
	after_lunch = str(int(lunch_periods[1]) + 1)
	no_double_booking = ["1"] + [before_lunch] + lunch_periods + [after_lunch]
	print("\t{}".format(no_double_booking))
	for period in no_double_booking:
		model.addConstr(quicksum(Y[teacher,course,period] for teacher in staff_list for course in PE_courses) <= 1, name='no_double_PE_period_{}'.format(period))

	numCurrentElectives = {}
	for student in students:
		numCurrentElectives[student] = model.addVar(lb=0,vtype=GRB.CONTINUOUS,name='numCurrentElectives_{}'.format(student))
	for student in students:
		model.addConstr(numCurrentElectives[student] ==
			quicksum(X[student, course, period] * (1-core[course]) * student_course[student,course] for course in courses for period in periods),
			name='link_num_current_electives_{}'.format(student))


	print("Building objective function")
	objectiveList = []

	extraTeacherFTE = model.addVar(lb=0,vtype=GRB.CONTINUOUS,name='extraTeacherFTE')
	model.addConstr(extraTeacherFTE == quicksum(Z[teacher]*FTE[teacher] for teacher in staff_list if PE_teacher[teacher] == 1 or dance_teacher[teacher] == 1), name='count_extra_FTE')
	objectiveList.append((1000, extraTeacherFTE))

	totalElectiveCountWeight = -1
	totalElectiveCount = model.addVar(vtype=GRB.CONTINUOUS, name='totalElectiveCount')
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