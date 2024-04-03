import math
from .models import *
from rest_framework.permissions import BasePermission
from rest_framework import status
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.middleware.csrf import get_token
from django.contrib.auth.models import Group
from io import TextIOWrapper,BytesIO
from django.http import FileResponse
from datetime import datetime
import csv


# class to check if logged in user is a teacher
class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='teacher').exists()


# class to check if logged in user is a student
class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='student').exists()


# function for generating csrf token
def generate_csrf_token(request):
    csrf_token = get_token(request)
    return csrf_token


# function for generating initial email and password for user
def generate_email_password(first_name, last_name):
    email_base = first_name.lower() + "." + last_name.lower()
    email = email_base + "@goose.lt"

    counter = 1
    while CustomUser.objects.filter(email=email).exists():
        email = email_base + f"{counter}@goose.lt"
        counter += 1

    password =  CustomUser.objects.make_random_password()
    return email, password


# function for retrieving current school year's start and end date
def get_current_school_year():
    today = datetime.now().date()

    if today.month >= 9:  
        start_date = datetime(today.year, 9, 1).date()
    else:
        start_date = datetime(today.year - 1, 9, 1).date()

    if today.month >= 9:
        end_date = datetime(today.year+1, 8, 31).date() 
    else:
        end_date = datetime(today.year, 8, 31).date()

    return start_date, end_date  


# function for counting how many students of one class finished assignment
def get_completed_students_count(assignment):
    assignment_results = AssignmentResult.objects.filter(assignment=assignment)
    return assignment_results.values('student').distinct().count()


# function for calculating assignment status based on how many students have finished it
def get_assignment_status(assignment):
    completed_students_count = get_completed_students_count(assignment)
    total_students_count = CustomUser.objects.filter(classs=assignment.classs).count()
    if total_students_count == 0:
        return 'Bad'
    completion_percentage = (completed_students_count / total_students_count) * 100
    if completion_percentage >= 75:
        return 'Good'
    elif completion_percentage >= 50:
        return 'Average'
    else:
        return 'Bad' 


# function for checking if student answered all questions
def has_answered_all_questions(student, assignment):
    assignment_questions_count = QuestionAnswerPair.objects.filter(homework=assignment.homework).count()
    student_answers_count = QuestionAnswerPairResult.objects.filter(
        question__homework=assignment.homework,
        student=student,
        assignment=assignment
    ).count()
    return assignment_questions_count == student_answers_count, assignment_questions_count, student_answers_count        


# function for calculating how many points student scored just from answers
def calculate_score(student, assignment):
    try:
        question_results = QuestionAnswerPairResult.objects.filter(assignment=assignment, student=student)
        return sum(question_result.points for question_result in question_results)
    except QuestionAnswerPairResult.DoesNotExist:
        return 0


# function for calculating how many points assignment has in total
def calculate_assignment_points(assignment):
    try:
        questions = QuestionAnswerPair.objects.filter(homework=assignment.homework)
        return sum(question.points for question in questions)
    except QuestionAnswerPair.DoesNotExist:
        return 0


# function for calculating student's grade based on scored points and total points of assignment
def calculate_grade(score, assignment):  
    total_points = calculate_assignment_points(assignment)
    if total_points > 0:
        return min(math.ceil(score / total_points * 10), 10)
    return 0


# function for sorting students in leaderboard by points, time and name
def sort_students(student):
    if student['points'] == 0 and student['time'] == '00:00:00.000000':
        return (float('inf'), student.get('first_name', student.get('student_first_name', '')))
    else:
        return (-int(student['points']), student['time'], student.get('first_name', student.get('student_first_name', '')))      


# function for creating new option for a question
def create_correct_option(question_answer_pair, option):
        try:
            QuestionCorrectOption.objects.create(question=question_answer_pair, option=option)
        except ObjectDoesNotExist:
            return "", status.status.HTTP_500_INTERNAL_SERVER_ERROR, 'Nepavyko sukurti atsakymo pasirinkimo'


# function for calculating how many points did student scored from select multiple options question
def calculate_points_for_one_question_multiple_select(question, selected_options):
    total_points=0
    if len(selected_options) > 0:
        correct_options_temp = QuestionCorrectOption.objects.filter(question=question).values('option')
        correct_option_ids = correct_options_temp.values_list('option', flat=True)
        correct_options = Option.objects.filter(id__in=correct_option_ids)
        points_per_option = int(question.points/len(correct_options))

        correct_count_original = len(correct_options)
        correct_count_student = 0

        # checks all selected options and calculates points based on them
        for optioni in selected_options:
            if optioni in correct_options:
                total_points += points_per_option
                correct_count_student+=1
            else:
                correct_count_student-=1
                total_points -= points_per_option

        # fixes if any irregularities came during calculation
        if total_points<0:
            total_points=0     
        elif total_points>question.points:
            total_points=question.points  

        if correct_count_student == correct_count_original:
            total_points = question.points    

    else:
        total_points = 0   

    return total_points    


# function for calculating how many points student scored in select multiple options question
def process_answer(question, selected):
    total_points = 0
    selected_options = []
    if len(selected) > 0:
        selected_elements = selected.split(',')
        if len(selected_elements) == 1 :
            indexes = [int(selected_elements[0])]
        else:
            indexes = [int(element) for element in selected_elements]

        options = Option.objects.filter(question=question)
        selected_options = [options[index] for index in indexes]
        total_points = calculate_points_for_one_question_multiple_select(question, selected_options)

    return total_points, selected_options        


# function for creating or updating students and teachers by admin uploaded file
def update_or_create_members(file, school):
    processed_users = set()
    students_group, created = Group.objects.get_or_create(name='student')
    teachers_group, created = Group.objects.get_or_create(name='teacher')

    csv_file = TextIOWrapper(file, encoding='utf-8', errors='replace')
    reader = csv.reader(csv_file, delimiter=';')

    login_data =[]
    reader_list = list(reader)
    # reads each line and creates or updates user based on provided information
    if len(reader_list) > 0:
            for row in reader_list:
                if len(row) == 4 :
                    first_name = row[0]
                    last_name = row[1]
                    class_name = row[2]
                    gender = row[3]
                    gender = 1 if gender=='vyras' else 2    
                    role = 2 if class_name == '' else 1

                    login_user, email, password, classs = get_login_user(first_name, last_name, class_name, school, role)
                    try:    
                        # old user is not changed
                        user = CustomUser.objects.get(
                            first_name=first_name,
                            last_name=last_name,
                            role=role,
                            classs = classs
                        )
                        processed_users.add(user.id)

                    # creates new user
                    except ObjectDoesNotExist:
                        new_user = CustomUser.objects.create_user(
                            first_name=first_name,
                            last_name=last_name, 
                            gender=gender,
                            classs=classs if classs else None,
                            school=school,
                            password= password, 
                            email = email,
                            role=role,
                            username=email
                        )
                        processed_users.add(new_user.id)
                        login_data.append(login_user)
                        
                        # adds created user to student or teacher group for permissions
                        if class_name:
                            new_user.groups.add(students_group)
                        else:
                            new_user.groups.add(teachers_group)   

                else:
                    return Response({"error": "Neteisingai užpildytas duomenų failas"}, status=status.HTTP_400_BAD_REQUEST) 

            response = login_file(login_data)

            # deletes users who are not in file (they finished or transfered school for example)
            all_users = CustomUser.objects.filter(role__in=[1, 2], school=school)
            users_to_delete = all_users.exclude(id__in=processed_users)
            users_to_delete.delete()

            return response
    else:
        return Response({"error": "Tuščias duomenų failas"}, status=status.HTTP_400_BAD_REQUEST)         


# function for creating login credentials for user
def get_login_user(first_name, last_name, class_name, school, role):
    existing_class = Class.objects.filter(school=school, title=class_name).first()
    email, password = generate_email_password(first_name, last_name)
    classs = ''

    if not existing_class and class_name:
        classs = Class.objects.create(school=school, title=class_name)
    else:
        classs = existing_class
    
    login_user ={
        'name': first_name,
        'surname': last_name,
        'classs' : class_name,
        'email': email,
        'password' : password,
        'role' : role
    }    

    return login_user, email, password, classs


# function for creating response file with login credentials for each user
def login_file(login_data):
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

    content.write("{:<101}\n".format('-'*101).encode('utf-8'))
    content.seek(0)

    response = FileResponse(content, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment"'

    return response