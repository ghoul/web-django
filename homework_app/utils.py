import math
from .models import *
from rest_framework.permissions import BasePermission
from django.db.models import Q, F, Exists,Subquery,Sum
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import status
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDict


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

def sort_students(student):
    if student['score'] == '' or student['time'] == '':
        return (float('inf'), float('inf'))
    else:
        return (-int(student['score']) if student['score'] else 0, student['time'] if student['time'] else '99:99:99')    

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




     