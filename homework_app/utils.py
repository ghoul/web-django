import math
import re
from .models import *
from rest_framework.permissions import BasePermission
from django.db.models import Q, F, Exists,Subquery,Sum
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import status
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDict
from django.middleware.csrf import get_token
from io import BytesIO
from django.http import FileResponse


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='teacher').exists()

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='student').exists()

class LeaderboardEntry:
    def __init__(self, student, points, gender):
        self.student = student
        self.points = points
        self.gender = gender

class LeaderboardEntryEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, LeaderboardEntry):
            return obj.__dict__
        return super().default(obj)


def generate_csrf_token(request):
    csrf_token = get_token(request)
    return csrf_token


def generate_email_password(first_name, last_name):
    email_base = first_name.lower() + "." + last_name.lower()
    email = email_base + "@goose.lt"

    counter = 1
    while CustomUser.objects.filter(email=email).exists():
        email = email_base + f"{counter}@goose.lt"
        counter += 1

    password =  CustomUser.objects.make_random_password()
    return email, password

def get_completed_students_count(assignment):
    assignment_results = AssignmentResult.objects.filter(assignment=assignment)
    return assignment_results.values('student').distinct().count()

def get_assignment_status(assignment):
    completed_students_count = get_completed_students_count(assignment)
    total_students_count = StudentClass.objects.filter(classs=assignment.classs).count()
    if total_students_count == 0:
        return 'Bad'
    completion_percentage = (completed_students_count / total_students_count) * 100
    if completion_percentage >= 75:
        return 'Good'
    elif completion_percentage >= 50:
        return 'Average'
    else:
        return 'Bad' 

def has_answered_all_questions(student, assignment):
    assignment_questions_count = QuestionAnswerPair.objects.filter(homework=assignment.homework).count()
    student_answers_count = QuestionAnswerPairResult.objects.filter(
        question__homework=assignment.homework,
        student=student,
        assignment=assignment
    ).count()
    return assignment_questions_count == student_answers_count, assignment_questions_count, student_answers_count        

def calculate_score(student, assignment):
    try:
        question_results = QuestionAnswerPairResult.objects.filter(assignment=assignment, student=student)
        return sum(question_result.points for question_result in question_results)
    except QuestionAnswerPairResult.DoesNotExist:
        return 0

def calculate_assignment_points(assignment):
    try:
        questions = QuestionAnswerPair.objects.filter(homework=assignment.homework)
        return sum(question.points for question in questions)
    except QuestionAnswerPair.DoesNotExist:
        return 0

def calculate_grade(score, assignment):  
    total_points = calculate_assignment_points(assignment)
    if total_points > 0:
        return min(math.ceil(score / total_points * 10), 10)
    return 0

# def sort_students(student):
#     if student['points'] == '' or student['time'] == '':
#         return (float('inf'), float('inf'))
#     else:
#         return (-int(student['points']) if student['points'] else 0, student['time'] if student['time'] else '99:99:99')    

# def sort_students(student):
#     if student['points'] == '' or student['time'] == '':
#         # Prioritize students who haven't finished their assignments
#         return (float('inf'), student['first_name'])
#     else:
#         # Prioritize students who finished their assignments
#         return (-int(student['points']), student['time'], student['first_name'])

def sort_students(student):
    if student['points'] == 0 and student['time'] == '00:00:00.000000':
        return (float('inf'), student.get('first_name', student.get('student_first_name', '')))
    else:
        print("yra points or time")
        # Prioritize students who finished their assignments
        return (-int(student['points']), student['time'], student.get('first_name', student.get('student_first_name', '')))

def get_current_school_year():
    today = datetime.now().date()

    # Calculate the start date for the school year
    if today.month >= 9:  # If it's September or later in the current year
        start_date = datetime(today.year, 9, 1).date()  # This year's September 1st
    else:
        start_date = datetime(today.year - 1, 9, 1).date()  # Last years ago September 1st

    # Calculate the end date for the school year
    if today.month >= 9:  # If it's September or later in the current year
        end_date = datetime(today.year+1, 8, 31).date()  # Next year's August 31st
    else:
        end_date = datetime(today.year, 8, 31).date()  # This year's August 31st
        print(start_date)
        print(end_date)
    return start_date, end_date        


def create_correct_option(question_answer_pair, option):
        try:
            print("Before correct option crete")
            QuestionCorrectOption.objects.create(question=question_answer_pair, option=option)
            print("After correct option crete")
        except ObjectDoesNotExist:
            return {'success': False, 'error': 'Failed to create correct option'}, status.HTTP_500_INTERNAL_SERVER_ERROR   

def login_file(login_data, school):
    headersS = ["Vardas", "Pavardė", "Klasė", "El.Paštas", "Slaptažodis"]
    headersM = ["Vardas", "Pavardė", "El.Paštas", "Slaptažodis"]

    content = BytesIO()
    content.write("{:<91}\n".format('-'*91).encode('utf-8'))
    content.write("{:^91}\n".format("MOKYTOJAI").encode('utf-8'))
    content.write("{:<91}\n".format('-'*91).encode('utf-8'))
    content.write("{:<20}{:<20}{:<40}{:<10}\n".format(*headersM).encode('utf-8'))
    content.write("{:91}\n".format('-'*91).encode('utf-8'))

    for user in login_data:
        if user['role'] ==2:
            content.write("{:<20}{:<20}{:<40}{:<10}\n".format(
                str(user['name']),
                str(user['surname']),
                str(user['email']),
                str(user['password'])
            ).encode('utf-8'))    
    content.write("{:<91}\n".format('-'*91).encode('utf-8'))
    content.write("{:<101}\n".format(' '*101).encode('utf-8'))
    content.write("{:<101}\n".format('-'*101).encode('utf-8'))
    content.write("{:^101}\n".format("MOKINIAI").encode('utf-8'))
    content.write("{:<101}\n".format('-'*101).encode('utf-8'))
    content.write("{:<20}{:<20}{:<10}{:<40}{:<10}\n".format(*headersS).encode('utf-8'))
    content.write("{:<101}\n".format('-'*101).encode('utf-8'))

    for user in login_data:
        if user['role'] ==1:
            content.write("{:<20}{:<20}{:<10}{:<40}{:<10}\n".format(
                str(user['name']),
                str(user['surname']),
                str(user['classs']),
                str(user['email']),
                str(user['password'])
            ).encode('utf-8'))
    # Seek to the beginning of the buffer before creating the FileResponse
    content.write("{:<101}\n".format('-'*101).encode('utf-8'))
    content.seek(0)

    date_string = datetime.now().strftime("%Y-%m-%d")
    filename = f"login_credentials_{school.title}_{date_string}.txt"

    # Create a response with the file as an attachment
    response = FileResponse(content, content_type='text/plain; charset=utf-8')
    # response['Content-Disposition'] = 'attachment; filename="login_credentials_{school.title}_{date}.txt"'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    # response['FormattedTitle'] = filename

    return response

def calculate_points_for_one_question_multiple_select(question, all_options, selected_options):
    total_points=0
    if selected_options.count() > 0:
        points_per_option = (question.points/all_options.count())
        correct_options = QuestionCorrectOption.objects.filter(question=question)

        for optioni in selected_options:
            if optioni in correct_options:
                correct_count += 1
                total_points += points_per_option
            else:
                total_points -= points_per_option

        if total_points<0:
            total_points=0     
        elif total_points>question.points:
            total_points=question.points  

    else:
        total_points = 0   

    return total_points    


def classes_year_changes():
    classes = Class.objects.all()
    for classs in classes:
        old_title = classs.title
        match = re.match(r'(\d+)(\D*)', old_title)
    
        if match:
            numeric_part, non_numeric_part = match.groups()

            new_numeric_part = str(int(numeric_part) + 1)
            if numeric_part>12:
                classs.delete()
            else:               
                new_title = new_numeric_part + non_numeric_part
                classs.title=new_title
                classs.save()

     