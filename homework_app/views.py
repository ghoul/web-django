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
from rest_framework.decorators import api_view,authentication_classes,permission_classes,action
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.mixins import PermissionRequiredMixin
from rest_framework import mixins
from rest_framework import viewsets
from .utils import *
from django.db.models import Subquery, OuterRef,Count


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

    def options(self, request, *args, **kwargs):
        print("options inside")
        response = Response()
        response['Access-Control-Allow-Methods'] = 'DELETE, GET, OPTIONS, PATCH, POST, PUT'
        return response

    # def update(self, request, *args, **kwargs):
    #     # response = super().update(request, *args, **kwargs)
    #     # response['Access-Control-Allow-Methods'] = 'DELETE, GET, OPTIONS, PATCH, POST, PUT'
    #     return response

    def update(self, request, *args, **kwargs):
        instance = self.get_object()  # Retrieve the instance to update
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        # # Check if assignment with provided ID exists
        # assignment_id = request.data.get('id')
        # if assignment_id and Assignment.objects.filter(id=assignment_id).exists():
        #     return self.update(request, *args, **kwargs)
        # else:
        #     return super().create(request, *args, **kwargs)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # serializer.is_valid(raise_exception=True)
        # self.perform_create(serializer)
        # headers = self.get_success_headers(serializer.data)
        # return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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

class HomeworkView(mixins.ListModelMixin,mixins.RetrieveModelMixin,mixins.UpdateModelMixin,mixins.DestroyModelMixin,mixins.CreateModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]
    serializer_class = HomeworkSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def get_queryset(self):
        queryset = Homework.objects.filter(teacher=self.request.user) #\
            # .annotate(num_questions=Count('pairs'))
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
        # serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            homework = serializer.save() #teacher=request.user, date = datetime.now().date()
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
        print(elapsed)
      
        date = datetime.now()
        assignment = Assignment.objects.get(pk=assignment_id)
        homework=assignment.homework
        questions = QuestionAnswerPair.objects.filter(homework=homework)

        total_points = 0
       
        for i, questionOG in enumerate(questions):
            print(i)
            qid = request.POST.get(f'pairs[{i}][questionId]')
            answer = request.POST.get(f'pairs[{i}][answer]')   
            print("answer: " + str(answer)) 
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
                print("id: " +  str(answerOG))
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
                    print(options)
                    print(str(len(options)))
                    print(str(optionIndex))

                    option = Option.objects.get(pk=optionIndex) #options[optionIndex]
                    
                    saveSelected = QuestionSelectedOption.objects.create(assignment=assignment, student=request.user, question=question, option=option)   
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
                

            if qtype==2 or qtype == 1:
                print("og: " + str(answerOG))
                print("ans: " + str(answer))
                if str(answerOG) == str(answer):
                    print("ifif points: " + str(points))
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

        assignmentResult = AssignmentResult.objects.create(assignment=assignment, student=request.user, date=date, points=total_points, time=formatted_time)
        return Response(status=201)


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


class AssignmentViewStatistics(mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AssignmentResultSerializer

    def retrieve(self, request, *args, **kwargs):
        assignment_id = self.kwargs.get('pk')
        assignment = Assignment.objects.get(pk=assignment_id)

        queryset = AssignmentResult.objects.filter(assignment=assignment)
        serializer = self.get_serializer(queryset, many=True)

        students_data = serializer.data
       
        sorted_students = sorted(students_data, key=sort_students)

        # class_students = StudentClass.objects.filter(classs=assignment.classs).values_list('student', flat=True)
        
        # # Get students who haven't submitted their assignment results yet
        # submitted_students = AssignmentResult.objects.filter(assignment=assignment).values_list('student', flat=True)
        # print(submitted_students)
        # remaining_students = class_students.exclude(id__in=submitted_students)
        

        # serializer = StatisticUserSerializer(instance=remaining_students, many=True)
        # students_data = serializer.data
        
        # # Get assignment results
        # assignment_results = AssignmentResult.objects.filter(assignment=assignment)
        # assignment_serializer = self.get_serializer(assignment_results, many=True)
        # assignment_data = assignment_serializer.data
        
        # print(students_data)
        # # Combine assignment results and remaining students
        # #TODO - NESORTINA PAGAL SITA, NERANDA NAMES
        # sorted_students_data = sorted(students_data, key=lambda x: (x['first_name'], x['last_name']))

        # # Sort assignment_data using sort_students function
        # sorted_assignment_data = sorted(assignment_data, key=sort_students)

        # sorted_data = sorted_assignment_data + sorted_students_data
        
        # Sort the combined data
        #sorted_students = sorted(combined_data, key=sort_students) 

        response_data = {
            'assignment': {
                'title': assignment.homework.title,
                'class_title': assignment.classs.title
            },
            'assignment_results': sorted_students
        }

        return Response(response_data)
    # def retrieve(self, request, *args, **kwargs):
    #     assignment_id = self.kwargs.get('pk')
    #     assignment = Assignment.objects.get(pk=assignment_id)

    #     # Get all students from the class
    #     student_class_relations = StudentClass.objects.filter(classs=assignment.classs)

    #     # Extract the students from the relations
    #     students_in_class = [relation.student for relation in student_class_relations]


    #     # Get assignment results for the assignment
    #     assignment_results = AssignmentResult.objects.filter(assignment=assignment)

    #     # Create a dictionary to hold the results for each student
    #     student_results = {student.id: None for student in students_in_class}
    #     print(student_results)

    #     # Update the dictionary with assignment results
    #     for result in assignment_results:
    #         student_results[result.student.id] = result
    #         print(result.student.id)
    #         print(result)

    #     # Serialize the data
    #     serializer = self.get_serializer(student_results.values(), many=True)
    #     students_data = serializer.data
    #     sorted_students = sorted(students_data, key=sort_students)
    #     print(sorted_students)

    #     response_data = {
    #         'assignment': {
    #             'title': assignment.homework.title,
    #             'class_title': assignment.classs.title
    #         },
    #         'assignment_results': sorted_students
    #     }

    #     return Response(response_data)


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


# @csrf_exempt
# def handle_students_assignment_results(request,aid):
#     if request.method == 'GET':
#         assignment = Assignment.objects.get(pk=aid)
#         assignmentResults = AssignmentResult.objects.filter(assignment=assignment)

#         students_data = [
#             {'id' : result.pk, 'name': result.student.first_name, 'surname': result.student.last_name, 'date' : result.date, 'time': result.time, 'points':result.points}
#             for result in assignmentResults
#         ]
      
#         return JsonResponse({'success': True, 'results': students_data}) 
#     #TODO: IS ZAIDIMO KREIPIASI I SITA PASIBAIGUS UZDUOTIM
#     elif request.method == 'POST':
#         assignment = Assignment.objects.get(pk=aid)
#         data = json.loads(request.body)
#         student_id = data['student_id']
#         student = CustomUser.objects.get(pk=student_id)
#         date = data['date']
#         time = data['time']
#         points = data['points']

#         result = AssignmentResult.objects.create(assignment=assignment, student=student, date=date, time=time, points=points)
      
#         return JsonResponse({'success': True, 'result': result})       



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
