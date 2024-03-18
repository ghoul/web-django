from ast import Assign
import math
import subprocess
from datetime import datetime, timedelta
import email
import json
from turtle import st
from urllib import request, response
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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from rest_framework_simplejwt.authentication import JWTAuthentication, JWTTokenUserAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework.authentication import  SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view,authentication_classes,permission_classes,action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.mixins import PermissionRequiredMixin
from rest_framework import mixins
from rest_framework import viewsets
from .utils import *
from django.db.models import Subquery, OuterRef,Count
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import Group

logger = logging.getLogger(__name__)


class LoginViewUser(viewsets.GenericViewSet):
    serializer_class = LoginUserSerializer

    def post(self, request):
        user = CustomUser.objects.get(email=request.data.get('email'))
        if user.check_password(request.data.get('password')):
            license_end = user.school.license_end
            if license_end and license_end < datetime.today().date():
                return Response({"error": "Your license has expired. Please contact your administrator."}, status=403)

            login(request, user)
            serializer = self.get_serializer(user)
            token, created = Token.objects.get_or_create(user=user)
            csrf_token = generate_csrf_token(request)

            return Response({"token": token.key, "user": serializer.data, "csrf_token": csrf_token})
        else:
            return Response({"error": "Invalid credentials"}, status=400)


class PasswordView(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            if str(request.user.id) != kwargs['pk']:
                return Response({"error": "You can only update your own password."}, status=status.HTTP_403_FORBIDDEN)
            return super().update(request, *args, **kwargs)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        ).exclude(id__in=Subquery(finished_assignments))
    
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

    def update(self, request, *args, **kwargs):
        instance = self.get_object() 
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return Assignment.objects.all()

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

class AssignmentViewStatistics(mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AssignmentResultSerializer

    def retrieve(self, request, *args, **kwargs):
        assignment_id = self.kwargs.get('pk')
        assignment = Assignment.objects.get(pk=assignment_id)
        #TODO VISI STUDENTS KLASEJ
        queryset = AssignmentResult.objects.filter(assignment=assignment)
        serializer = self.get_serializer(queryset, many=True)

        students_data = serializer.data
       
        sorted_students = sorted(students_data, key=sort_students)

        response_data = {
            'assignment': {
                'title': assignment.homework.title,
                'class_title': assignment.classs.title
            },
            'assignment_results': sorted_students
        }

        return Response(response_data)


class ClassViewStatistics(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        classs = StudentClass.objects.get(student=request.user).classs
        class_title = classs.title
        students = StudentClass.objects.filter(classs=classs)
        assignments = Assignment.objects.filter(classs=classs)

        start_date, end_date = get_current_school_year()
        assignment_results = AssignmentResult.objects.filter(
            student__in=students.values_list('student', flat=True),
            assignment__in=assignments,
            date__range=(start_date, end_date)
        ).values('student__first_name', 'student__last_name', 'student__gender').annotate(
            total_points=Sum('points')
        )

        leaderboard_entries = [
            {
                'student': f"{result['student__first_name']} {result['student__last_name']}",
                'gender': result['student__gender'],
                'points': result['total_points'] or 0
            }
            for result in assignment_results
        ]
        leaderboard_entries.sort(key=lambda x: x['points'], reverse=True)
        response_data = {
            'leaderboard': leaderboard_entries,
            'class_title': class_title
        }

        return Response(response_data)

class OneStudentViewStatistics(viewsets.GenericViewSet, mixins.ListModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionAnswerPairResultSerializer
    lookup_url_kwarg = 'assignment_id'

    def get_queryset(self):
        assignment_id = self.kwargs.get('assignment_id')
        student_id = self.kwargs.get('student_id')

        queryset = QuestionAnswerPairResult.objects.filter(
            assignment__id=assignment_id,
            student__id=student_id
        ).select_related('question__homework').prefetch_related('question__option', 'question__questionoselect')

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        assignment = queryset.first().assignment
        student = queryset.first().student

        score = calculate_score(student, assignment)
        assignment_points = calculate_assignment_points(assignment)
        grade = calculate_grade(score, assignment)

        data = self.serializer_class(queryset, many=True, context = {'request': self.request}).data
        response_data = {
            'results': data,
            'points' : assignment_points,
            'score': score,
            'grade': grade
        }
        return Response(response_data)


class HomeworkView(mixins.ListModelMixin,mixins.RetrieveModelMixin,mixins.UpdateModelMixin,mixins.DestroyModelMixin,mixins.CreateModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = HomeworkSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        queryset = Homework.objects.filter(teacher=self.request.user)
        return queryset

    def get_object(self):
        queryset = self.get_queryset()
        obj = queryset.get(pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        edit = True
        assignments = Assignment.objects.filter(homework=instance)
        if assignments.exists():
            edit = False

        serializer = self.get_serializer(instance)
        serialized_data = serializer.data
        serialized_data['edit'] = edit

        return Response(serialized_data)    

    def create_question_answer_pairs(self, request, homework):
        data = []
        num_pairs = sum('question' in key for key in request.POST.keys())
        qtype_mapping = {'select': 1, 'write': 2, 'multiple': 3}

        for i in range(num_pairs):
            qtype = request.POST.get(f'pairs[{i}][qtype]')
            qtype = qtype_mapping.get(qtype, None)
            question = request.POST.get(f'pairs[{i}][question]')
            answer = request.POST.get(f'pairs[{i}][answer]')
            #TODO
            if len(answer) == 0:
                answer = "none"
            points = request.POST.get(f'pairs[{i}][points]')

            qapair_serializer = QuestionAnswerPairSerializer(data={'homework': homework.id, 'qtype': qtype, 'question': question, 'answer' : answer, 'points': points}, context={'request': request})
            if qapair_serializer.is_valid():
                qapair = qapair_serializer.save()
                data.append(qapair_serializer.data)

                num_options = sum(key.startswith(f'pairs[{i}][options]') for key in request.POST.keys())

                options = []
                for option_i in range(num_options):
                    option_text = request.POST.get(f'pairs[{i}][options][{option_i}]')
                    option_serializer = OptionSerializer(data={'text': option_text, 'question': qapair.id}, context={'request': request})
                    if option_serializer.is_valid():
                        option = option_serializer.save()
                        options.append(option)

                        if qtype == 3:  # multiple select question      
                            num_mult = sum(key.startswith(f'pairs[{i}][multipleOptionIndex]') for key in request.POST.keys())                                                      
                            for y in range(num_mult):                                
                                correct = int(request.POST.get(f'pairs[{i}][multipleOptionIndex][{y}]'))
                                if correct==option_i:
                                    create_correct_option(qapair, option)   

                    else:
                        print("option : " + str(option_serializer.errors))
                        return {'success': False, 'error': option_serializer.errors}, status.HTTP_400_BAD_REQUEST   

                if qtype == 1:                      
                            correct_option_index = int(request.POST.get(f'pairs[{i}][correctOptionIndex]'))
                            if 0 <= correct_option_index < len(options):
                                create_correct_option(qapair, options[correct_option_index])     

            else:
                print("qapair: " + str(qapair_serializer.errors))
                return {'success': False, 'error': option_serializer.errors}, status.HTTP_400_BAD_REQUEST                          

        return data, status.HTTP_201_CREATED

    def create(self, request):
        print("crating homework start")
        mutable_data = request.data.copy()
        mutable_data['teacher'] = request.user.id
        mutable_data['date'] = datetime.now().date()

        serializer = self.serializer_class(data=mutable_data)
        if serializer.is_valid():
            homework = serializer.save() 
            print("success1")
            data = self.create_question_answer_pairs(request, homework)
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    

    def update(self, request,*args, **kwargs):
        try:
            homework = self.get_object()
        except Homework.DoesNotExist:
            return JsonResponse({'message': 'Homework not found'}, status=404)

        # data = json.loads(request.body)
        print(request.data)
        homework_name = request.data.get('title')
        correct = request.data.get('correct') #local indxes each question answer option
        multiple = request.data.get('multiple') #local ids qid ir oid each question

        if not homework_name:
            return JsonResponse({'message': 'Homework name is required'}, status=400)

        homework.title = homework_name
        homework.save()    

        received_pairs = request.data.get('pairs', [])
        existing_pairs = QuestionAnswerPair.objects.filter(homework=homework)
        qtype_mapping = {'select': 1, 'write': 2, 'multiple': 3}

        # Extract IDs from received pairs
        received_pair_ids = set(pair.get('id') for pair in received_pairs if pair.get('qid'))

        # Check and delete pairs that are missing from received data
        for existing_pair in existing_pairs:
            if existing_pair.id not in received_pair_ids:
                existing_pair.delete()

        for index, pair in enumerate(received_pairs):
            question = pair.get('question')
            answer = pair.get('answer')
            points = pair.get('points')
            qtype = pair.get('qtype')
            qtype = qtype_mapping.get(qtype, None) 
          
            pair_obj, created = QuestionAnswerPair.objects.get_or_create(
                homework=homework,
                id=pair.get('id'),
                defaults={
                    'qtype': qtype,
                    'question': question,
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
                pair_obj.points = points
                pair_obj.save()
            
            if qtype == 1:
                options = pair.get('options', [])
                correct_option_index = correct[index]

                try:
                    options_old = Option.objects.filter(question=pair_obj)
                    options_old.delete()
                    correct_old = QuestionCorrectOption.objects.get(question = pair_obj)
                    correct_old.delete()
                except:
                    print("nera")    

                for option_text in options:
                    option = Option.objects.create(text=option_text, question=pair_obj)

                if 0 <= correct_option_index < len(options):
                    correct = Option.objects.get(text=options[correct_option_index], question=pair_obj)
                    QuestionCorrectOption.objects.create(option = correct, question = pair_obj)

            elif qtype == 3:
                options = pair.get('options', [])
                correct_option_indexes = [item['oid'] for item in multiple if item.get('qid') == index]

                try:
                    options_old = Option.objects.filter(question=pair_obj)
                    options_old.delete()
                    correct_options_old = QuestionCorrectOption.objects.filter(question=pair_obj)
                    correct_options_old.delete()
                except:
                    print("nera mult")    

                for option_text in options:
                    option = Option.objects.create(text=option_text, question=pair_obj)

                for correct_option_index in correct_option_indexes:
                    QuestionCorrectOption.objects.create(question=pair_obj, option=Option.objects.get(text=options[correct_option_index], question=pair_obj))      

        return Response(status=status.HTTP_201_CREATED)            


class TestView(mixins.ListModelMixin, mixins.CreateModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = TestSerializer

    def get_queryset(self):
        assignment_id = self.kwargs.get('assignment_id')
        homework = Assignment.objects.get(pk=assignment_id).homework
        questions = QuestionAnswerPair.objects.filter(homework=homework)
        return questions

    def post_answers(self, request, *args, **kwargs): 
        assignment_id = self.kwargs.get('assignment_id')
        elapsed = float(request.POST.get('time'))/1000      
        date = datetime.now()
        assignment = Assignment.objects.get(pk=assignment_id)
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
                answered_before = QuestionAnswerPairResult.objects.get(question=question, assignment=assignment, student=request.user)
                answered_before.delete()
                selected = QuestionSelectedOption.objects.filter(assignment=assignment, student=request.user, question=question)
                selected.delete()
            except ObjectDoesNotExist:
                new = True
                
            if qtype == 1: #select
                answerOG = QuestionCorrectOption.objects.get(question=question).option.id
                option = Option.objects.get(pk=answerOG)
                QuestionSelectedOption.objects.create(option = option, question = questionOG, student = request.user, assignment=assignment) #serializer TODO
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
                num_mult = sum(key.startswith(f'pairs[{i}][multipleIndex]') for key in request.POST.keys())
                for y in range(num_mult):
                    optionIndex = int(request.POST.get(f'pairs[{i}][multipleIndex][{y}]'))
                    answersUser.append(optionIndex)

                    option = Option.objects.get(pk=optionIndex) 
                    QuestionSelectedOption.objects.create(assignment=assignment, student=request.user, question=question, option=option)   

                for optionIndex in answersUser:
                    if optionIndex in originIndexes:
                        get_points+=points

                #jei per daug pasirenka
                if len(answersUser)>len(originIndexes):
                    wrongC = len(answersUser)-len(originIndexes)
                    minusPoints = question.points/len(options)
                    for w in range(wrongC):
                        get_points-=minusPoints 

                #arba jei nei vieno teisingo nepasirinko: 0 automatiskai               

                total_points+=get_points   
                

            if qtype==2 or qtype == 1:
                if str(answerOG) == str(answer):
                    get_points=points

            total_points+=get_points  

            print("total points: " + str(total_points)) 


            QuestionAnswerPairResult.objects.create(question=question, assignment=assignment, student=request.user, answer=answer, points=get_points)
            get_points=0
        elapsed_timedelta = timedelta(seconds=elapsed)

        # Extract hours, minutes, and seconds from the timedelta
        hours, remainder = divmod(elapsed_timedelta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Create a string representation of the elapsed time
        formatted_time = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

        AssignmentResult.objects.create(assignment=assignment, student=request.user, date=date, points=total_points, time=formatted_time)
        return Response(status=201)



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


    

################
######GAME#####
################

#NEREIKIA?
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

#NEREIKIA?? - I ASSIGNMENTKVIEW ar kita
@csrf_exempt
def get_questions(request,aid):
     if request.method == 'GET':
        homework_id = Assignment.objects.get(pk=aid).homework.pk
        try:
            homework = Homework.objects.get(pk=homework_id)
            pairs = QuestionAnswerPair.objects.filter(homework=homework).values('id','question', 'answer', 'points')           
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



#####################
#### ADMIN SCHOOL ####
#####################
class SchoolViewAdmin(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = SchoolSerializer

    def get_queryset(self):
        return School.objects.all()

    def create(self, request):
        csv_file = request.FILES.get("file")
        title = request.POST.get("title")
        license = request.POST.get("license")
        students_group, created = Group.objects.get_or_create(name='student')
        teachers_group, created = Group.objects.get_or_create(name='teacher')
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
                StudentClass.objects.create(student=user, classs=classs)
                user.groups.add(students_group)
            else:
                user.groups.add(teachers_group)   

        response = login_file(login_data, school)

        return response

   
class UpdateViewSchool(APIView):
    def post(self, request, school_id):
        # Retrieve school instance
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return Response({'error': 'School not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Extract data from request
        csv_file = request.FILES.get("file")
        new_school_title = request.POST.get("title")
        new_license_expire_date = request.POST.get("license")

        # Update school details if provided
        if new_school_title:
            school.title = new_school_title
        if new_license_expire_date:
            school.license_end = new_license_expire_date
        school.save()

        # Update or create members (teachers and students) if CSV file is provided
        if csv_file:
            response = update_or_create_members(csv_file, school)
            return response

        return Response({'success': True})


def update_or_create_members(file, school):
    processed_users = set()  # To keep track of processed users
    students_group, created = Group.objects.get_or_create(name='student')
    teachers_group, created = Group.objects.get_or_create(name='teacher')
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
                StudentClass.objects.create(student=new_user, classs=classs)
                new_user.groups.add(students_group)
            else:
                new_user.groups.add(teachers_group)   

    response = login_file(login_data, school)

    # Delete users who are not present in the new file
    all_users = CustomUser.objects.filter(role__in=[1, 2], school=school)
    users_to_delete = all_users.exclude(id__in=processed_users)
    # for user in users_to_delete:
    #     print(user.first_name)
    
    #users_to_delete.delete()

    return response



