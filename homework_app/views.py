from ast import Assign
import math
import subprocess
from datetime import datetime, timedelta
import email
import json
from turtle import st
from urllib import response
from urllib.parse import ParseResultBytes
from xml.etree.ElementTree import Comment
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse,HttpResponseNotFound, HttpResponseBadRequest,HttpResponseServerError
from homework_app.models import Homework,QuestionAnswerPair, Class, StudentClass, AssignmentResult, QuestionCorrectOption,School, Assignment,StudentTeacher,StudentTeacherConfirm,QuestionAnswerPairResult
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie

import logging
import re
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from rest_framework_simplejwt.tokens import Token
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenObtainPairView

from homework_app.utils import *
from .models import CustomUser, Option, QuestionSelectedOption
import jwt 
from django.conf import settings
from django.db.models import Q, F, Exists,Subquery,Sum
from datetime import date, time
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
import csv
from io import TextIOWrapper,StringIO,BytesIO
from django.http import FileResponse
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import permission_required
from django.middleware.csrf import get_token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from rest_framework_simplejwt.authentication import JWTAuthentication, JWTTokenUserAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework.authentication import  SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.mixins import PermissionRequiredMixin
from rest_framework import mixins
from rest_framework import viewsets

def generate_csrf_token(request):
    csrf_token = get_token(request)
    return csrf_token

logger = logging.getLogger(__name__)


def generate_email_password(first_name, last_name):
    email_base = first_name.lower() + "." + last_name.lower()
    email = email_base + "@goose.lt"

    counter = 1
    while CustomUser.objects.filter(email=email).exists():
        email = email_base + f"{counter}@goose.lt"
        counter += 1

    password =  CustomUser.objects.make_random_password()
    return email, password



class AssignmentListViewTeacher(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         

    def get_queryset(self):
        return Assignment.objects.filter(
            homework__teacher=self.request.user, 
            to_date__gte=date.today(),  
        )
    serializer_class = AssignmentSerializer

class AssignmentListViewStudent(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsStudent]         
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        student_classes = Class.objects.filter(classs__student=self.request.user)
        finished_assignments = AssignmentResult.objects.filter(student=self.request.user).values('assignment')

        return Assignment.objects.filter(
            classs__in=student_classes,
            from_date__lte=date.today(), 
            to_date__gte=date.today()  
        ).exclude(
            id__in=Subquery(finished_assignments)
        )
    
class AssignmentListViewTeacherFinished(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         

    def get_queryset(self):
        return Assignment.objects.filter(
        homework__teacher = self.request.user,
        to_date__lte=date.today(),
    )
    serializer_class = AssignmentSerializer

class AssignmentListViewStudentFinished(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsStudent]         
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        student_classes = Class.objects.filter(classs__student=self.request.user)
        finished_assignments = AssignmentResult.objects.filter(student=self.request.user).values_list('assignment__id', flat=True)

        return Assignment.objects.filter(
            Q(classs__in=student_classes) &  # Filter by classes associated with the student
            (Q(to_date__lt=date.today()) | Q(id__in=finished_assignments))  # Past or finished assignments
        )

class AssignmentView(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         
    serializer_class = AssignmentSerializer
    def get_queryset(self):
        return Assignment.objects.all() #filter pagal teacher
        # assignment_id = self.kwargs.get('pk')
        # return Assignment.objects.get(id=assignment_id)

class ClassesListView(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         
    serializer_class = ClassSerializer
    def get_queryset(self):
        return Class.objects.filter(school = self.request.user.school)

class ProfileViewUser(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] 
    serializer_class = UserSerializer        
    def get_queryset(self):
        return CustomUser.objects.all() #self.request.user


@api_view(['POST'])
@require_POST
@csrf_exempt
def login_user(request):
    print("loginn")
    user = CustomUser.objects.get(email=request.data['email'])
    if not user.check_password(request.data['password']):
        print("loginn bad")
        return Response({'error': 'Neteisingas prisijungimo vardas arba slaptažodis'}, status=401)     

    # user = authenticate(request, email=request.data['email'], password=request.data['password'])
    # if not user:
    #     print("bad login")
    #     return Response({'error': 'Neteisingas prisijungimo vardas arba slaptažodis'}, status=401)     

    license_end = user.school.license_end
    if license_end>datetime.today().date():
        login(request, user)
        serializer = LoginUserSerializer(instance=user)    
        token, created = Token.objects.get_or_create(user=user)
        csrf_token = generate_csrf_token(request)
        print(token.key)
        print("loginn2")

        return Response({"token": token.key, "user": serializer.data, "csrf_token": csrf_token})
    else:
        return Response({'error': 'Jūsų licenzija nebegalioja'}, status=401)           



    


#PAVYZDYS
@csrf_exempt
# @require_PUT
@api_view(['PUT'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def change_password(request):
    if request.method == 'PUT':
        new_password = request.data['password']
        user = request.user

        if not new_password:
            return JsonResponse({'success': False, 'error': 'Klaida! Visi laukai privalomi'}, status=400)

        if not user.check_password(new_password):
            user.set_password(new_password)
        else:
            return JsonResponse({'success': False, 'error': "Klaida! Naujas slaptažodis negali būti toks pats kaip senas slaptažodis"})    
        
        try:
            user.save()
            return JsonResponse({'success': True, "id": user.pk}, status=200)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


def home(request):
    return HttpResponse("Hello, Django!")


def has_answered_all_questions(student, assignment):
    assignment_questions_count = QuestionAnswerPair.objects.filter(homework=assignment.homework).count()
    student_answers_count = QuestionAnswerPairResult.objects.filter(
        question__homework=assignment.homework,
        student=student,
        assignment=assignment
    ).count()
    return assignment_questions_count == student_answers_count, assignment_questions_count, student_answers_count

def sort_students(student):
    if student['scored'] == '' or student['time'] == '':
        return (float('inf'), float('inf'))
    else:
        return (-int(student['scored']) if student['scored'] else 0, student['time'] if student['time'] else '99:99:99')

@csrf_exempt
def get_assignment_statistics(request,pk):
    token = request.headers.get('Authorization')   
    if not token:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        # Verify and decode the token
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

    # Check if the user is an admin
    role = payload.get('role')
    email = payload.get('email')
    user = CustomUser.objects.get(email=email)
    assignment = Assignment.objects.get(pk=pk)
    classs_title = assignment.classs.title
    assingment_title = assignment.homework.title

    if request.method == 'GET':
        classs = assignment.classs
        students_in_class = classs.classs.all()
        results = AssignmentResult.objects.filter(assignment=assignment)

        homework = assignment.homework
        total_points = QuestionAnswerPair.objects.filter(homework=homework).aggregate(total_points=Sum('points'))['total_points']
        students_data = []

        for student in students_in_class:
        # Filter AssignmentResult for the current student and assignment
            student_results = results.filter(student=student.student)
            date = ''
            time = ''
            points = ''
            status = 'Bad'
            gender = student.student.gender
            grade = 0

            print(gender)

            if student_results.exists():
                answered_all, all_questions, student_result = has_answered_all_questions(student.student, assignment)
                if answered_all:
                    status = 'Good'
                else: 
                    status = 'Average'
                # Extracting the date and time from the first result
                date = student_results.first().date.strftime('%Y-%m-%d') 
                time = student_results.first().time.strftime('%H:%M:%S')  

                # Calculate total points for the student
                scored_points_total = student_results.first().points
                points = QuestionAnswerPairResult.objects.filter(
                    assignment=assignment,
                    student=student.student, 
                ).aggregate(total_points=Sum('points'))['total_points']
                print(student.student.last_name + " points: " + str(points))
                
                if total_points >0:
                    grade = math.ceil(points/total_points*10)
                else:
                    grade = 0
                grade = min(grade, 10)

            students_data.append({
                'id': student.student.pk,
                'name': student.student.first_name,
                'surname': student.student.last_name,
                'date': date,
                'time': time,
                'points': points,
                'status': status, 
                'gender' : gender,
                'grade' : grade,
                'scored' : scored_points_total
            })

            students_data = sorted(students_data, key=sort_students)
        return JsonResponse({'students': students_data, 'title': assingment_title, 'classs' : classs_title, 'id' : user.id}) 

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

@csrf_exempt
def get_class_statistics(request):
    token = request.headers.get('Authorization')   
   
    payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
    email = payload.get('email')
    role=payload.get('role')
    user = CustomUser.objects.get(email=email)
    if request.method == 'GET':
        if role==1:
            print("mokinio leaderboard")
            try:
                # Step 1: Get the class of the student who sent the request
                student_class = StudentClass.objects.get(student=user)
                classs = student_class.classs.title

                # Step 2: Retrieve all the assignments for that class
                assignments = Assignment.objects.filter(classs=student_class.classs)

                # Step 4: Calculate points for each student in the class
                leaderboard_entries = []
                student_ids = StudentClass.objects.filter(classs=student_class.classs).values_list('student', flat=True)
                students = CustomUser.objects.filter(pk__in=student_ids)

                # Step 3: Filter assignment results based on the school year and class
                start_date, end_date = get_current_school_year()
                assignment_results = AssignmentResult.objects.filter(
                    student__in=students,
                    assignment__in=assignments,
                    date__range=(start_date, end_date)
                )

                for student in students:
                    points = assignment_results.filter(student=student).aggregate(Sum('points'))['points__sum'] or 0
                    print(points)
                    leaderboard_entries.append(LeaderboardEntry(f'{student.first_name} {student.last_name}', points, student.gender))

                # Step 5: Create a leaderboard
                leaderboard_entries.sort(key=lambda x: x.points, reverse=True)
                print("success")

                serialized_leaderboard_entries = json.dumps(leaderboard_entries, cls=LeaderboardEntryEncoder,ensure_ascii=False)

                return JsonResponse({'data': serialized_leaderboard_entries, 'classs' : classs}, safe=False)
            except StudentClass.DoesNotExist:
                return JsonResponse({'error': 'Student class not found'}, status=404)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)

        elif role==2:
            print("mokytojo leaderboard")



@csrf_exempt
def handle_assignment_update(request,aid):
    token = request.headers.get('Authorization')   
    if not token:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

    if request.method == 'GET':
        assignment = Assignment.objects.get(pk=aid)   
        assignment_info = {
            'id': assignment.pk,
            'title': assignment.homework.title,
            'fromDate': assignment.from_date,
            'toDate': assignment.to_date,
            'classs': assignment.classs.pk
        }
        return JsonResponse({'data': assignment_info}) 
    elif request.method == 'PUT':
            assignment = Assignment.objects.get(pk=aid)  
            try:
                data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

            toDate = data.get("toDate")
            fromDate = data.get("fromDate")
            classId = data.get("class")

            classs = Class.objects.get(pk=classId)

            if not toDate or not fromDate or not classId:
                return JsonResponse({'success': False, 'error': 'All fields are required'}, status=422)

            assignment.to_date = toDate
            assignment.from_date = fromDate
            assignment.classs = classs

            try:
                assignment.save()
                return JsonResponse({'success': True, "id" : assignment.pk}, status=200)
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500) 


@csrf_exempt
# @ensure_csrf_cookie
def handle_homework(request):
    token = request.headers.get('Authorization')   
    if not token:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        # Verify and decode the token
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

    # Check if the user is an admin
    role = payload.get('role')
    email = payload.get('email')
    teacher = CustomUser.objects.get(email=email)

    if request.method == 'GET':
        homework = Homework.objects.filter(teacher=teacher)
        homework_data = [
                {'id' : hw.pk, 'title': hw.title, 'questions': calculate_question_count(hw.pk)}
                for hw in homework
            ]
        return JsonResponse({'homework': homework_data}) 
    elif request.method == 'POST':
     
        homework_name = request.POST.get('homeworkName')
        date = datetime.now().date()

        # Create a new homework object
        homework = Homework.objects.create(title=homework_name, date=date, teacher=teacher)


        num_pairs = sum('question' in key for key in request.POST.keys())
        print(num_pairs)
       
        for i in range(num_pairs):
            qtype = request.POST.get(f'pairs[{i}][qtype]')
            print(qtype)
            question = request.POST.get(f'pairs[{i}][question]')
            image = request.FILES.get(f'pairs[{i}][image]')
            points = request.POST.get(f'pairs[{i}][points]')

            if qtype == 'select':
                qtype=1
            elif qtype == 'write':
                qtype=2   
            elif qtype == 'multiple':
                qtype=3  
            #multipleOptionIndex vieno klausimo
            num_mult = sum(key.startswith(f'pairs[{i}][multipleOptionIndex]') for key in request.POST.keys())
            print(str(i) + " num mult: " + str(num_mult))
            # Create a question-answer pair object and associate it with the homework
            qapair = QuestionAnswerPair.objects.create(
                homework=homework,
                qtype=qtype,
                question=question,
                image=image,
                points=points
            )
       
            if qtype == 1:  # Select question

                num_options = sum(key.startswith(f'pairs[{i}][options]') for key in request.POST.keys())
                print(num_options)
                options = []
                for option_i in range(num_options):
                    option_text = request.POST.get(f'pairs[{i}][options][{option_i}]')
                    option = Option.objects.create(text=option_text, question=qapair)
                    options.append(option)

                correct_option_index = int(request.POST.get(f'pairs[{i}][correctOptionIndex]'))
                try:
                    if 0 <= correct_option_index < len(options):
                        qapair.correct = options[correct_option_index]
                        qapair.save()
                except ObjectDoesNotExist:
                    return JsonResponse({'success': False, 'error': 'Correct option not found'}, status=400)

            elif qtype == 2:
                qapair.answer = request.POST.get(f'pairs[{i}][answer]')
                qapair.save()     

            elif qtype == 3:  # multiple select question

                num_options = sum(key.startswith(f'pairs[{i}][options]') for key in request.POST.keys())
                print("multiple : " + str(num_options))
                options = []
                for option_i in range(num_options):
                    option_text = request.POST.get(f'pairs[{i}][options][{option_i}]')
                    option = Option.objects.create(text=option_text, question=qapair)
                    options.append(option)
                    #tikrint for multipleindexes ar nera i question option ir tada tikrint ar ia ta pati kuria rado 
                    #ir jei ta pati, tai sukurt optioncorrect objekta
                    for y in range(num_mult):
                        
                        correct = int(request.POST.get(f'pairs[{i}][multipleOptionIndex][{y}]'))
                        print("correct: " + str(correct))
                        print("optioni: " + str(option_i))
                        if correct==option_i:
                           QuestionCorrectOption.objects.create(question=qapair, option = option)
                            

        return JsonResponse({'success': True, 'message': 'Operation successful!'})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)


def calculate_question_count(homework_id):
    question_count = QuestionAnswerPair.objects.filter(homework_id=homework_id).count()
    return question_count

#TODO:
@csrf_exempt
def handle_homework_id(request, pk):
    if request.method=="PUT":
        try:
            homework = Homework.objects.get(pk=pk)
        except Homework.DoesNotExist:
            return JsonResponse({'message': 'Homework not found'}, status=404)

        data = json.loads(request.body)
        homework_name = data['homeworkName']
        correct = data['correct']
        multiple = data['multiple']

        if homework_name:
            homework.title = homework_name
            homework.save()
        else:
            return JsonResponse({'message': 'Homework name is required'}, status=400)

        received_pairs = data.get('pairs', [])
        existing_pairs = QuestionAnswerPair.objects.filter(homework=homework)

        # Extract IDs from received pairs
        received_pair_ids = set(pair.get('id') for pair in received_pairs if pair.get('qid'))

        # Check and delete pairs that are missing from received data
        for existing_pair in existing_pairs:
            if existing_pair.id not in received_pair_ids:
                existing_pair.delete()

        for index, pair in enumerate(received_pairs):
            question = pair.get('question')
            answer = pair.get('answer')
            image = pair.get('image')
            points = pair.get('points')
            qtype = pair.get('type')

            if qtype=='select':
                qtype=1
            elif qtype=='write':
                qtype=2
            elif qtype=='multiple':
                qtype=3        
          
            pair_obj, created = QuestionAnswerPair.objects.get_or_create(
                homework=homework,
                id=pair.get('qid'),
                defaults={
                    'qtype': qtype,
                    'question': question,
                    'image': image,
                    'points': points,
                    'answer': answer
                }
            )

            if not created:
                if pair_obj.qtype != qtype:
                    Option.objects.filter(question=pair_obj).delete()
                    QuestionCorrectOption.objects.filter(question=pair_obj).delete()

                pair_obj.qtype = qtype                   
                pair_obj.question = question
                pair_obj.answer = answer
                pair_obj.image = image
                pair_obj.points = points
                pair_obj.save()
            
            if qtype == 1:
                options = pair.get('options', [])
                correct_option_index = correct[index]

                options_old = Option.objects.filter(question=pair_obj)
                options_old.delete()

                for option_text in options:
                    option = Option.objects.create(text=option_text, question=pair_obj)

                if 0 <= correct_option_index < len(options):
                    pair_obj.correct = Option.objects.get(text=options[correct_option_index], question=pair_obj)
                    pair_obj.save()

            elif qtype == 3:
                options = pair.get('options', [])
                print(multiple)
                print(index)
                correct_option_indexes = [item['oid'] for item in multiple if item.get('qid') == index]
                print(correct_option_indexes)

                options_old = Option.objects.filter(question=pair_obj)
                options_old.delete()

                for option_text in options:
                    option = Option.objects.create(text=option_text, question=pair_obj)

                for correct_option_index in correct_option_indexes:
                    QuestionCorrectOption.objects.create(question=pair_obj, option=Option.objects.get(text=options[correct_option_index], question=pair_obj))

        return JsonResponse({'success': True, 'message': 'Operacija atlikta sėkmingai!'})

    elif request.method=="DELETE":
        homework = Homework.objects.get(pk=pk)
        homework.delete()
        return JsonResponse({'success': True})

    elif request.method=="GET":
        homework = Homework.objects.get(pk=pk)
        questions = get_homework_questions(homework)
        edit = True

        assignments = Assignment.objects.filter(homework=homework)
        if assignments.exists():
            edit=False
    
        return JsonResponse({'success': True, 'homework': questions, 'edit' : edit}, safe=True)


def get_homework_questions(homework):
        homework_data = []
        questions = QuestionAnswerPair.objects.filter(homework=homework)

        for question in questions:
            options=[]
            correct = ''
            correctMultiple = []
            if question.qtype==1 or question.qtype==3:
                options = Option.objects.filter(question=question).values_list('text', flat=True)
                options=list(options)

            if question.qtype ==1:    
                correct = question.correct.text
            elif question.qtype == 3:
                #surast visus teisingu indeksus ir sudet i array
                correctOptions = QuestionCorrectOption.objects.filter(question=question).values_list('option__text', flat=True).distinct() #.values_list('option__id', flat=True)
    
                indexes = [(index) for index, obj in enumerate(options) if obj in correctOptions]
                
                correctMultiple = indexes
                print("correctmultiplle: " + ', '.join(map(str, correctMultiple)))


            question_info = {
                'qid' : question.pk,
                'question': question.question,
                'type': question.qtype,
                'options': options,
                'answer' : question.answer,
                'correct' : correct,
                'correctMultiple' : correctMultiple,
                'points' : question.points
            }
            homework_data.append(question_info)

   
        questions_data = {
                'title': homework.title,
                'pairs': list(homework_data)
            }
        print(questions_data)
        return questions_data

@csrf_exempt
def handle_assign_homework(request):
    token = request.headers.get('Authorization')   
    if not token:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        # Verify and decode the token
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

    # Check if the user is an admin
    role = payload.get('role')
    email = payload.get('email')
    teacher = CustomUser.objects.get(email=email)
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        classs_id = data.get("class")
        homework_id = data.get("homeworkId")
        fromDate = data.get("fromDate")
        toDate = data.get("toDate")

   

        classs = Class.objects.get(pk=classs_id)
        homework = Homework.objects.get(pk=homework_id)

        assignment = Assignment(classs=classs, homework=homework, from_date=fromDate, to_date=toDate)
        assignment.save()
        return JsonResponse({'success' : True, 'message': 'Operacija sėkminga!'})

@csrf_exempt
def handle_assignment_id(request,id):
    token = request.headers.get('Authorization') 
    if not token:
        userId=0
    else:    
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
        email=payload.get('email')
        userId = CustomUser.objects.get(email=email).pk
    if request.method == 'GET':
        homework = Assignment.objects.get(pk=id).homework
     
        questions_data = get_homework_questions(homework)
        return JsonResponse({'questions': questions_data, 'uid' : userId, 'success' : True}) 


@csrf_exempt
def handle_test_answers(request):
    if request.method == 'POST':
        aid = request.POST.get('assignmentId')
        elapsed = float(request.POST.get('time'))/1000
        print(elapsed)
        token = request.headers.get('Authorization')   
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
        email = payload.get('email')
        student = CustomUser.objects.get(email=email)
        print(aid)
        date = datetime.now()
        assignment = Assignment.objects.get(pk=aid)
        homework=assignment.homework
        questions = QuestionAnswerPair.objects.filter(homework=homework)

        total_points = 0
       
        for i, questionOG in enumerate(questions):
            qid = request.POST.get(f'pairs[{i}][questionId]')
            answer = request.POST.get(f'pairs[{i}][answer]')    
            question = questions.get(pk=qid)
            qtype=question.qtype
            points = question.points
            get_points = 0
            answerOG = ''
            answersUser = []
            new = False
            try:
                answered_before = QuestionAnswerPairResult.objects.get(question=question, assignment=assignment, student=student)
                answered_before.delete()
                selected = QuestionSelectedOption.objects.filter(assignment=assignment, student=student, question=question)
                selected.delete()
            except ObjectDoesNotExist:
                new = True
                
            if qtype == 1: #select
                answerOG = question.correct.text
            elif qtype == 2: #write
                answerOG = question.answer


            elif qtype ==3:
                answer=''
                options = Option.objects.filter(question=question)
                options =list(options)
                correctOptions = QuestionCorrectOption.objects.filter(question=question)
                correctOptions=list(correctOptions)

                originIndexes = []

                for  j, option in enumerate(options):
                    for y, correctOp in enumerate(correctOptions):
                        if option==correctOp.option:
                            originIndexes.append(j)

                points /= len(originIndexes) if originIndexes else 1   
                print("points: " + str(points))  
                num_mult = sum(key.startswith(f'pairs[{i}][multipleIndex]') for key in request.POST.keys())
                for y in range(num_mult):
                    optionIndex = int(request.POST.get(f'pairs[{i}][multipleIndex][{y}]'))
                    answersUser.append(optionIndex)
                    option = options[optionIndex]
                    
                    saveSelected = QuestionSelectedOption.objects.create(assignment=assignment, student=student, question=question, option=option)   
                print(answersUser)
                print(originIndexes)
                for optionIndex in answersUser:
                    if optionIndex in originIndexes:
                        print(optionIndex)
                        get_points+=points
                        print("getpoints: " + str(get_points))

                #jei per daug pasirenka
                if len(answersUser)>len(originIndexes):
                    wrongC = len(answersUser)-len(originIndexes)
                    minusPoints = question.points/len(options)
                    for w in range(wrongC):
                        get_points-=minusPoints 

                #arba jei nei vieno teisingo nepasirinko: 0 automatiskai               

                total_points+=get_points    

            if qtype==1 or qtype==2:
                if answerOG == answer:
                    get_points=points

                total_points+=get_points  


            QuestionAnswerPairResult.objects.create(question=question, assignment=assignment, student=student, answer=answer, points=get_points)
            get_points=0
        elapsed_timedelta = timedelta(seconds=elapsed)

        # Extract hours, minutes, and seconds from the timedelta
        hours, remainder = divmod(elapsed_timedelta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Create a string representation of the elapsed time
        formatted_time = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

        assignmentResult = AssignmentResult.objects.create(assignment=assignment, student=student, date=date, points=total_points, time=formatted_time)

    return JsonResponse({'success': True, 'id': assignmentResult.pk})



@csrf_exempt
def get_classes_by_school(request):
    token = request.headers.get('Authorization')   
    if not token:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        # Verify and decode the token
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

    # Check if the user is an admin
    role = payload.get('role')
    email = payload.get('email')
    teacher = CustomUser.objects.get(email=email)
    school=teacher.school
    if request.method == 'GET':
        try:
            classes = Class.objects.filter(school=school)
            data = [
            {
                'title': classs.title,
                'id': classs.pk
            }
            for classs in classes
        ]
            return JsonResponse(data, safe=False, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)


#ADMIN TODO??
@csrf_exempt
def handle_classes(request):
    token = request.headers.get('Authorization')   
    if not token:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        # Verify and decode the token
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

    # Check if the user is an admin
    role = payload.get('role')
    email = payload.get('email')
    teacher = CustomUser.objects.get(email=email)
    school = teacher.school
    if request.method=="POST":
        #if(role=="2" or role=="3"):
        data = json.loads(request.body.decode('utf-8'))
        title = data.get("title")
        classs = Class(title=title, school=school)
        classs.save()
        return JsonResponse({'success' : True, 'message': 'Operacija sėkminga!'})
    elif request.method == 'GET':
        try:
            #TODO: tik mokytojo klasės
            #classes = Class.objects.all().values('id', 'title')
            classes = Class.objects.filter(school=school).values('id', 'title')
            classes_list = list(classes)
            return JsonResponse(classes_list, safe=False, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

#TODO? 
@csrf_exempt
def handle_classes_id(request, pk):
    token = request.headers.get('Authorization')   
    if not token:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
    try:
        # Verify and decode the token
        payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

    # Check if the user is an admin
    role = payload.get('role')

    if request.method == 'GET':
        try:
            classs = Class.objects.get(pk=pk)
        except Class.DoesNotExist:
            return HttpResponseNotFound("Class not found")
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

        data = {
            'title': classs.title
        }
        return JsonResponse(data, status=200)

    elif request.method == 'DELETE':
        if(role==2 or role==3):
            try:
                classs = Class.objects.get(pk=pk)
            except Class.DoesNotExist:
                return HttpResponseNotFound("Class not found")
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
        else:
            return JsonResponse({'success': False, 'error': 'Unauthorized access to delete classs'}, status=403)         

        classs.delete()
        return HttpResponse(status=204)

    elif request.method == 'PUT':
        if(role=="1" or role=="2" or role=="3"): #TODO: ISIMT 1
            try:
                classs = Class.objects.get(pk=pk)
            except Class.DoesNotExist:
                return HttpResponseNotFound("Class not found")

            try:
                data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

            new_title = data.get("title")

            if not new_title:
                return JsonResponse({'success': False, 'error': 'All fields are required'}, status=422)

            classs.title = new_title

            try:
                classs.save()
                return JsonResponse({'success': True, "id" : classs.pk}, status=200)
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            return JsonResponse({'success': False, 'error': 'Unauthorized access to update classs'}, status=403)   
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)        

#TODO? 
@csrf_exempt
def handle_students_class(request,sid,cid):
    #TOOD: perkelt i kit metoda
    if request.method == 'GET':
        classs = get_object_or_404(Class, pk=cid)

        # Step 2: Filter StudentClass instances based on the class
        student_class_instances = StudentClass.objects.filter(classs=classs)

        # Step 3: Retrieve the associated CustomUser instances
        student_users = [student.student for student in student_class_instances]

        # If you want to retrieve distinct CustomUser instances, use set() to remove duplicates
        students_in_class = list(set(student_users))

        # students_in_class = CustomUser.objects.filter(studentclass__classs__id=cid)
        students_data = [
            {'id' : student.pk, 'name': student.first_name, 'surname': student.last_name}
            for student in students_in_class
        ]
        return JsonResponse({'students': students_data})
        
    elif request.method == 'DELETE':
        try:
            student_class_entry = get_object_or_404(StudentClass, student_id=sid, classs_id=cid)
            student_class_entry.delete()
            # return HttpResponse(status=204)
            return JsonResponse({'successs': True})
        except StudentClass.DoesNotExist:
            return HttpResponseNotFound("StudentClass not found")
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

@csrf_exempt
def get_user_id(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_email = data['user_email']
        user_id = CustomUser.objects.get(email=user_email).pk
        return JsonResponse({'user_id': user_id})



@csrf_exempt
def handle_students_assignment_results(request,aid):
    if request.method == 'GET':
        assignment = Assignment.objects.get(pk=aid)
        assignmentResults = AssignmentResult.objects.filter(assignment=assignment)

        students_data = [
            {'id' : result.pk, 'name': result.student.first_name, 'surname': result.student.last_name, 'date' : result.date, 'time': result.time, 'points':result.points}
            for result in assignmentResults
        ]
      
        return JsonResponse({'success': True, 'results': students_data}) 
    #TODO: IS ZAIDIMO KREIPIASI I SITA PASIBAIGUS UZDUOTIM
    elif request.method == 'POST':
        assignment = Assignment.objects.get(pk=aid)
        data = json.loads(request.body)
        student_id = data['student_id']
        student = CustomUser.objects.get(pk=student_id)
        date = data['date']
        time = data['time']
        points = data['points']

        result = AssignmentResult.objects.create(assignment=assignment, student=student, date=date, time=time, points=points)
      
        return JsonResponse({'success': True, 'result': result})       

@csrf_exempt
def get_one_student_answers(request,aid,sid):
    if request.method == 'GET':
        student = CustomUser.objects.get(pk=sid)
        name = student.first_name + " " + student.last_name
        question_answer_pairs = QuestionAnswerPair.objects.filter(homework__assignment__id=aid)
        assignment = Assignment.objects.get(pk=aid)  
        # Retrieve QuestionAnswerPairResult objects for a given assignment and student
        question_answer_results = QuestionAnswerPairResult.objects.filter(
            assignment__id=aid, student__id=sid
        )

        print(question_answer_results)

        #jei klausimas multiple - atsakymu masyvas kitas, reikia tikrint tipa ir jei 3 - pasiimt studento atsakymus
        # student_choice = QuestionSelectedOption.objects.filter(question=pair, student=student, assignment=assignment).values('option__text')

        title = Assignment.objects.get(pk=aid).homework.title
        pairs_dict = {}
        results_list = []
        student_choices=[]

        for pair in question_answer_pairs:
            answer = ''
            if pair.qtype == 2:
                answer=pair.answer
            elif pair.qtype == 1:
                answer=pair.correct.text 
            elif pair.qtype==3:             
                correct_choices = QuestionCorrectOption.objects.filter(question=pair).values('option__text')
                # correct_choices = Option.objects.filter(question=pair.questioncorrectoption.question).values_list('text', flat=True)
                values_list = [item['option__text'] for item in correct_choices]
                answer = list(values_list)
                print("3")
                print(answer)    


            pairs_dict[pair.question] = {
                'question': pair.question,
                'answer': answer
            }

          
        answered_all, all_questions, student_result = has_answered_all_questions(student, assignment)
        # Create a list of student answers aligned with their respective questions
        for result in question_answer_results:
            question_pair=result.question
            question_text = result.question.question
            question_id=result.question.pk
            question_type = result.question.qtype
            question_points = result.question.points
            if question_text in pairs_dict:

                question_info = pairs_dict[question_text]
                if question_type == 1:
                    all_options = Option.objects.filter(question=question_pair).values_list('text', flat=True)
                   
                    results_list.append({
                        'question': question_info['question'],
                        'answer': question_info['answer'],
                        'all_options': list(all_options),  # Include all options for the multiple-choice question
                        'student_answer': result.answer,  # Include student's choices for multiple-choice questions
                        'points': result.points,
                        'qtype': question_type,
                        'opoints' : question_points
                    })
                elif question_type == 3: 
                # Retrieve all options for the multiple-choice question
                    all_options = Option.objects.filter(question=question_pair).values_list('text', flat=True)

                    # Retrieve student's choices for multiple-choice question
                    student_choices = QuestionSelectedOption.objects.filter(
                        question=question_pair, student=student, assignment=assignment
                    ).values_list('option__text', flat=True)

                    results_list.append({
                        'question': question_info['question'],
                        'answer': question_info['answer'],
                        'all_options': list(all_options),  # Include all options for the multiple-choice question
                        'student_answer': list(student_choices),  # Include student's choices for multiple-choice questions
                        'points': result.points,
                        'qtype': question_type,
                        'opoints' : question_points
                    })
                else:
                    results_list.append({
                        'question': question_info['question'],
                        'answer': question_info['answer'],
                        'student_answer': result.answer,
                        'points': result.points,
                        'qtype': question_type,
                        'opoints' : question_points
                    })
     
        return JsonResponse({'success': True, 'results': results_list, 'title' : title, 'name' : name, 'questions' : all_questions, 'answers' : student_result})      



################
######GAME#####
################

@csrf_exempt
def start_game(request):

    if request.method == 'POST':
        data = json.loads(request.body)
        student_email = data['student_email']
        aid = data['assignment_id']

        sid = CustomUser.objects.get(email=student_email).pk

        game_path = "C:\\Users\\Namai\\Desktop\\fps\\Bakalauras2.exe"

        # Command to start the game executable with parameters
        command = [game_path, str(aid), str(sid)]

        try:
            # Execute the game using subprocess.Popen()
            subprocess.Popen(command)

            # Return success response
            return JsonResponse({'message': 'Game started successfully'})
        except Exception as e:
            print(str(e))
            # Return error response if execution fails
            return JsonResponse({'message': f'Failed to start game. Error: {str(e)}'}, status=500)

    # Return error response for non-POST requests
    return JsonResponse({'message': 'Invalid request method'}, status=400)


@csrf_exempt
def get_questions(request,aid):
     if request.method == 'GET':
        homework_id = Assignment.objects.get(pk=aid).homework.pk
        try:
            homework = Homework.objects.get(pk=homework_id)
            pairs = QuestionAnswerPair.objects.filter(homework=homework).values('id','question', 'answer', 'points', 'image')           
            homework_data = {
                'title': homework.title,
                'pairs': list(pairs)
            }
            return JsonResponse({'success': True, 'homework': homework_data})
        except Homework.DoesNotExist:
            return JsonResponse({'message': 'Homework not found'}, status=404)



@csrf_exempt
def post_answer(request):
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id', None)
        question_id = request.POST.get('question_id', None)
        player_answer = request.POST.get('answer', None)
        student_id = request.POST.get('student_id', None)
        points = request.POST.get('points', None)
        selected = request.POST.get('selected', None) #string numeriuku

        if assignment_id is not None and question_id is not None and player_answer is not None and student_id is not None and points is not None:

          
            question = QuestionAnswerPair.objects.get(pk=question_id)
            qtype = question.qtype
            assignment = Assignment.objects.get(pk=assignment_id)
            student = CustomUser.objects.get(pk=student_id)

            try:
                previous_answer = QuestionAnswerPairResult.objects.get(assignment=assignment, student=student, question=question)
    
            # Update the answer if it exists
            # if not created:
                if qtype == 3:
                    selected_elements = selected.split(',')
                    if len(selected_elements) > 0:
                        if len(selected_elements) == 1:
                            # Handle single number case
                            numbers = [int(selected_elements[0])]
                            print(f"One element selected: {numbers[0]}")
                        else:
                            # Handle array case
                            numbers = [int(element) for element in selected_elements]
                            print("Multiple elements selected:", numbers)
                        indexes = [int(element) for element in selected_elements]
                        options = Option.objects.filter(question=question)
                        selected_options = [options[index] for index in indexes]

                        QuestionSelectedOption.objects.filter(question=question, student=student, assignment=assignment).delete()
                        for option in selected_options:
                            QuestionSelectedOption.objects.create(question=question, student=student, assignment=assignment, option=option)
                    else:
                        print("nieko nepasirinko")
                    
                
                
                previous_answer.answer = player_answer
                previous_answer.points = points
                previous_answer.save()
            # Create a new answer if it doesn't exist
            except ObjectDoesNotExist:
                if qtype == 3:
                    selected_elements = selected.split(',')
                    indexes = [int(element) for element in selected_elements]
                    options = Option.objects.filter(question=question)
                    selected_options = [options[index] for index in indexes]

                    for option in selected_options:
                        QuestionSelectedOption.objects.create(question=question, student=student, assignment=assignment, option=option)

                previous_answer = QuestionAnswerPairResult.objects.create(question=question, assignment=assignment, student=student, answer=player_answer, points=points)

           
            return JsonResponse({'success': True, 'id': previous_answer.pk})
            
        return JsonResponse({'message': 'Failed to receive answer or missing data'}, status=400)    

@csrf_exempt
def check_summary(request,aid,sid):
    assignment = Assignment.objects.get(pk=aid)
    student = CustomUser.objects.get(pk=sid)
    exists = True
    try:
        AssignmentResult.objects.get(assignment = assignment, student=student)
    except ObjectDoesNotExist:
        exists=False

    return JsonResponse({'success': True, 'exists': exists})


@csrf_exempt
def post_summary(request):
    assignment_id = request.POST.get('assignment_id', None)
    time = request.POST.get('time', None) 
    student_id = request.POST.get('student_id', None)
    points = request.POST.get('points', None)
    date = datetime.now()

    if assignment_id is not None and time is not None and student_id is not None and points is not None:
        assignment = Assignment.objects.get(pk=assignment_id)
        student = CustomUser.objects.get(pk=student_id)
        assignmentResult= AssignmentResult.objects.create(assignment=assignment, student=student, date=date, points=points, time=time)

        return JsonResponse({'success': True, 'id': assignmentResult.pk})
        
    return JsonResponse({'message': 'Failed to receive summary or missing data'}, status=400) 


@csrf_exempt
def handle_school(request):
    if request.method == 'POST':
        csv_file = request.FILES.get("file")
        title = request.POST.get("title")
        license = request.POST.get("license")
        print(title)
        print(license)

        try:
            # Try to get the school by title
            school_exist = School.objects.get(title=title)
            school = school_exist
        except ObjectDoesNotExist:
            # If the school doesn't exist, create it
            school = School.objects.create(title=title, license_end=license)

        csv_file = TextIOWrapper(csv_file, encoding='utf-8', errors='replace')

        reader = csv.reader(csv_file, delimiter=';')
        login_data =[]
        for row in reader:
            first_name = row[0]
            last_name = row[1]
            class_name = row[2]
            gender = row[3]
            if gender=='vyras':
                gender=1
            else:
                gender=2    

            # Check if the class exists for the given school
            existing_class = Class.objects.filter(school=school, title=class_name).first()

            if not existing_class and class_name:
                # Create the class if it doesn't exist
                classs = Class.objects.create(school=school, title=class_name)
            else:
                classs = existing_class
            
            email, password = generate_email_password(first_name, last_name)

            role = 2 if class_name == '' else 1 

            login_user ={
                'name': first_name,
                'surname': last_name,
                'classs' : class_name,
                'email': email,
                'password' : password,
                'role' : role
            }    
            login_data.append(login_user)

            user = CustomUser.objects.create_user(
                first_name=first_name,
                last_name=last_name, 
                gender=gender,
                school=school,
                password= password, 
                email = email,
                role=role,
                username=email
            )

            if class_name:
                student_class = StudentClass.objects.create(student=user, classs=classs)

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

    elif request.method == 'GET':
        schools = School.objects.all()
        school_data = [{'id': school.pk, 'title': school.title, 'license' : school.license_end} for school in schools]
        return JsonResponse({'schools': school_data})  

@csrf_exempt
def handle_school_id(request, sid):
    if request.method == 'DELETE':
        school = School.objects.get(pk=sid)
        school.delete()
        return JsonResponse({'data': 'ok'})  
    elif request.method == 'POST':
        #gali ir nebut failo - tada tik licenzijos data keiciasi ir pavadinimas
        csv_file = request.FILES.get("file")
        new_school_title = request.POST.get("title")
        new_license_expire_date = request.POST.get("license")
        school_id = sid
        try:
            school = School.objects.get(id=school_id)
        except ObjectDoesNotExist:
            return JsonResponse({'success' : False}, status=404)

        # Update school details if provided
        if new_school_title:
            school.title = new_school_title
        if new_license_expire_date:
            school.license_end = new_license_expire_date
        school.save()

        # Update or create members (teachers and students)
        if csv_file:
            response = update_or_create_members(csv_file, school)
            return response

    return JsonResponse({'success' : True})


def update_or_create_members(file, school):
    processed_users = set()  # To keep track of processed users
    csv_file = TextIOWrapper(file, encoding='utf-8', errors='replace')
    print("viduj update members")
    reader = csv.reader(csv_file, delimiter=';')
    login_data =[]
    for row in reader:
        first_name = row[0]
        print(first_name)
        last_name = row[1]
        class_name = row[2]
        gender = row[3]
        gender = 1 if gender=='vyras' else 2    
        role = 2 if class_name == '' else 1

        # Check if the class exists for the given school
        existing_class = Class.objects.filter(school=school, title=class_name).first()

        if not existing_class and class_name:
            # Create the class if it doesn't exist
            classs = Class.objects.create(school=school, title=class_name)
        else:
            classs = existing_class
        
        email, password = generate_email_password(first_name, last_name)

        role = 2 if class_name == '' else 1 

        login_user ={
            'name': first_name,
            'surname': last_name,
            'classs' : class_name,
            'email': email,
            'password' : password,
            'role' : role
        }    

        try:    
            #randa pagal varda i pavarde tai jei du vienodi mokykloj tai negerai, bet nieko tokio, jei pereina i klase irgi nereikia
            #gali lyst i admin panel ir ten pavienius tvarkyt atvejus
            user = CustomUser.objects.get(
                first_name=first_name,
                last_name=last_name,
                role=role,
                school = school
            )
            processed_users.add(user.id)  # Add user to processed users set
            print("found user: " + str(user.id))

        except ObjectDoesNotExist:
            email, password = generate_email_password(first_name, last_name)
            new_user = CustomUser.objects.create_user(
                first_name=first_name,
                last_name=last_name, 
                gender=gender,
                school=school,
                password= password, 
                email = email,
                role=role,
                username=email
            )
            processed_users.add(new_user.id)  # Add user to processed users set
            print("new user: " + str(new_user.id))
            login_data.append(login_user)
            
            if class_name:
                student_class = StudentClass.objects.create(student=new_user, classs=classs)

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
            # Customize the width of each column
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
            # Customize the width of each column
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
        response['Content-Disposition'] = 'attachment; filename="login_credentials.txt"'
        #response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['FormattedTitle'] = filename

       

    # Delete users who are not present in the new file
    all_users = CustomUser.objects.filter(role__in=[1, 2], school=school)
    users_to_delete = all_users.exclude(id__in=processed_users)
    # for user in users_to_delete:
    #     print(user.first_name)
    
    #users_to_delete.delete()

    return response


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
