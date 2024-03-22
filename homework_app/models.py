from django.db import models
from django.contrib.auth.models import AbstractUser

class School(models.Model):
    title = models.CharField(max_length=100) 
    license_end = models.DateField()

class Class(models.Model):
    title = models.CharField(max_length=100)
    school = models.ForeignKey(School, related_name='classs', on_delete=models.CASCADE)

class CustomUser(AbstractUser):
    role = models.IntegerField() #1-student 2-teacher 3-admin
    gender = models.IntegerField() #1-man 2-woman
    classs = models.ForeignKey(Class, related_name='user_classs', on_delete=models.CASCADE, null = True)
    school = models.ForeignKey(School, related_name='user_school', on_delete=models.CASCADE)

class Homework(models.Model):
    title = models.CharField(max_length=255)
    date = models.DateField()
    teacher = models.ForeignKey(CustomUser, related_name='homework', on_delete=models.CASCADE)

class Assignment(models.Model):
    classs = models.ForeignKey(Class, related_name='assignment', on_delete=models.CASCADE)
    homework = models.ForeignKey(Homework, related_name='assignment', on_delete=models.CASCADE)
    from_date = models.DateField()
    to_date = models.DateField()

class QuestionAnswerPair(models.Model):
    homework = models.ForeignKey(Homework, related_name='pairs', on_delete=models.CASCADE)
    qtype = models.IntegerField()  #1 - select one, 2 - write, 3-multiple select
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=255, null=True)
    points = models.IntegerField()

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