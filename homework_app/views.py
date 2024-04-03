from .models import *
from .serializers import *
from .utils import *

from datetime import datetime, timedelta, date
from django.http import JsonResponse
from django.db.models import Q, Subquery,Sum, Value, IntegerField, Subquery
from django.db.models.functions import Concat
from django.contrib.auth import login
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import Token
from rest_framework import serializers
from rest_framework.authentication import  SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import mixins
from rest_framework import viewsets

from io import TextIOWrapper
import csv

import logging
logger = logging.getLogger(__name__)


################
#### WEBSITE ###
################

# viewset for logging user in
class LoginViewUser(viewsets.GenericViewSet):
    serializer_class = UserSerializer

    def post(self, request):
        user = CustomUser.objects.get(email=request.data.get('email'))
        if user.check_password(request.data.get('password')):
            license_end = user.school.license_end
            if license_end and license_end < datetime.today().date():
                return Response({"error": "Jūsų licenzija nebegalioja"}, status=status.HTTP_403_FORBIDDEN)

            login(request, user)
            serializer = self.get_serializer(user)
            token, created = Token.objects.get_or_create(user=user)
            csrf_token = generate_csrf_token(request)

            return Response({"token": token.key, "user": serializer.data, "csrf_token": csrf_token})
        else:
            return Response({"error": "Neteisingas el. paštas arba slaptažodis"}, status=status.HTTP_400_BAD_REQUEST)


# viewset for changing user's password
class PasswordView(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            if str(request.user.id) != kwargs['pk']:
                return Response({"error": "Prieiga uždrausta"}, status=status.HTTP_403_FORBIDDEN)
            return super().update(request, *args, **kwargs)
        else:
            return Response({"error" : "Neužpildyti privalomi laukai"}, status=status.HTTP_400_BAD_REQUEST)


# viewset for returning all active assignments created by teacher
class AssignmentListViewTeacher(mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         

    def get_queryset(self):
        return Assignment.objects.filter(
            homework__teacher=self.request.user, 
            to_date__gte=date.today(),  
        )
    serializer_class = AssignmentSerializer


# viewset for returning all active and not finished assignments for student
class AssignmentListViewStudent(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsStudent]         
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        finished_assignments = AssignmentResult.objects.filter(student=self.request.user).values('assignment')

        return Assignment.objects.filter(
            classs=self.request.user.classs,
            from_date__lte=date.today(), 
            to_date__gte=date.today()  
        ).exclude(id__in=Subquery(finished_assignments))


# viewset for returning all finished assignments created by teacher    
class AssignmentListViewTeacherFinished(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         

    def get_queryset(self):
        return Assignment.objects.filter(
        homework__teacher = self.request.user,
        to_date__lte=date.today(),
    )
    serializer_class = AssignmentSerializer


# viewset for returning all finished assignments by student
class AssignmentListViewStudentFinished(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsStudent]         
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        finished_assignments = AssignmentResult.objects.filter(student=self.request.user).values_list('assignment__id', flat=True)

        return Assignment.objects.filter(
            Q(classs=self.request.user.classs) &  #filter by student class
            (Q(to_date__lt=date.today()) | Q(id__in=finished_assignments))  #past or finished assignments
        )


# viewset for assigning homework to class and editing assignment
class AssignmentView(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         
    serializer_class = AssignmentSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user == instance.homework.teacher:
            return Response({"error": "Prieiga uždrausta"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        else:
            return Response({"error" : "Netinkamai užpildyta forma"}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({"error" : "Netinkamai užpildyta forma"}, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return Assignment.objects.all()


# viewset for returning all classes in teacher's school
class ClassesListView(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsTeacher]         
    serializer_class = ClassSerializer
    def get_queryset(self):
        return Class.objects.filter(school = self.request.user.school)


# viewset for viewing and updating user's profile information (email)
class ProfileViewUser(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated] 
    serializer_class = UserSerializer     
    def get_queryset(self):
        return CustomUser.objects.all()
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        if 'email' in request.data and len(request.data) == 1:
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response(serializer.data)
            else:
                return Response({"error" : "Netinkamai užpildyta forma"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Netinkamai užpildyta forma"}, status=status.HTTP_400_BAD_REQUEST)    


# viewset for viewing statistics of selected assignment - returns all students of class with their scores, times and grades
class AssignmentViewStatistics(mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AssignmentResultSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            assignment_id = self.kwargs.get('pk')
            assignment = Assignment.objects.get(pk=assignment_id)

            # retrieve finished students assignment results
            queryset = AssignmentResult.objects.filter(assignment=assignment)
            serializer = self.get_serializer(queryset, many=True)
            finished_students_data = serializer.data
            # retrieve not finished students with zero values
            students = CustomUser.objects.filter(classs=assignment.classs)
            not_finished_students = CustomUser.objects.filter(id__in=students.values('id')).exclude(
                results__in=queryset
            ).annotate(
                points=Value(0, output_field=IntegerField()),
                time=Value('00:00:00', output_field=models.TimeField()),
                status = Value('Bad', output_field = models.CharField()),
                grade=Value(0, output_field=IntegerField())
            ).annotate(
                student_first_name=Concat('first_name', Value(''), output_field=models.CharField()),
                student_last_name=Concat('last_name', Value(''), output_field=models.CharField())
            ).values('student_first_name', 'student_last_name', 'gender', 'points', 'time', 'status', 'grade')

            # Combine finished and not finished students data
            all_students_data = finished_students_data + list(not_finished_students)
            
            #sort firstly by points, then by time, then by name
            sorted_students = sorted(all_students_data, key=sort_students)

            response_data = {
                'assignment': {
                    'title': assignment.homework.title,
                    'class_title': assignment.classs.title
                },
                'assignment_results': sorted_students
            }

            return Response(response_data)
        except Assignment.DoesNotExist: 
            return Response({"error": "Namų darbas nerastas"}, status=status.HTTP_404_NOT_FOUND)   


# viewset for returning list of one class students for the podium with their points
class ClassViewStatistics(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        classs = request.user.classs
        students = CustomUser.objects.filter(classs=classs)
        assignments = Assignment.objects.filter(classs=classs)
        leaderboard_entries = []

        start_date, end_date = get_current_school_year()

        for student in students:
            assignment_results = AssignmentResult.objects.filter(
                student=student,
                assignment__in=assignments,
                date__range=(start_date, end_date)
            ).aggregate(total_points=Sum('points'))

            total_points = assignment_results['total_points'] or 0

            leaderboard_entries.append({
                'student': f"{student.first_name} {student.last_name}",
                'gender': student.gender,
                'points': total_points
            })

        sorted_leaderboard = sorted(leaderboard_entries, key=lambda x: (-x['points'], x['student']))
        response_data = {
            'leaderboard': sorted_leaderboard,
            'class_title': classs.title
        }

        return Response(response_data)


# viewset for viewing one student's finished assignment, shows answers, scored points, grade
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

        if not queryset.exists():
            return Response({"error": "Statistika nerasta"}, status=status.HTTP_404_NOT_FOUND)   

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


# viewset for creating, updating, retrieving, deleting homework
class HomeworkView(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                                                                     mixins.CreateModelMixin, viewsets.GenericViewSet):
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

    # function for creating question with answers, deals with three types of questions and creates options if needed
    def create_question_answer_pairs(self, request, homework):
        data = []
        num_pairs = sum('question' in key for key in request.POST.keys())
        if num_pairs > 0:
            qtype_mapping = {'select': 1, 'write': 2, 'multiple': 3}

            for i in range(num_pairs):
                qtype = request.POST.get(f'pairs[{i}][qtype]')
                qtype = qtype_mapping.get(qtype, None)
                question = request.POST.get(f'pairs[{i}][question]')
                answer = request.POST.get(f'pairs[{i}][answer]')
                points = request.POST.get(f'pairs[{i}][points]')

                if len(answer) == 0:
                    answer = None              

                qapair_serializer = QuestionAnswerPairSerializer(data={'homework': homework.id, 'qtype': qtype, 'question': question, 'answer' : answer, 'points': points}, context={'request': request})
                if qapair_serializer.is_valid():
                    qapair = qapair_serializer.save()
                    data.append(qapair_serializer.data)

                    num_options = sum(key.startswith(f'pairs[{i}][options]') for key in request.POST.keys())
                    if (qtype == 1 or qtype == 3) and num_options > 0: 
                        options = []

                        for option_i in range(num_options):
                            option_text = request.POST.get(f'pairs[{i}][options][{option_i}]')
                            option_serializer = OptionSerializer(data={'text': option_text, 'question': qapair.id}, context={'request': request})
                            if option_serializer.is_valid():
                                option = option_serializer.save()
                                options.append(option)

                                if qtype == 3:  # select multiple options question   
                                    num_mult = sum(key.startswith(f'pairs[{i}][multipleOptionIndex]') for key in request.POST.keys())
                                    if num_mult>0:                                                      
                                        for y in range(num_mult):  
                                            if request.POST.get(f'pairs[{i}][multipleOptionIndex][{y}]') is not None:                              
                                                correct = int(request.POST.get(f'pairs[{i}][multipleOptionIndex][{y}]'))
                                                if correct==option_i:
                                                    create_correct_option(qapair, option)  
                                            else:
                                                return "", status.HTTP_400_BAD_REQUEST,"Namų darbų forma užpildyta neteisingai: nepasirinkti teisingi atsakymai"         
                                    else:
                                        return "", status.HTTP_400_BAD_REQUEST, "Namų darbų forma užpildyta neteisingai: nėra atsakymo pasirinkimų"                
                            else:
                                return "", status.HTTP_400_BAD_REQUEST, "Namų darbų forma užpildyta neteisingai"

                        if qtype == 1: #select one option question
                            if request.POST.get(f'pairs[{i}][correctOptionIndex]') != 'null':                      
                                correct_option_index = int(request.POST.get(f'pairs[{i}][correctOptionIndex]'))
                                if 0 <= correct_option_index < len(options):
                                    create_correct_option(qapair, options[correct_option_index])  
                                else:
                                    return "", status.HTTP_400_BAD_REQUEST, "Namų darbų forma užpildyta neteisingai"    
                                           
                    elif qtype == 2: #writable answer
                        continue 
                    else:
                        return "", status.HTTP_400_BAD_REQUEST, "Namų darbų forma užpildyta neteisingai: nėra atsakymo pasirinkimų"    
                else:
                    return "", status.HTTP_400_BAD_REQUEST, "Namų darbų forma užpildyta neteisingai"                        
            return data, status.HTTP_201_CREATED, ""
        else:
            return "", status.HTTP_400_BAD_REQUEST, "Namų darbe privalo būti bent vienas klausimas"   

    def create(self, request):
        mutable_data = request.data.copy()
        mutable_data['teacher'] = request.user.id
        mutable_data['date'] = datetime.now().date()

        serializer = self.serializer_class(data=mutable_data)
        if serializer.is_valid():
            homework = serializer.save() 
            data, status, error = self.create_question_answer_pairs(request, homework)
            return Response({"data" : data, "error" : error}, status)
        else:
            return Response({'error': "Namų darbų forma užpildyta neteisingai"}, status=status.HTTP_400_BAD_REQUEST)    

    # function for updating homework - if question is changed, all related information is deleted (options, correct options), 
    # and question is updated, creates completely new questions and deletes deleted questions
    def update(self, request,*args, **kwargs):
        try:
            homework = self.get_object()
        except Homework.DoesNotExist:
            return Response({'error': 'Namų darbas nerastas'}, status=status.HTTP_404_NOT_FOUND)

        homework_name = request.data.get('title')
        multiple = request.data.get('multiple')
        correct = request.data.get('correct')
        correct = [-1 if item is None else item for item in correct]
        print(correct)
        options = [] 

        if not homework_name:
            return Response({'error': 'Nenurodytas namų darbo pavadinimas'}, status=status.HTTP_400_BAD_REQUEST)

        homework.title = homework_name
        homework.save()    

        received_pairs = request.data.get('pairs', [])

        if len(received_pairs) > 0:

            existing_pairs = QuestionAnswerPair.objects.filter(homework=homework)
            qtype_mapping = {'select': 1, 'write': 2, 'multiple': 3}

            received_pair_ids = set(pair.get('id') for pair in received_pairs if pair.get('qid'))

            # deletes deleted questions by teacher
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

                # updating old question with new information
                if not created:
                    if pair_obj.qtype != qtype:
                        Option.objects.filter(question=pair_obj).delete()
                        QuestionCorrectOption.objects.filter(question=pair_obj).delete()

                    pair_obj.qtype = qtype                   
                    pair_obj.question = question
                    pair_obj.answer = answer
                    pair_obj.points = points
                    pair_obj.save()

                options = pair.get('options')

                #deleting old options and creating new 
                if (qtype == 1 or qtype == 3): 
                    if len(options) > 0:
                        try:
                            options_old = Option.objects.filter(question=pair_obj)
                            options_old.delete()
                        except ObjectDoesNotExist:
                            print("")    
                            
                        try:    
                            correct_old = QuestionCorrectOption.objects.filter(question=pair_obj)
                            correct_old.delete()    
                        except ObjectDoesNotExist:
                            print("")       

                        for option_text in options:
                            Option.objects.create(text=option_text, question=pair_obj)

                        if qtype == 1: #select one option question
                            if correct[index] != -1:
                                correct_option_index = correct[index] 
                                if 0 <= correct_option_index < len(options):
                                    correct_option = Option.objects.get(text=options[correct_option_index], question=pair_obj)
                                    QuestionCorrectOption.objects.create(option = correct_option, question = pair_obj)
                                else:
                                    return Response({'error': "Namų darbų forma užpildyta neteisingai"}, status=status.HTTP_400_BAD_REQUEST)                       
                            else:
                                return Response({'error': "Namų darbų forma užpildyta neteisingai: nepasirinkti teisingi atsakymai"}, status=status.HTTP_400_BAD_REQUEST)                   

                        elif qtype == 3: #select multiple options question
                            correct_option_indexes = [item['oid'] for item in multiple if item.get('qid') == index]
                            if len(correct_option_indexes) > 0:
                                for correct_option_index in correct_option_indexes:
                                    QuestionCorrectOption.objects.create(question=pair_obj, option=Option.objects.get(text=options[correct_option_index], question=pair_obj)) 
                            else:
                                return Response({'error': "Namų darbų forma užpildyta neteisingai: nepasirinkti teisingi atsakymai"}, status=status.HTTP_400_BAD_REQUEST)               
                    else:
                        return Response({'error': "Namų darbų forma užpildyta neteisingai: nėra atsakymo pasirinkimų"}, status=status.HTTP_400_BAD_REQUEST)  
                else:
                    continue
                
            return Response(status=status.HTTP_201_CREATED)     
        else:
            return Response({"error" : "Namų darbe privalo būti bent vienas klausimas"}, status=status.HTTP_400_BAD_REQUEST)    


# viewset for retrieving test and saving answers by student
class TestView(mixins.ListModelMixin, mixins.CreateModelMixin,viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, IsStudent]
    serializer_class = TestSerializer

    def get_queryset(self):
        assignment_id = self.kwargs.get('assignment_id')
        homework = Assignment.objects.get(pk=assignment_id).homework
        questions = QuestionAnswerPair.objects.filter(homework=homework)
        return questions

    # function for posting test answers by student
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
            get_points = 0
            selected_options = []

            #checks if question was not answered before (could happen if started test in a game and finished in website)
            try:
                answered_before = QuestionAnswerPairResult.objects.get(question=question, assignment=assignment, student=request.user)
                answered_before.delete()
            except ObjectDoesNotExist:
                print("")
            try:    
                selected = QuestionSelectedOption.objects.filter(assignment=assignment, student=request.user, question=question)
                selected.delete()
            except ObjectDoesNotExist:
                print("")
               
            if qtype == 1: # select one option question
                selected_option = Option.objects.get(pk=answer)
                QuestionSelectedOption.objects.create(option = selected_option, question = question, student = request.user, assignment=assignment)
                correct_option = QuestionCorrectOption.objects.get(question=question).option
                if correct_option == selected_option:
                    get_points=question.points

            elif qtype == 2: # writable answer
                if question.answer.lower() == answer.lower():
                    get_points = question.points

            elif qtype == 3: # select multiple options question
                num_mult = sum(key.startswith(f'pairs[{i}][multipleIndex]') for key in request.POST.keys())
                for y in range(num_mult):
                    optionId = int(request.POST.get(f'pairs[{i}][multipleIndex][{y}]'))
                    selected_option = Option.objects.get(pk=optionId)
                    selected_options.append(selected_option)
                    QuestionSelectedOption.objects.create(assignment=assignment, student=request.user, question=question, option=selected_option)   

                get_points = calculate_points_for_one_question_multiple_select(question, selected_options)
              
            QuestionAnswerPairResult.objects.create(question=question, assignment=assignment, student=request.user, answer=answer, points=get_points)
            total_points+=get_points
            get_points=0

        elapsed_timedelta = timedelta(seconds=elapsed)
        hours, remainder = divmod(elapsed_timedelta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        formatted_time = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

        # saves summary of all test - time, points, date
        AssignmentResult.objects.create(assignment=assignment, student=request.user, date=date, points=total_points, time=formatted_time)

        return Response(status = status.HTTP_201_CREATED)


#################
###### GAME #####
#################

# viewset for retrieving questions in a game and saving answers for separate questions
class QuestionsViewGame(mixins.ListModelMixin, mixins.CreateModelMixin,viewsets.GenericViewSet):
    serializer_class = TestSerializer

    def get_queryset(self):
        assignment_id = self.kwargs.get('assignment_id')
        homework = Assignment.objects.get(pk=assignment_id).homework
        questions = QuestionAnswerPair.objects.filter(homework=homework)
        return questions
        
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serialized_questions = self.serializer_class(queryset, many=True)
        return Response({"questions": serialized_questions.data})

    # function for saving answer of one question
    def post_answer(self, request,*args, **kwargs ):
        assignment_id = request.POST.get('assignment_id', None)
        question_id = request.POST.get('question_id', None)
        player_answer = request.POST.get('answer', '')
        student_id = request.POST.get('student_id', None)
        selected = request.POST.get('selected', None) 

        if assignment_id is not None and question_id is not None and student_id is not None:
            question = QuestionAnswerPair.objects.get(pk=question_id)
            qtype = question.qtype
            assignment = Assignment.objects.get(pk=assignment_id)
            student = CustomUser.objects.get(pk=student_id)
            total_points = 0

            # checks if user plays game again, if yes - old submition of an answer must be updated
            try: 
                previous_answer = QuestionAnswerPairResult.objects.get(assignment=assignment, student=student, question=question)

                if qtype == 3: # select multiple options question                    
                    total_points, selected_options = process_answer(question, selected)

                    QuestionSelectedOption.objects.filter(question=question, student=student, assignment=assignment).delete()
                    for option in selected_options:
                        QuestionSelectedOption.objects.create(question=question, student=student, assignment=assignment, option=option)

                elif qtype == 1: # select one option question
                    option = Option.objects.get(question=question, text=player_answer)
                    correct_option = QuestionCorrectOption.objects.get(question=question).option

                    if correct_option == option:
                        total_points=question.points

                    QuestionSelectedOption.objects.filter(question=question, student=student, assignment=assignment).delete()
                    QuestionSelectedOption.objects.create(question=question, student=student, assignment=assignment, option=option)

                elif qtype == 2: # writable answer
                    previous_answer.answer = player_answer

                    if question.answer.lower() == player_answer.lower():
                        total_points=question.points
                            
                previous_answer.points = total_points
                previous_answer.save()

            # user plays first time and all answers are new
            except ObjectDoesNotExist:
                if qtype == 3: # seelct multiple options question
                    total_points, selected_options = process_answer(question, selected)

                    for option in selected_options:
                        QuestionSelectedOption.objects.create(question=question, student=student, assignment=assignment, option=option)
                
                elif qtype==1: # select one option question
                    option = Option.objects.get(question=question, text=player_answer)
                    correct_option = QuestionCorrectOption.objects.get(question=question).option
                    player_answer = ''
                    if correct_option == option:
                        total_points=question.points

                    QuestionSelectedOption.objects.create(question=question, student=student, assignment=assignment, option=option)

                elif player_answer.lower() == question.answer.lower(): # writable answer
                        total_points=question.points                      
                
                QuestionAnswerPairResult.objects.create(question=question, assignment=assignment, student=student, answer=player_answer, points=total_points)
           
            return JsonResponse({'success': True}, status=status.HTTP_201_CREATED)
            
        return JsonResponse({"success" : False}, status=status.HTTP_400_BAD_REQUEST)       


# viewset for saving summary of finished game - time, date, points
class SummaryView(mixins.CreateModelMixin, viewsets.GenericViewSet):    
    serializer_class = AssignmentResultSerializer
    def get_queryset(self):
        queryset = AssignmentResult.objects.all()
        return queryset

    def create(self, request): 
        assignment_id = request.POST.get('assignment_id', None)
        time = request.POST.get('time', None) 
        student_id = request.POST.get('student_id', None)
        points = request.POST.get('points', None)

        if assignment_id is not None and time is not None and student_id is not None and points is not None:
            assignment = Assignment.objects.get(pk=assignment_id)
            student = CustomUser.objects.get(pk=student_id)
            # calculates scored points from answers and adds to points scored in a game
            points_from_questions = QuestionAnswerPairResult.objects.filter(assignment=assignment, student=student).aggregate(scored_points=Sum('points'))
            total_points = points_from_questions.get('scored_points', 0) + int(points)
            serializer = AssignmentResultSerializer(data={'assignment': assignment_id, 'student': student_id,'date': datetime.now(),'points': total_points,'time': time})
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({"success" : True}, status=status.HTTP_201_CREATED)
            else:
                return JsonResponse({"success" : False}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({"success" : False}, status=status.HTTP_400_BAD_REQUEST)  


#####################
#### ADMIN SCHOOL ###
#####################  

# viewset for creating and deleteing schools by admin
class SchoolViewAdmin(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
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

        try:
            School.objects.get(title=title)
            return Response({"error": "Mokykla jau užregistruota anksčiau"}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            serializer = SchoolSerializer(data={'title': title, 'license_end': license})
            if serializer.is_valid():
                school = serializer.save()
            else:
                return Response({"error" : "Neteisingai užpildyta forma"}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = TextIOWrapper(csv_file, encoding='utf-8', errors='replace')

        # admin uploads file, which is read and from each row new user is created, returns login credentials for each of them
        reader = csv.reader(csv_file, delimiter=';')
        login_data =[]
        reader_list = list(reader)
        if len(reader_list) > 0:
            for row in reader_list:
                if len(row) == 4 :
                    first_name = row[0]
                    last_name = row[1]
                    class_name = row[2]
                    gender = row[3]
                    gender = 1 if gender == 'vyras' else 2
                    role = 2 if class_name == '' else 1 

                    login_user, email, password, classs = get_login_user(first_name, last_name, class_name, school, role)
                    login_data.append(login_user)

                    # creates new user
                    user = CustomUser.objects.create_user(
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

                    # adds created user to either student or teacher group for permissions
                    if class_name:
                        user.groups.add(students_group)
                    else:
                        user.groups.add(teachers_group) 

                else:
                    return Response({"error": "Neteisingai užpildytas duomenų failas"}, status=status.HTTP_400_BAD_REQUEST)           

            # login text file with names, generated emails and passwords
            response = login_file(login_data)

            return response
             
        else:
            return Response({"error": "Tuščias duomenų failas"}, status=status.HTTP_400_BAD_REQUEST)    


# viewset for updating school by admin   
class UpdateViewSchool(APIView):
    def post(self, request, school_id):
        try:
            school = School.objects.get(id=school_id)
        except School.DoesNotExist:
            return Response({'error': 'Mokykla nerasta'}, status=status.HTTP_404_NOT_FOUND)

        csv_file = request.FILES.get("file")
        new_school_title = request.POST.get("title")
        new_license_expire_date = request.POST.get("license")

        if new_school_title:
            school.title = new_school_title
        if new_license_expire_date:
            school.license_end = new_license_expire_date
        school.save()

        # if admin uploads file - each row is processed and either users are created, updated or deleted
        if csv_file:
            response = update_or_create_members(csv_file, school)
            return response

        else:
            return Response({'success': True, 'id' : school_id})