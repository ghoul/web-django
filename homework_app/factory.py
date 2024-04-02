from datetime import datetime
import factory
from faker import Faker
from .models import *


fake = Faker()

class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School

    title = factory.Faker("company")
    license_end = fake.future_date(end_date='+10y')


class CustomUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomUser

    username = factory.Faker("name")
    password = factory.Faker("password")
    email = factory.Faker("email")
    role = 1
    gender = 1
    school = factory.SubFactory(SchoolFactory) 


class ClassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Class

    title = factory.Faker("sentence")
    school = factory.SubFactory(SchoolFactory) 


class HomeworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Homework

    title = factory.Faker("sentence")
    date = datetime.now().date()
    teacher = factory.SubFactory(CustomUserFactory)        

class AssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Assignment

    homework = factory.SubFactory(HomeworkFactory) 
    classs = factory.SubFactory(ClassFactory)
    from_date = datetime.now().date()
    to_date = fake.future_date(end_date='+10d')  

class AssignmentResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssignmentResult

    assignment = factory.SubFactory(AssignmentFactory) 
    student = factory.SubFactory(CustomUserFactory)
    date = factory.Faker("date")
    points = factory.Faker("random_int", min=0, max=100) 
    time = factory.Faker("time")