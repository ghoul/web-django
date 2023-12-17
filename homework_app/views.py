from ast import Assign
from datetime import datetime
import json
from xml.etree.ElementTree import Comment
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse,HttpResponseNotFound, HttpResponseBadRequest,HttpResponseServerError
from homework_app.models import Homework,QuestionAnswerPair, Class, StudentClass, AssignmentResult, School, Assignment,StudentTeacher,StudentTeacherConfirm,QuestionAnswerPairResult
from django.views.decorators.csrf import csrf_exempt, csrf_protect
import logging
import re
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from rest_framework_simplejwt.tokens import Token
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenObtainPairView
# from django.contrib.auth.models import User
from .models import CustomUser
import jwt 
from django.conf import settings
from django.db.models import Q
from datetime import date, time

logger = logging.getLogger(__name__)

class CustomTokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    username = serializers.CharField(source='user.username')
    is_admin = serializers.SerializerMethodField()

    def get_is_admin(self, obj):
        return obj.user.is_staff

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer


@csrf_exempt
def signup_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        name = data['name']
        surname = data['surname']
        password = data['password']
        email = data['email']
        role = data['role']

        print(email)

        existing_user = CustomUser.objects.filter(email=email).first()
        if existing_user:
            return JsonResponse({'error': 'Email is already taken.'}, status=400)

        print("po custom")
        # Create a new user
        user = CustomUser.objects.create_user(first_name=name, last_name=surname,email=email, username=email, password=password, role=role)

        # Generate JWT token
        payload = {
            'name': user.first_name,
            'surname': user.last_name,
            'email': user.email,
            'role' : user.role
        }
        token = jwt.encode(payload, settings.SECRET_KEY_FOR_JWT, algorithm='HS256')  # Use a secure secret key

        # Log the user in
        login(request, user)

        return JsonResponse({'success': True, 'user': name, 'token': token, 'role': user.role}, status=200)
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

@csrf_exempt
def login_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data['email']
        password = data['password']
        print(email)
        print(password)
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            payload = {
            'name': user.first_name,
            'surname': user.last_name,
            'email': user.email,
            'role' : user.role
            #"exp": datetime.utcnow() + timedelta(hours=1)
        } 
            token = jwt.encode(payload, settings.SECRET_KEY_FOR_JWT, algorithm='HS256')  # Use a secure secret key
            login(request, user)
            return JsonResponse({'success': True, 'token': token, 'role': user.role}, status=200)
        else:
            return JsonResponse({'error': 'Neteisingas prisijungimo vardas arba slaptažodis'}, status=401)
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

@csrf_exempt
def user_data(request):
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

    email = payload.get('email')
    user = CustomUser.objects.get(email=email)
    if request.method == "GET":
        user_data =[
        {
            'name': user.first_name,
            'surname': user.last_name,
            'email': user.email,
        }
        ]
        return JsonResponse({'data': user_data})
    elif request.method == "PUT":
        data = json.loads(request.body)
        new_name = data['name']
        new_surname = data['surname']
        new_email = data['email']

        if not new_name or not new_surname or not new_email:
            return JsonResponse({'success': False, 'error': 'Visi laukai privalomi'}, status=400)

        user.first_name = new_name
        user.last_name = new_surname
        user.email = new_email

        try:
            user.save()
            payload = {
            'name': user.first_name,
            'surname': user.last_name,
            'email': user.email,
            'role': user.role
            }
            token = jwt.encode(payload, settings.SECRET_KEY_FOR_JWT, algorithm='HS256')

            return JsonResponse({'success': True, 'token': token, "id": user.pk}, status=200)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def change_password(request):
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

    email = payload.get('email')
    user = CustomUser.objects.get(email=email)
    if request.method == "PUT":
        data = json.loads(request.body)
        new_password = data['password']

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
    if student['points'] != '' and student['time'] != '':
        return (-student['points'], student['time'])
    else:
        return (float('-inf'), float('-inf'))

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
    assingment_title = assignment.homework.title
    #pagal assignment rast klase ir mokinius visus
    #tada tikrint kiekviena ar jau atliko ta assignment pagal AssignemtResult ir is ten paimt info 
    if request.method == 'GET':
        classs = assignment.classs
        students_in_class = classs.classs.all()
        results = AssignmentResult.objects.filter(assignment=assignment)
        
        students_data = []

        for student in students_in_class:
        # Filter AssignmentResult for the current student and assignment
            student_results = results.filter(student=student.student)

            # Initialize empty values for date, time, points
            date = ''
            time = ''
            points = ''
            status = 'Bad'

            if student_results.exists():
                answered_all, all_questions, student_result = has_answered_all_questions(student.student, assignment)
                if answered_all:
                    status = 'Good'
                else: 
                    status = 'Average'
                # Extracting the date and time from the first result (assuming all results have the same date and time for a student)
                date = student_results.first().date.strftime('%Y-%m-%d')  # Format the date as needed
                time = student_results.first().time.strftime('%H:%M:%S')  # Format the time as needed

                # Calculate total points for the student
                points = student_results.first().points

            students_data.append({
                'id': student.student.pk,
                'name': student.student.first_name,
                'surname': student.student.last_name,
                'date': date,
                'time': time,
                'points': points,
                'status': status,  # Add status logic if needed
            })

            students_data = sorted(students_data, key=sort_students)
        return JsonResponse({'students': students_data, 'title': assingment_title, 'id' : user.id}) 


@csrf_exempt
def handle_assignments_teacher(request):
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
        today = date.today()  
        active_assignments = Assignment.objects.filter(
        classs__teacher=teacher,  # Filter by teacher ID
        # from_date__lte=today,  # From date less than or equal to today
        to_date__gte=today,  # To date greater than or equal to today
    )
        assignment_data = []

        for assignment in active_assignments:
            status = get_assignment_status(assignment)
            assignment_info = {
                'id': assignment.pk,
                'title': assignment.homework.title,
                'fromDate': assignment.from_date,
                'toDate': assignment.to_date,
                'classs': assignment.classs.title,
                'status': status
            }
            assignment_data.append(assignment_info)
        return JsonResponse({'data': assignment_data}) 

    elif request.method == 'DELETE':
        data = json.loads(request.body)
        id = data['id']
        assignment = Assignment.objects.get(pk=id)
        assignment.delete()
        return JsonResponse({'success': True}) 

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

@csrf_exempt
def handle_assignments_teacher_finished(request):
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
        today = date.today()  
        active_assignments = Assignment.objects.filter(
        classs__teacher=teacher,  # Filter by teacher ID
        to_date__lte=today,
    )

        assignment_data = [
                {'id' : hw.pk, 'title': hw.homework.title, 'fromDate': hw.from_date, 'toDate' : hw.to_date, 'classs' : hw.classs.title, 'status' : "good"}
                for hw in active_assignments
            ]

        return JsonResponse({'data': assignment_data}) 



@csrf_exempt
def handle_assignments_student(request):
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
    student = CustomUser.objects.get(email=email)

    if request.method == 'GET':
        # Get classes associated with the student
        student_classes = Class.objects.filter(classs__student=student)

        # Get active assignments for each class
        today = date.today()
        active_assignments = Assignment.objects.filter(
            classs__in=student_classes,  # Filter by classes associated with the student
            from_date__lte=today,  # From date less than or equal to today
            to_date__gte=today  # To date greater than or equal to today
        )
        assignment_data = [
        {
            'id': assignment.id,
            'title': assignment.homework.title,
            'fromDate': assignment.from_date,
            'toDate': assignment.to_date,
            'teacher': assignment.classs.teacher.first_name + ' ' + assignment.classs.teacher.last_name,
        }
        for assignment in active_assignments
        ]

        return JsonResponse({'data': assignment_data})

            

@csrf_exempt
def handle_assignments_student_finished(request):
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
    student = CustomUser.objects.get(email=email)

    if request.method == 'GET':
        # Get classes associated with the student
        student_classes = Class.objects.filter(classs__student=student)

        # Get active assignments for each class
        today = date.today()
        active_assignments = Assignment.objects.filter(
            classs__in=student_classes,  # Filter by classes associated with the student
            to_date__lte=today,
        )
        assignment_data = [
        {
            'id': assignment.id,
            'title': assignment.homework.title,
            'fromDate': assignment.from_date,
            'toDate': assignment.to_date,
            'teacher': assignment.classs.teacher.first_name + ' ' + assignment.classs.teacher.last_name,
        }
        for assignment in active_assignments
        ]

        return JsonResponse({'data': assignment_data})


@csrf_exempt
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
        
        #data = json.loads(request.body)
        #homework_name = data['homeworkName']
        homework_name = request.POST.get('homeworkName')
        date = datetime.now().date()
        print("post homework: " + homework_name)

        # Create a new homework object
        homework = Homework.objects.create(title=homework_name, date=date, teacher=teacher)

        num_pairs = len(request.POST.getlist('pairs[0][question]'))
        print(num_pairs)

        for i in range(num_pairs):
            question = request.POST.get(f'pairs[{i}][question]')
            answer = request.POST.get(f'pairs[{i}][answer]')
            image = request.FILES.get(f'pairs[{i}][image]')
            points = request.POST.get(f'pairs[{i}][points]')

            # Create a question-answer pair object and associate it with the homework
            pair = QuestionAnswerPair.objects.create(
                homework=homework,
                question=question,
                answer=answer,
                image=image,  # Handle image upload or storage logic here
                points=points
            )
        
        return JsonResponse({'success': True, 'message': 'Operation successful!'})
    else:
        return JsonResponse({'success' : False,'error': 'Invalid request method'})

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

        # Update homework fields based on the request data
        print("hw name: " + str(homework.title))

        data = json.loads(request.body)
        homework_name = data['homeworkName']
        # homework_name = request.POST.get('homeworkName')
        if homework_name:
            homework.title = homework_name
            print("homework_name: " + str(homework_name))
            homework.save()
        else:
            return JsonResponse({'message': 'Homework name is required'}, status=400)

        received_pairs = data.get('pairs', [])
        existing_pairs = QuestionAnswerPair.objects.filter(homework=homework)
        
        # Extract IDs from received pairs
        received_pair_ids = set(pair.get('id') for pair in received_pairs if pair.get('id'))
        
        # Check and delete pairs that are missing from received data
        for existing_pair in existing_pairs:
            if existing_pair.id not in received_pair_ids:
                existing_pair.delete()

        for index, pair in enumerate(received_pairs):
            question = pair.get('question')
            answer = pair.get('answer')
            image = pair.get('image')  # If image is included in the data
            points = pair.get('points')
            try:
                print(index)
                pair = QuestionAnswerPair.objects.get(homework=homework, id=pair.get('id'))
                pair.question = question
                pair.answer = answer
                pair.image = image
                pair.points = points
                pair.save()
            except QuestionAnswerPair.DoesNotExist:
                print("naujas question")
                pair = QuestionAnswerPair.objects.create(
                    homework=homework,
                    question=question,
                    answer=answer,
                    image=image,
                    points=points
                )

        return JsonResponse({'success': True, 'message': 'Operacija atlikta sėkmingai!'})

    elif request.method=="DELETE":
        homework = Homework.objects.get(pk=pk)
        homework.delete()
        return JsonResponse({'success': True})

    elif request.method=="GET":
        try:
            homework = Homework.objects.get(pk=pk)
            pairs = QuestionAnswerPair.objects.filter(homework=homework).values('id','question', 'answer', 'points', 'image')           
            homework_data = {
                'title': homework.title,
                'pairs': list(pairs)
            }
            return JsonResponse({'success': True, 'homework': homework_data})
        except Homework.DoesNotExist:
            return JsonResponse({'message': 'Homework not found'}, status=404)

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

        # existing_assignment = Assignment.objects.filter(
        #     classs=classs,
        #     homework=homework,
        #     Q(from_date__lte=datetime.strptime(toDate, '%Y-%m-%d').date()) &
        #     Q(to_date__gte=datetime.strptime(fromDate, '%Y-%m-%d').date())
        # )

        # if existing_assignment.exists():
        #     return JsonResponse({'success': False, 'message': 'Homework already assigned to this class'}, status=400)

        assignment = Assignment(classs=classs, homework=homework, from_date=fromDate, to_date=toDate)
        assignment.save()
        return JsonResponse({'success' : True, 'message': 'Operacija sėkminga!'})

@csrf_exempt
def get_classes_by_teacher(request):
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
        try:
            classes = Class.objects.filter(teacher=teacher)
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

#mokytojo studentai, mokytojas patvirtina,atmeta studenta
@csrf_exempt
def handle_teacher_students(request):
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
    if request.method=='GET':
        students_of_teacher = StudentTeacher.objects.filter(teacher=teacher)
        student_ids = students_of_teacher.values_list('student_id', flat=True)
        students = CustomUser.objects.filter(id__in=student_ids).order_by('first_name', 'last_name')

        students_data = [
            {
                'id': student.id,
                'name': student.first_name,
                'surname': student.last_name,
            }
            for student in students
        ]

        return JsonResponse({'students': students_data})
    elif request.method == 'POST':
        data = json.loads(request.body)
        student_id = data['student_id']
        if not student_id:
            return JsonResponse({'success': False, 'error': 'Student ID is required'}, status=400)

        student = CustomUser.objects.filter(pk=student_id).first()
        if not student:
            return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)

        teacher_student, created = StudentTeacher.objects.get_or_create(student=student, teacher=teacher)
        deleteConfirm = StudentTeacherConfirm.objects.get(student=student, teacher=teacher)
        deleteConfirm.delete()
        if created:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Relationship already exists'}, status=400)

    elif request.method == 'DELETE':
        data = json.loads(request.body)
        student_id = data['student_id']
        if not student_id:
            return JsonResponse({'success': False, 'error': 'Student ID is required'}, status=400)

        student = CustomUser.objects.filter(pk=student_id).first()
        if not student:
            return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)

        teacher_student = StudentTeacherConfirm.objects.filter(student=student, teacher=teacher).first()
        if not teacher_student:
            return JsonResponse({'success': False, 'error': 'Relationship not found'}, status=404)

        teacher_student.delete()
        return JsonResponse({'success': True})

    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

#return teachers by school
@csrf_exempt
def handle_teachers(request):
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
    student = CustomUser.objects.get(email=email)
    if not student:
        return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)
    school = student.school
    if request.method=='GET':
        teachers = CustomUser.objects.filter(
        role="2",  # Assuming "2" is the role for teachers
        school=school
        ).exclude(
            teacher_s__student=student  # Exclude teachers connected via StudentTeacher
        ).exclude(
            teacher_c__student=student  # Exclude teachers connected via StudentTeacherConfirm
        ).distinct()

        teachers_data = [
        {
            'id': teacher.id,
            'name': teacher.first_name,
            'surname': teacher.last_name,
        }
        for teacher in teachers]

        return JsonResponse({'success': True, 'teachers': teachers_data})

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)   

@csrf_exempt
def get_not_confirmed_students(request):
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
    if request.method=='GET':
        students_of_teacher = StudentTeacherConfirm.objects.filter(teacher=teacher)
        student_ids = students_of_teacher.values_list('student_id', flat=True)
        students = CustomUser.objects.filter(id__in=student_ids)

        students_data = [
            {
                'id': student.id,
                'name': student.first_name,
                'surname': student.last_name,
            }
            for student in students
        ]

        return JsonResponse({'students': students_data})
#studento mokytojai, student pasirenka mokytoja, pasalina?(admin jau)
@csrf_exempt
def handle_student_teachers(request):
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
    student = CustomUser.objects.get(email=email)
    if request.method=='GET':
        teachers_of_student = StudentTeacher.objects.filter(student=student)
        teacher_ids = teachers_of_student.values_list('teacher_id', flat=True)
        teachers = CustomUser.objects.filter(id__in=teacher_ids)

        teachers_data = [
            {
                'id': teacher.id,
                'name': teacher.first_name,
                'surname': teacher.last_name,
            }
            for teacher in teachers
        ]

        return JsonResponse({'teachers': teachers_data})
    elif request.method == 'POST':
        data = json.loads(request.body)
        teacher_id = data['teacher_id']
        if not teacher_id:
            return JsonResponse({'success': False, 'error': 'teacher ID is required'}, status=400)

        teacher = CustomUser.objects.get(pk=teacher_id)
        if not teacher:
            return JsonResponse({'success': False, 'error': 'teacher not found'}, status=404)

        student_teacher, created = StudentTeacherConfirm.objects.get_or_create(teacher=teacher, student=student)
        if created:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Relationship already exists'}, status=400)
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        teacher_id = data['teacher_id']
        if not teacher_id:
            return JsonResponse({'success': False, 'error': 'teacher ID is required'}, status=400)

        teacher = CustomUser.objects.get(pk=teacher_id)
        if not teacher:
            return JsonResponse({'success': False, 'error': 'teacher not found'}, status=404)

        student_teacher = StudentTeacherConfirm.objects.get(teacher=teacher, student=student)
        student_teacher.delete()
        return JsonResponse({'success': True})

    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

@csrf_exempt
def get_not_confirmed_teachers(request):
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
    student = CustomUser.objects.get(email=email)
    if request.method=='GET':
        teachers_of_student = StudentTeacherConfirm.objects.filter(student=student)
        teacher_ids = teachers_of_student.values_list('teacher_id', flat=True)
        teachers = CustomUser.objects.filter(id__in=teacher_ids)

        teachers_data = [
            {
                'id': teacher.id,
                'name': teacher.first_name,
                'surname': teacher.last_name,
            }
            for teacher in teachers
        ]
        return JsonResponse({'teachers': teachers_data})
    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


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
    if request.method=="POST":
        #if(role=="2" or role=="3"):
        data = json.loads(request.body.decode('utf-8'))
        title = data.get("title")
        classs = Class(title=title, teacher=teacher)
        classs.save()
        return JsonResponse({'success' : True, 'message': 'Operacija sėkminga!'})
    elif request.method == 'GET':
        try:
            #TODO: tik mokytojo klasės
            #classes = Class.objects.all().values('id', 'title')
            classes = Class.objects.filter(teacher=teacher).values('id', 'title')
            classes_list = list(classes)
            return JsonResponse(classes_list, safe=False, status=200)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Method not allowed.'}, status=405)
  
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

@csrf_exempt
def handle_teacher_class(request, cid):
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
    email = payload.get('email')
    teacher = get_object_or_404(CustomUser, email=email)
    classs = get_object_or_404(Class, pk=cid)

    if request.method == "GET":
        # TODO: Check if the user is a teacher       
        # Filter students associated with the specified teacher
        students_of_teacher = CustomUser.objects.filter(student_t__teacher=teacher)
        print(students_of_teacher)

        # Filter CustomUser instances not associated with the specified class
        students_not_in_class = students_of_teacher.exclude(student__classs=classs)
        print(students_not_in_class)
        students_data = [
                {'id' : student.pk, 'name': student.first_name, 'surname': student.last_name}
                for student in students_not_in_class
            ]
        return JsonResponse({'students': students_data}) 
    elif request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

        student_id = data.get("id")        
        student = get_object_or_404(CustomUser, pk=student_id) #teacher class student
        studentclass = StudentClass(student=student, classs = classs)
        studentclass.save()
        return  JsonResponse({'success': True})
                     
@csrf_exempt
def handle_students(request):
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
    if request.method == 'DELETE':
        data = json.loads(request.body)
        student_id = data['student_id']
        # student_id = request.POST.get('student_id')
        if not student_id:
            return JsonResponse({'success': False, 'error': 'Student ID is required'}, status=400)

        student = CustomUser.objects.filter(pk=student_id).first()
        if not student:
            return JsonResponse({'success': False, 'error': 'Student not found'}, status=404)

        teacher_student = StudentTeacher.objects.filter(student=student, teacher=teacher).first()
        if not teacher_student:
            return JsonResponse({'success': False, 'error': 'Relationship not found'}, status=404)

        teacher_student.delete()
        return JsonResponse({'success': True})

    else:
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

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
def post_answer(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        student_id = data['student_id']
        assignment_id = data['assignment_id']
        question_id = data['question_id']
        answer = data['answer']
        points = data['points']

        question = QuestionAnswerPair.objects.get(pk=question_id)
        assignment = Assignment.objects.get(pk=assignment_id)
        student = CustomUser.objects.get(pk=student_id)


        pairResult = QuestionAnswerPairResult.objects.create(question=question, assignment=assignment, student=student, answer=answer, points=points)
        return JsonResponse({'success': True, 'id': pairResult.pk})

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

        # Retrieve QuestionAnswerPairResult objects for a given assignment and student
        question_answer_results = QuestionAnswerPairResult.objects.filter(
            assignment__id=aid, student__id=sid
        )
        title = Assignment.objects.get(pk=aid).homework.title
        pairs_dict = {}
        results_list = []

        for pair in question_answer_pairs:
            pairs_dict[pair.question] = {
                'question': pair.question,
                'answer': pair.answer
            }
        assignment = Assignment.objects.get(pk=aid)    
        answered_all, all_questions, student_result = has_answered_all_questions(student, assignment)
        # Create a list of student answers aligned with their respective questions
        for result in question_answer_results:
            question_id = result.question.question
            if question_id in pairs_dict:
                question_answer = pairs_dict[question_id]
                results_list.append({
                    'question': question_answer['question'],
                    'answer': question_answer['answer'],
                    'student_answer': result.answer,
                    'points' : result.points
                })

     
        return JsonResponse({'success': True, 'results': results_list, 'title' : title, 'name' : name, 'questions' : all_questions, 'answers' : student_result})      


# def get_cat_id(request,type):
#     category=Category.objects.get(type=type)
#     data = {
#         'id': category.id
#     }
#     return JsonResponse(data, status=200)

# def get_latests(request):
#     logger.info("latests ")
#     tricks = Trick.objects.order_by('-id')[:4]
#     data = [
#         {
#             'title': trick.title,
#             'description': trick.description,
#             'category': trick.category.type,
#             'link': trick.link,
#             'id':trick.id
#         }
#         for trick in tricks
#     ]
#     return JsonResponse(data, safe=False)

# @csrf_exempt
# def handle_trick(request, cid):
#     token = request.headers.get('Authorization')
    
#     if not token:
#         return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
#     print("handletrick" + token)    
#     try:
#         # Verify and decode the token
#         payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
#     except jwt.InvalidTokenError:
#         return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

#     # Check if the user is an admin
#     is_admin = payload.get('admin', False)    

#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             title = data['title']
#             description = data['description']
#             link = data['link']
#             category_id = cid           
           
#             if not title or not description or not link or not category_id:
#                 return JsonResponse({'success': False, 'error': 'All fields are required'}, status=422)

#             if(is_admin):
#                 category = Category.objects.get(pk=category_id)  # Fetch the category by ID

#                 video_id_match = re.search(r'v=([^\s&]+)', link)
#                 if video_id_match:
#                     video_id = video_id_match.group(1)
#                     embedded_link = f'https://www.youtube.com/embed/{video_id}'
#                 else:
#                     return JsonResponse({'success': False, 'error': 'Invalid YouTube URL'})

#                 trick = Trick(title=title, description=description, link=embedded_link, category=category)
#                 trick.save()
#                 return JsonResponse({'success': True, "id" : trick.pk}, status = 201)
#             else:
#                 return JsonResponse({'success': False, 'error': 'Unauthorized access to create trick'}, status=403)   

#         except (json.JSONDecodeError, KeyError, Category.DoesNotExist) as e:
#             return JsonResponse({'success': False, 'error': str(e)}, status=400)

#     elif request.method == 'GET':
#         try:
#             category = Category.objects.get(pk=cid)
#             tricks = Trick.objects.filter(category__type=category.type)
#             data = [
#                 {
#                     'title': trick.title,
#                     'description': trick.description,
#                     'category': trick.category.type,
#                     'link': trick.link,
#                     'id': trick.id
#                 }
#                 for trick in tricks
#             ]
#             return JsonResponse(data, safe=False)
#         except Category.DoesNotExist:
#             return HttpResponseNotFound("Category not found")
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
#     else:
#         return JsonResponse({'error': 'Method not allowed.'}, status=405)

# @csrf_exempt
# def handle_trick_id(request, cid, tid):
#     token = request.headers.get('Authorization')
    
#     if not token:
#         return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
#     print("handletrickid" + token)
#     try:
#         # Verify and decode the token
#         payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
#     except jwt.InvalidTokenError:
#         return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

#     # Check if the user is an admin
#     is_admin = payload.get('admin', False)

#     if request.method == 'GET':
#         try:
#             trick = Trick.objects.get(pk=tid)
#             data = {
#                 'title': trick.title,
#                 'description': trick.description,
#                 'category': trick.category.id,
#                 'link': trick.link
#             }
#             return JsonResponse(data, status=200)
#         except Trick.DoesNotExist:
#             return HttpResponseNotFound("Trick not found")
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

#     elif request.method == 'PUT':
#         if(is_admin):
#             try:
#                 trick = Trick.objects.get(pk=tid)
#             except Trick.DoesNotExist:
#                 return HttpResponseNotFound("Trick not found")
#             try:
#                 data = json.loads(request.body.decode('utf-8'))
#             except json.JSONDecodeError:
#                 return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

#             new_title = data.get("title")
#             new_description = data.get("description")
#             new_link = data.get("link")
#             category_id = data.get("category")

#             if not new_title or not new_description or not new_link or not category_id:
#                 return JsonResponse({'success': False, 'error': 'All fields are required'}, status=422)

#             if new_link != trick.link:
#                 video_id_match = re.search(r'v=([^\s&]+)', new_link)
#                 if video_id_match:
#                     video_id = video_id_match.group(1)
#                     new_link = f'https://www.youtube.com/embed/{video_id}'
#                 else:
#                     return JsonResponse({'success': False, 'error': 'Invalid YouTube URL'}, status=422)

#             try:
#                 new_category = Category.objects.get(pk=category_id)
#             except Category.DoesNotExist:
#                 return JsonResponse({'success': False, 'error': f'Category with ID {category_id} does not exist'}, status=404)

#             trick.title = new_title
#             trick.description = new_description
#             trick.link = new_link
#             trick.category = new_category

#             try:
#                 trick.save()
#                 return JsonResponse({'success': True, "id" : trick.pk},   status=200)
#             except Exception as e:
#                 return JsonResponse({'success': False, 'error': str(e)}, status=500)
#         else:
#             return JsonResponse({'success': False, 'error': 'Unauthorized access to update trick'}, status=403) 

#     elif request.method == 'DELETE':
#         if(is_admin):
#             try:          
#                 trick = Trick.objects.get(pk=tid)
#                 trick.delete()
#                 return HttpResponse(status=204)
#             except Trick.DoesNotExist:
#                 return HttpResponseNotFound("Trick not found")
#             except json.JSONDecodeError:
#                 return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
#         else:
#             return JsonResponse({'success': False, 'error': 'Unauthorized access to delete trick'}, status=403) 

#     else:
#         return HttpResponseServerError("Internal Server Error")
    
# #---------------
# @csrf_exempt
# def handle_comment(request,cid,tid):
#     token = request.headers.get('Authorization')
    
#     if not token:
#         return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
#     print("handlecomment" + token)    
#     try:
#         # Verify and decode the token
#         payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
#     except jwt.InvalidTokenError:
#         return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

#     if request.method == 'GET':
#         try:
#             comments = Comment.objects.filter(trick_id=tid)
#             comment_list = [{'id': comment.id,'text': comment.text, 'user': comment.user.username, 'date': comment.date.strftime('%Y-%m-%d')} for comment in comments]
#             return JsonResponse({'success': True, 'comments': comment_list})
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

#     elif request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             text = data.get('text')
#             date = datetime.now().date()

#             # Check if the user is an admin
#             username_from_token = payload.get('username', False)
#             # Retrieve the user instance based on the username from the token
#             user = User.objects.get(username=username_from_token)

#             if not text or not user:
#                 return JsonResponse({'success': False, 'error': 'All fields are required'}, status=422)

        
#             trick = Trick.objects.get(pk=tid) 
#         except Trick.DoesNotExist:
#             return JsonResponse({'success': False, 'error': f'Trick with ID {tid} does not exist'}, status=404)
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

#         try:
#             comment = Comment(text=text, date=date, trick=trick, user=user) 
#             comment.save()
#             return JsonResponse({'success': True, "id" : comment.pk}, status = 201)
        
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)}, status=500)

#     else:
#         return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

# #TODO: visada grazint ir jwt??
# @csrf_exempt
# def handle_comment_id(request, cid,tid,ccid):
#      # Extract token from request headers
#     token = request.headers.get('Authorization')
    
#     if not token:
#         return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
#     print("handlecommentid" + token)
#     try:
#         # Verify and decode the token
#         payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
#     except jwt.InvalidTokenError:
#         return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

#     # Check if the user is an admin
#     is_admin = payload.get('admin', False)

#  # Retrieve the comment by ID
#     try:
#         comment = Comment.objects.get(pk=ccid)
#     except Comment.DoesNotExist:
#         return HttpResponseNotFound("Comment not found")
#     except json.JSONDecodeError:
#         return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

#     if request.method == 'GET':
#         data = {
#             'id': comment.id,
#             'text': comment.text,
#             'user': comment.user.id,
#             'date': comment.date.strftime('%Y-%m-%d')
#         }
#         return JsonResponse(data, status=200)

#     elif request.method == 'PUT':
        
#         try:
#             data = json.loads(request.body.decode('utf-8'))
#             new_text = data.get("text")
#             print(new_text)
#             if not new_text:
#                 return JsonResponse({'success': False, 'error': 'All fields are required'}, status=422)

#             if is_admin or comment.user.username == payload.get('username'):
#                 comment.text = new_text
#                 comment.save()
#                 return JsonResponse({'success': True, "id" : comment.pk}, status = 200)
#             else:
#                 return JsonResponse({'success': False, 'error': 'Unauthorized access to update comment'}, status=403)      
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': str(e)}, status=500)

#     elif request.method == 'DELETE':
#         # Access control logic based on user role for DELETE request
#         if is_admin or comment.user.username == payload.get('username'):
#             # Admin can delete any comment or user can delete their own comment
#             comment.delete()
#             return HttpResponse(status=204)
#         else:
#             # User does not have permission to delete the comment
#             return JsonResponse({'success': False, 'error': 'Unauthorized access to delete this comment'}, status=403)

#     else:
#         return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)

# #------------
# @csrf_exempt
# def handle_category(request):
#     token = request.headers.get('Authorization')
    
#     if not token:
#         return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
#     print("handlecategory" + token)
#     try:
#         # Verify and decode the token
#         payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
#     except jwt.InvalidTokenError:
#         return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

#     # Check if the user is an admin
#     is_admin = payload.get('admin', False)

#     if request.method == 'POST':
#         if(is_admin):
#             try:
#                 data = json.loads(request.body)
#                 category_type = data.get('type')

#                 if not category_type:
#                     return JsonResponse({'success': False, 'error': 'Category type is required.'}, status=422)

                
#                 category = Category(type=category_type)
#                 category.save()
#                 return JsonResponse({'success': True, "id" : category.pk}, status=201)
#             except IntegrityError:
#                 return JsonResponse({'success': False, 'error': 'Category type already exists.'}, status=400)
#             except json.JSONDecodeError:
#                 return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
#         else:
#             return JsonResponse({'success': False, 'error': 'Unauthorized access to create category'}, status=403) 

#     elif request.method == 'GET':
#         try:
#             categories = Category.objects.all().values('id', 'type')
#             categories_list = list(categories)
#             return JsonResponse(categories_list, safe=False, status=200)
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
#     else:
#         return JsonResponse({'error': 'Method not allowed.'}, status=405)



# @csrf_exempt
# def handle_category_id(request, pk):
#     token = request.headers.get('Authorization')
    
#     if not token:
#         return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)
#     print("handlecategoryid" +token)
#     try:
#         # Verify and decode the token
#         payload = jwt.decode(token, settings.SECRET_KEY_FOR_JWT, algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         return JsonResponse({'success': False, 'error': 'Token has expired'}, status=401)
#     except jwt.InvalidTokenError:
#         return JsonResponse({'success': False, 'error': 'Invalid token'}, status=401)

#     # Check if the user is an admin
#     is_admin = payload.get('admin', False)

#     if request.method == 'GET':
#         try:
#             category = Category.objects.get(pk=pk)
#         except Category.DoesNotExist:
#             return HttpResponseNotFound("Category not found")
#         except json.JSONDecodeError:
#             return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

#         data = {
#             'type': category.type
#         }
#         return JsonResponse(data, status=200)

#     elif request.method == 'DELETE':
#         if(is_admin):
#             try:
#                 category = Category.objects.get(pk=pk)
#             except Category.DoesNotExist:
#                 return HttpResponseNotFound("Category not found")
#             except json.JSONDecodeError:
#                 return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
#         else:
#             return JsonResponse({'success': False, 'error': 'Unauthorized access to delete category'}, status=403)         

#         category.delete()
#         return HttpResponse(status=204)

#     elif request.method == 'PUT':
#         if(is_admin):
#             try:
#                 category = Category.objects.get(pk=pk)
#             except Category.DoesNotExist:
#                 return HttpResponseNotFound("Category not found")

#             try:
#                 data = json.loads(request.body.decode('utf-8'))
#             except json.JSONDecodeError:
#                 return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)

#             new_type = data.get("type")

#             if not new_type:
#                 return JsonResponse({'success': False, 'error': 'All fields are required'}, status=422)

#             category.type = new_type

#             try:
#                 category.save()
#                 return JsonResponse({'success': True, "id" : category.pk}, status=200)
#             except Exception as e:
#                 return JsonResponse({'success': False, 'error': str(e)}, status=500)
#         else:
#             return JsonResponse({'success': False, 'error': 'Unauthorized access to update category'}, status=403)   
#     else:
#         return JsonResponse({'error': 'Method not allowed.'}, status=405)             
