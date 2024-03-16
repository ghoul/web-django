import math
from rest_framework import serializers

from .utils import *
from .models import *

class UserSerializer(serializers.ModelSerializer):
    school_title = serializers.CharField(source='school.title')
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'gender', 'school_title']

class LoginUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'gender']        


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    # homework = serializers.SerializerMethodField() #HomeworkSerializer()
    # classs = serializers.SerializerMethodField() #ClassSerializer()
    homework = serializers.PrimaryKeyRelatedField(queryset=Homework.objects.all())
    classs = serializers.PrimaryKeyRelatedField(queryset=Class.objects.all()) 
    status = serializers.SerializerMethodField()

    homework_title = serializers.CharField(source='homework.title')
    teacher_first_name = serializers.CharField(source='homework.teacher.first_name')
    teacher_last_name = serializers.CharField(source='homework.teacher.last_name')
    classs_title = serializers.CharField(source='classs.title')
     
    class Meta:
        model = Assignment
        fields = '__all__'

    def get_status(self, obj):
        return get_assignment_status(obj)

    def update(self, instance, validated_data):
        # # class_data = validated_data.get('classs')
        # # class_title = class_data.get('title')
        # # school = class_data.get('school')
        # # class_instance, created = Class.objects.get_or_create(title=class_title, school=school)

        # # # Update the instance with the new Class object
        # # instance.classs = class_instance

        # instance.classs = Class.objects.get(pk=1)#validated_data.get('classs', instance.classs)
        # instance.homework = Homework.objects.get(pk=61)#validated_data.get('homework', instance.homework)
        # return super().update(instance, validated_data)    
           # Extract and update nested fields

        homework_data = validated_data.pop('homework', None)
        class_data = validated_data.pop('classs', None)

        # Update instance fields
        # instance.from_date = validated_data.get('from_date', instance.from_date)
        # instance.to_date = validated_data.get('to_date', instance.to_date)

        # Handle nested fields
        if homework_data:
            homework_instance = instance.homework
            homework_serializer = self.fields['homework']
            updated_homework = homework_serializer.update(homework_instance, homework_data)
            instance.homework = updated_homework

        if class_data:
            class_instance = instance.classs
            class_serializer = self.fields['classs']
            updated_class = class_serializer.update(class_instance, class_data)
            instance.classs = updated_class

        # Save and return the updated instance
        instance.save()
        return super().update(instance, validated_data)    # instance


class AssignmentResultSerializer(serializers.ModelSerializer):
    grade = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField() # just points from questions, without enemies kill, instance.points - su viskuo
    status = serializers.SerializerMethodField()
    student_first_name = serializers.CharField(source='student.first_name')
    student_last_name = serializers.CharField(source='student.last_name')
    student_gender = serializers.CharField(source='student.gender')
    student_id = serializers.IntegerField(source = 'student.id')

    homework_title = serializers.CharField(source='assignment.homework.title')
    teacher_first_name = serializers.CharField(source='assignment.homework.teacher.first_name')
    teacher_last_name = serializers.CharField(source='assignment.homework.teacher.last_name')
    classs_title = serializers.CharField(source='assignment.classs.title')

    class Meta:
        model = AssignmentResult
        fields = '__all__'  #('id', 'date', 'time', 'points') #'status', 'student', 'grade', 'score'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['date'] = instance.date.strftime('%Y-%m-%d')
        representation['time'] = instance.time.strftime('%H:%M:%S')  
        return representation


    def get_status(self, instance):
        answered_all = has_answered_all_questions(instance.student, instance.assignment)
        if answered_all:
            status = 'Good'
        else: 
            status = 'Average'
        return status        

    def get_score(self, instance):
       return calculate_score(instance.student, instance.assignment)

    def get_grade(self, instance):
        score = calculate_score(instance.student, instance.assignment)
        return calculate_grade(score, instance.assignment)

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = '__all__'

class CorrectOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionCorrectOption   
        fields = '__all__'

class HomeworkSerializer(serializers.ModelSerializer):
    teacher_first_name = serializers.CharField(source='teacher.first_name')
    teacher_last_name = serializers.CharField(source='teacher.last_name')
    num_questions = serializers.SerializerMethodField()
    pairs = serializers.SerializerMethodField()

    class Meta:
        model = Homework
        fields = '__all__'

    def get_pairs(self, obj):
        pairs = QuestionAnswerPair.objects.filter(homework=obj)  
        serializer = QuestionAnswerPairSerializer(pairs, many=True)
        return serializer.data    

    def get_num_questions(self,obj):
        num = QuestionAnswerPair.objects.filter(homework=obj).count()
        return num    



class QuestionAnswerPairSerializer(serializers.ModelSerializer):
    # homework = HomeworkSerializer()
    options = OptionSerializer(many=True, source='option')
    correct_options = CorrectOptionsSerializer(many=True, source='questiono') 

    def get_correct_options(self, obj):
        correct_options = Option.objects.filter(questiono__question=obj)
        return OptionSerializer(correct_options, many=True).data

    class Meta:
        model = QuestionAnswerPair
        fields = '__all__'

class QuestionSelectedOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionSelectedOption
        fields = '__all__'

class QuestionAnswerPairResultSerializer(serializers.ModelSerializer):
    question = QuestionAnswerPairSerializer()
    selected_options = QuestionSelectedOptionSerializer(many=True, source='question.questionoselect')
    student = LoginUserSerializer()
    class Meta:
        model = QuestionAnswerPairResult
        fields = '__all__'   

class CorrectOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionCorrectOption   
        fields = '__all__'    

class TestSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, source='option')
    homework_title = serializers.CharField(source='homework.title', read_only=True)

    class Meta:
        model = QuestionAnswerPair
        fields = ['id', 'question', 'options', 'qtype', 'points', 'homework_title'] 
    


