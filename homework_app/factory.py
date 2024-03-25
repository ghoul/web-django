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




# class ClassFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Class

#     title = factory.Faker("8C")
#     school = CustomUser.objects.get_or_create(email="agne@gmail.com")[0] 


# class CustomUserFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = CustomUser

#     #TODO: NAMES, EMAIL, PASS?
#     role = 1
#     gender = 1
#     classs = Class.objects.get_or_create(title="8C")
#     school = School.objects.get_or_create(title = "Kauno jėzuitų gimnazija")


# class HomeworkFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Homework

#     title = "Matematika. Daugyba"
#     date = datetime.now()
#     teacher = CustomUser.objects.get_or_create() #TODO??        