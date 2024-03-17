from datetime import datetime
from operator import mod
from django.db import models
# from django.contrib.auth.models import AbstractUser
# from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser

from django.contrib.auth.models import BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        # Your custom logic for creating a regular user
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Your custom logic for creating a superuser
        extra_fields.setdefault('role', 3)
        extra_fields.setdefault('is_superuser', 1)
        extra_fields.setdefault('school_id', 1)
        extra_fields.setdefault('is_staff', 1) 
        extra_fields.setdefault('gender', 0)
        return self.create_user(email, password, **extra_fields)

class School(models.Model):
    title = models.CharField(max_length=100) 
    license_end = models.DateField( ) #default=datetime.now().date()

class CustomUser(AbstractUser):
    school = models.ForeignKey(School, related_name='school', on_delete=models.CASCADE)
    role = models.IntegerField() #1-mokinys 2-mokytojas 3-admin
    gender = models.IntegerField() #1- vyras 2-moteris
    objects = CustomUserManager()

class Homework(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateField()
    teacher = models.ForeignKey(CustomUser, related_name='homework', on_delete=models.CASCADE)

class Class(models.Model):
    title = models.CharField(max_length=100)
    school = models.ForeignKey(School, related_name='classs', on_delete=models.CASCADE)

class Assignment(models.Model):
    classs = models.ForeignKey(Class, related_name='assignment', on_delete=models.CASCADE)
    homework = models.ForeignKey(Homework, related_name='assignment', on_delete=models.CASCADE)
    from_date = models.DateField()
    to_date = models.DateField()

class QuestionAnswerPair(models.Model):
    homework = models.ForeignKey(Homework, related_name='pairs', on_delete=models.CASCADE)
    qtype = models.IntegerField()  #1 - select #2 - write
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=255, null=True)
    points = models.IntegerField()
    # correct = models.ForeignKey('Option', related_name='qapair', null = True, on_delete=models.CASCADE)
   

class Option(models.Model):
    text = models.CharField(max_length=255)
    question = models.ForeignKey(QuestionAnswerPair, related_name='option', on_delete=models.CASCADE)

class QuestionCorrectOption(models.Model):
    option = models.ForeignKey(Option, related_name='optionq', on_delete=models.CASCADE)
    question = models.ForeignKey(QuestionAnswerPair, related_name='questiono', on_delete=models.CASCADE)

class QuestionSelectedOption(models.Model):
    option = models.ForeignKey(Option, related_name='optionqselect', on_delete=models.CASCADE)
    question = models.ForeignKey(QuestionAnswerPair, related_name='questionoselect', on_delete=models.CASCADE)
    student = models.ForeignKey(CustomUser, related_name='questionselect', on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, related_name='questionselectass', on_delete=models.CASCADE)

class QuestionAnswerPairResult(models.Model):
    question = models.ForeignKey(QuestionAnswerPair, related_name='pairResult', on_delete=models.CASCADE)
    student = models.ForeignKey(CustomUser, related_name='questionResult', on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, related_name='assignmentPair', on_delete=models.CASCADE)
    answer = models.CharField(max_length=255, null=True)
    points = models.IntegerField()
   
class AssignmentResult(models.Model):
    student = models.ForeignKey(CustomUser, related_name='results', on_delete=models.CASCADE)
    assignment = models.ForeignKey(Assignment, related_name='assignment', on_delete=models.CASCADE)
    date = models.DateTimeField()
    points = models.IntegerField()
    time = models.TimeField()

class StudentClass(models.Model):
    student = models.ForeignKey(CustomUser,related_name='student', on_delete=models.CASCADE)
    classs = models.ForeignKey(Class,related_name='classs', on_delete=models.CASCADE)

class StudentTeacher(models.Model):
    student = models.ForeignKey(CustomUser,related_name='student_t', on_delete=models.CASCADE)  
    teacher = models.ForeignKey(CustomUser,related_name='teacher_s', on_delete=models.CASCADE)

class StudentTeacherConfirm(models.Model):
    student = models.ForeignKey(CustomUser,related_name='student_c', on_delete=models.CASCADE)  
    teacher = models.ForeignKey(CustomUser,related_name='teacher_c', on_delete=models.CASCADE)    

