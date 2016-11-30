import httplib2
import os

import pandas as pd

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import cPickle as pickle
import re

try:
	import argparse
	flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
	flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-course-scheduling.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Course Scheduling'

SPREADSHEET_DATA_ID = "1GbrcdGX-pzZGD5k6Q8Q9RkPhtk_Ekt50DGj4MsAR8hY"


def get_credentials():
	"""Gets valid user credentials from storage.

	If nothing has been stored, or if the stored credentials are invalid,
	the OAuth2 flow is completed to obtain the new credentials.

	Returns:
		Credentials, the obtained credential.
	"""
	home_dir = os.path.expanduser('~')
	credential_dir = os.path.join(home_dir, '.credentials')
	if not os.path.exists(credential_dir):
		os.makedirs(credential_dir)
	credential_path = os.path.join(credential_dir, 'sheets.googleapis.com-course-scheduling.json')

	store = Storage(credential_path)
	credentials = store.get()
	if not credentials or credentials.invalid:
		flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
		flow.user_agent = APPLICATION_NAME
		if flags:
			credentials = tools.run_flow(flow, store, flags)
		else: # Needed only for compatibility with Python 2.6
			credentials = tools.run(flow, store)
		print('Storing credentials to ' + credential_path)
	return credentials

def get_data():
	print("Getting credentials")
	credentials = get_credentials()
	http = credentials.authorize(httplib2.Http())
	discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
	service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)

	print("Getting data")

	# staff
	rangeName = 'staff!A:M'
	result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_DATA_ID, range=rangeName).execute()
	staff = result.get('values', [])
	staff_headers = staff.pop(0)

	# staff_course
	rangeName = 'staff_course!A:E'
	result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_DATA_ID, range=rangeName).execute()
	staff_course = result.get('values', [])
	staff_course_headers = staff_course.pop(0)

	# students
	rangeName = 'students!A:I'
	result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_DATA_ID, range=rangeName).execute()
	students = result.get('values', [])
	students_headers = students.pop(0)

	# student_courses
	rangeName = 'student_courses!A:E'
	result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_DATA_ID, range=rangeName).execute()
	student_courses = result.get('values', [])
	student_courses_headers = student_courses.pop(0)

	# courses
	rangeName = 'courses!A:Q'
	result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_DATA_ID, range=rangeName).execute()
	courses = result.get('values', [])
	courses_headers = courses.pop(0)

	# rooms
	rangeName = 'rooms!A:I'
	result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_DATA_ID, range=rangeName).execute()
	rooms = result.get('values', [])
	rooms_headers = rooms.pop(0)

	print("Converting raw data")

	# convert lists of lists to pandas dataframes
	staff_data_frame = pd.DataFrame(staff, columns=staff_headers)
	staff_course_data_frame = pd.DataFrame(staff_course, columns=staff_course_headers)
	students_data_frame = pd.DataFrame(students, columns=students_headers)
	student_courses_data_frame = pd.DataFrame(student_courses, columns=student_courses_headers)
	courses_data_frame = pd.DataFrame(courses, columns=courses_headers)
	rooms_data_frame = pd.DataFrame(rooms, columns=rooms_headers)

	
	staff_list = list(staff_data_frame.staff.unique())					# set of staff/teachers
	courses = list(staff_course_data_frame.course.unique())				# set of courses
	course_types = list(courses_data_frame.Course_Department.unique())	# set of course types
	students = list(student_courses_data_frame.student.unique())		# set of students

	for i in range(len(course_types)):
		course_types[i] = re.sub(r'\W+', '', course_types[i])

	staff_course = {} 				# indicates whether or not a staff member teachers a course
	student_course = {}				# indicates whether or not a student is currently enrolled in a course
	core = {}						# indicates if a class is a core class
	PE = {}							# indicates if a class qualifies as PE
	immersion = {}					# indicates if a class is an immersion class
	ELL = {}						# indicates if a class is ELL
	SPED = {}						# indicates if a class if SPED
	core_type_indicator = {}		# indicates if a course is of a core type
	max_class_size = {}				# indicates what the max class size is for each class
	min_class_size = {}
	FTE = {}						# the number of FTE for each teacher
	numPeriods = {}					# the number of periods a teacher is currently teaching
	grade = {}						# the grade of each student
	grade_low = {}
	grade_high = {}

	print("Building dictionaries by course")
	count = 0
	status = 0.0
	for course in courses:
		for student in students:
			# check to see if this student/course match exists
			if ((student_courses_data_frame['student'] == student) & (student_courses_data_frame['course'] == course)).any():
				student_course[student, course] = 1
			else:
				student_course[student, course] = 0

		for staff in staff_list:
			# check to see if this staff/course match exists
			if ((staff_course_data_frame['staff'] == staff) & (staff_course_data_frame['course'] == course)).any():
				staff_course[staff, course] = 1
			else:
				staff_course[staff, course] = 0

		core[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'core'].values[0])
		PE[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'PE'].values[0])
		immersion[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'Immersion'].values[0])
		ELL[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'ELL'].values[0])
		SPED[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'SPED'].values[0])
		max_class_size[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'max_size'].values[0])
		min_class_size[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'min_size'].values[0])
		grade_low[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'grade_low'].values[0])
		grade_high[course] = int(courses_data_frame.loc[courses_data_frame['course'] == course, 'grade_high'].values[0])

		# check to see if this course is of this course type AND course is core
		for course_type in course_types:
			if core[course] == 1 and ((courses_data_frame['course'] == course) & (courses_data_frame['Course_Department'] == course_type)).any():
				core_type_indicator[course, course_type] = 1
			else:
				core_type_indicator[course, course_type] = 0

		print '{}%\r'.format(status),
		status = round((float(count) / float(len(courses))*100), 1)
		count += 1

	print("Building dictionaries by staff")
	FTE = {}						# the number of FTE for each teacher
	numPeriods = {}					# the number of periods a teacher is currently teaching
	for staff in staff_list:
		FTE[staff] = float(staff_data_frame.loc[staff_data_frame['staff'] == staff, 'FTE'].values[0])
		numPeriods[staff] = float(staff_data_frame.loc[staff_data_frame['staff'] == staff, 'periods'].values[0])

	print("Building dictionaries by student")
	grade = {}
	for student in students:
		grade[student] = int(students_data_frame.loc[students_data_frame['student'] == student, 'grade'].values[0])


	# put everything into a big dictionary
	data = {}

	data["staff_list"] = staff_list
	data["courses"] = courses
	data["course_types"] = course_types
	data["students"] = students
	data["staff_course"] = staff_course
	data["student_course"] = student_course
	data["core"] = core
	data["PE"] = PE
	data["immersion"] = immersion
	data["ELL"] = ELL
	data["SPED"] = SPED
	data["max_class_size"] = max_class_size
	data["min_class_size"] = min_class_size
	data["core_type_indicator"] = core_type_indicator
	data["FTE"] = FTE
	data["numPeriods"] = numPeriods
	data["grade"] = grade
	data["grade_low"] = grade_low
	data["grade_high"] = grade_high

	return data

def pickle_data(data, filepath):
	print("Pickling data to {}".format(filepath))
	pickle.dump(data, open(filepath, "w"))

if __name__ == '__main__':
	filepath = "./data/course_scheduling_data.p"

	data = get_data()
	pickle_data(data, filepath)
	
