from rest_framework import serializers

from .utils import get_assignment_status
from .models import Assignment, CustomUser, Homework, Class

class UserSerializer(serializers.ModelSerializer):
    school_title = serializers.CharField(source='school.title')
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'role', 'gender', 'school_title']

class LoginUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'gender']        

class HomeworkSerializer(serializers.ModelSerializer):
    teacher_first_name = serializers.CharField(source='teacher.first_name')
    teacher_last_name = serializers.CharField(source='teacher.last_name')

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