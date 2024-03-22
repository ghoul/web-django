from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .utils import *
from .models import *

class UserSerializer(serializers.ModelSerializer):
    school_title = serializers.CharField(source='school.title')
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'gender', 'school_title']     

class PasswordSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['password']

    def update(self, instance, validated_data):
        instance.password = make_password(validated_data['password'])
        instance.save()
        return instance

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    homework = serializers.PrimaryKeyRelatedField(queryset=Homework.objects.all())
    classs = serializers.PrimaryKeyRelatedField(queryset=Class.objects.all()) 
    status = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = '__all__'
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['homework_title'] = instance.homework.title
        representation['teacher_first_name'] = instance.homework.teacher.first_name
        representation['teacher_last_name'] = instance.homework.teacher.last_name
        representation['classs_title'] = instance.classs.title
        return representation

    def get_status(self, obj):
        return get_assignment_status(obj)

    def update(self, instance, validated_data):
        instance.from_date = validated_data.get('from_date', instance.from_date)
        instance.to_date = validated_data.get('to_date', instance.to_date)
        instance.save()
        return instance

class AssignmentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentResult
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['date'] = instance.date.strftime('%Y-%m-%d')
        representation['time'] = instance.time.strftime('%H:%M:%S')  
        representation['score'] = calculate_score(instance.student, instance.assignment)  #points from questions, without game score
        representation['grade'] = self.get_grade(instance)
        representation['status'] = self.get_status(instance)
        representation['student_first_name'] = instance.student.first_name
        representation['student_last_name'] = instance.student.last_name
        representation['student_gender'] = instance.student.gender
        return representation

    def get_status(self, instance):
        answered_all = has_answered_all_questions(instance.student, instance.assignment)
        status = 'Good' if answered_all else 'Average'
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
    num_questions = serializers.SerializerMethodField()
    pairs = serializers.SerializerMethodField()

    class Meta:
        model = Homework
        fields = '__all__'

    def get_pairs(self, obj):
        pairs = QuestionAnswerPair.objects.filter(homework=obj)  
        serializer = QuestionAnswerPairSerializer(pairs, many=True, context={'request': self.context.get('request')})
        return serializer.data    

    def get_num_questions(self,obj):
        num = QuestionAnswerPair.objects.filter(homework=obj).count()
        return num    

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not request.method == 'POST':  #for get requests
            data['teacher_first_name'] = instance.teacher.first_name
            data['teacher_last_name'] = instance.teacher.last_name
        return data   


class StatisticUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name']


class QuestionAnswerPairSerializer(serializers.ModelSerializer):
    def get_correct_options(self, obj):
        correct_options = Option.objects.filter(optionq__question=obj)
        return OptionSerializer(correct_options, many=True).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if self.context['request'].method == 'GET':
            representation['options'] = OptionSerializer(instance.option.all(), many=True).data
            representation['correct_options'] = self.get_correct_options(instance)
        return representation

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
    student = UserSerializer()
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