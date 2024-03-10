from rest_framework import serializers

from .utils import get_assignment_status
from .models import Assignment, CustomUser, Homework, Class

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'gender']

class LoginUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'gender']        

class HomeworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Homework
        fields = '__all__'

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    homework = HomeworkSerializer()
    classs = ClassSerializer()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = '__all__'

    def get_status(self, obj):
        status = get_assignment_status(obj)
        return status    