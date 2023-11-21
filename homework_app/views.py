from datetime import datetime
import json
from xml.etree.ElementTree import Comment
from django.http import HttpResponse,Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse,HttpResponseNotFound, HttpResponseBadRequest,HttpResponseServerError
from homework_app.models import Homework,QuestionAnswerPair, Class, StudentClass, HomeworkResult, School, Assignment
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

        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email is already taken.'}, status=400)

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


def home(request):
    return HttpResponse("Hello, Django!")

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
        homework_name = request.POST.get('homeworkName')
        date = datetime.now().date()

        # Create a new homework object
        homework = Homework.objects.create(title=homework_name, date=date, teacher=teacher)

        # Determine the number of pairs based on the 'pairs' prefix in the form data
        # num_pairs = len([key for key in request.POST if key.startswith('pairs[')])
        # num_pairs = int(num_pairs / 4)
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
        homework_name = request.POST.get('homeworkName')
        if homework_name:
            homework.title = homework_name
            homework.save()
        else:
            return JsonResponse({'message': 'Homework name is required'}, status=400)

        # Update or create question-answer pairs based on the request data
        for i in range(len(request.POST.getlist('pairs[0][question]'))):
            question = request.POST.getlist(f'pairs[{i}][question]')[0]
            answer = request.POST.getlist(f'pairs[{i}][answer]')[0]
            image = request.FILES.getlist(f'pairs[{i}][image]')[0] if request.FILES.getlist(f'pairs[{i}][image]') else None
            points = request.POST.getlist(f'pairs[{i}][points]')[0]

            # Check if the pair exists and update it, otherwise create a new one
            try:
                pair = QuestionAnswerPair.objects.get(homework=homework, id=i + 1)
                pair.question = question
                pair.answer = answer
                pair.image = image
                pair.points = points
                pair.save()
            except QuestionAnswerPair.DoesNotExist:
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
            pairs = QuestionAnswerPair.objects.filter(homework=homework).values('question', 'answer', 'points')           
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
    teacher = CustomUser.objects.filter(email=email)
    if request.method=="POST":
        #if(role=="2" or role=="3"):
        data = json.loads(request.body.decode('utf-8'))
        title = data.get("title")
        classs = Class(title=title, teacher=teacher)
        classs.save()
        return JsonResponse({'success' : True, 'message': 'Operacija sėkminga!'})
    elif request.method == 'GET':
        try:
            classes = Class.objects.all().values('id', 'title')
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
