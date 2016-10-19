
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

if NUM_PERIODS_PER_DAY == 7:
	lunch_periods = ["03", "04"]
elif NUM_PERIODS_PER_DAY == 8:
	lunch_periods = ["04", "05"]

NUM_DAYS = 3
days = tuple(list(string.ascii_uppercase)[0:NUM_DAYS])

BIG_M = 100000

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
	students = data["students"]
	staff_course = data["staff_course"]
	student_course = data["student_course"]
	core = data["core"]
	PE = data["PE"]
	immersion = data["immersion"]
	ELL = data["ELL"]
	SPED = data["SPED"]
	gr05 = data["gr05"]

	# define variables
	X = {}								# decision variable
	teacher_scheduled_indicator = {}	# indicates if a teacher is scheduled for a given course during a given period and day
	num_students_assigned = {}			# the number of students assigned for a given course and teacher during a given period and day

	# create a new model instance
	model = Model("school-scheduling")

	print("Building decision variables")
	count = 0
	status = 0.0
	for student in students:
		for teacher in staff_list:
			for course in courses:
				for period in periods:
					for day in days:
						# if a teacher isn't teaching a course, then they can't teach it (i.e don't create a variable)
						# NOTE: this is a simplifing assumption
						if staff_course[teacher, course] == 0:
							X[student, teacher, course, period, day] = 0
						else:
							# create decision variable
							X[student, teacher, course, period, day] = model.addVar(vtype=GRB.BINARY, name='X.{}.{}.{}.{}.{}'.format(student, teacher, course, period, day))

		print '{}%\r'.format(status),
		status = round((float(count) / float(len(students))*100), 1)
		count += 1


	print("Building variables to count number of students assigned for a given teacher, course, period, and day\n\tand variables to indicate if a teacher is scheduled for a given course, period, and day")
	for teacher in staff_list:
		for course in courses:
			for period in periods:
				for day in days:
					# variables to count number of students assigned for a given teacher, course, period, and day
					num_students_assigned[teacher, course, period, day] = model.addVar(lb=0, vtype=GRB.INTEGER, name='num_students_assigned_{}_{}_{}_{}'.format(teacher, course, period, day))
					# variables to indicate if a teacher is scheduled for a given course, period, and day
					teacher_scheduled_indicator[teacher, course, period, day] = model.addVar(vtype=GRB.BINARY, name='teacher_scheduled_indicator_{}_{}_{}_{}'.format(teacher, course, period, day))


	model.update()

	# add constraints to ensure every student is fully scheduled
	print("Adding constraints to ensure every student is fully scheduled.")
	for student in students:
		for day in days:
			model.addConstr(
				quicksum(X[student, teacher, course, period, day] for teacher in staff_list for course in courses for period in periods)
				== NUM_PERIODS_PER_DAY, name="every_student_fully_scheduled_{}_{}".format(student, day))

	# constraint to count number of students assigned
	print("Adding constraints to count number of students assigned.")
	for teacher in staff_list:
		for course in courses:
			for period in periods:
				for day in days:
					model.addConstr(
						num_students_assigned[teacher, course, period, day]
						== quicksum(X[student, teacher, course, period, day] for student in students), name='num_students_assigned_{}_{}_{}_{}'.format(teacher, course, period, day))

	# constraints to link teacher scheduled indicator variable
	print("Adding constraints to link teacher scheduled indicator variable.")
	for teacher in staff_list:
		for course in courses:
			for period in periods:
				for day in days:
					model.addConstr(
						teacher_scheduled_indicator[teacher, course, period, day]*BIG_M
						>= num_students_assigned[teacher, course, period, day], name="link_teacher_scheduled_indicator_{}_{}_{}_{}".format(teacher, course, period, day))

	
	print("Adding constraint to ensure every teacher is teaching one or fewer courses for each period on each day")
	for teacher in staff_list:
		for period in periods:
			for day in days:
				model.addConstr(quicksum(teacher_scheduled_indicator[teacher, course, period, day] for course in courses)
					<= 1, name="teachers_not_double_scheduled_{}".format(teacher))

	print("Adding constraint that forces student assignments if they're currently enrolled in a core class")
	for student in students:
		for course in courses:
			if student_course[student, course] == 1 and core[course] == 1:
				model.addConstr(quicksum(X[student, teacher, course, period, day] for teacher in staff_list for period in periods for day in days)
					== 1, name="student_assigned_to_current_core_classes_{}_{}".format(student, course))


	print("Assign students and teacher to lunch")
	for student in students:
		for teacher in staff_list:
			for day in days:
				model.addConstr(X[student, teacher, "Lunch1", lunch_periods[0], day]
					+ X[student, teacher, "Lunch1", lunch_periods[1], day]
					+ X[student, teacher, "Lunch2", lunch_periods[0], day]
					+ X[student, teacher, "Lunch2", lunch_periods[1], day] == 1, name="assign_teacher_student_lunch_{}_{}_{}".format(student, teacher, day))


	# print("Ensure teachers can only teach a course they're currently teaching.")
	# for student in students:
	# 	for teacher in staff_list:
	# 		for course in courses:
	# 			for period in periods:
	# 				for day in days:
	# 					X[student, teacher, course, period, day] 

	model.update()


	return model


def save_as_mps(model):
	outputpath = asksaveasfilename(title="Choose an output file", defaultextension=".mps", initialdir="../model/")
	print("Writing model to {}".format(outputpath))
	model.write(outputpath)

if __name__ == '__main__':
	model = build_model()

	save_as_mps(model)