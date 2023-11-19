from django.db import models
# from django.contrib.auth.models import AbstractUser
# from django.contrib.auth.models import BaseUserManager
from django.contrib.auth.models import User


class Homework(models.Model):
    name = models.CharField(max_length=255)

class QuestionAnswerPair(models.Model):
    homework = models.ForeignKey(Homework, related_name='pairs', on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    answer = models.CharField(max_length=255)
    image = models.ImageField(upload_to='homework_images/', null=True, blank=True)

    
# class Category(models.Model):
#     type = models.CharField(max_length=20)

# class Trick(models.Model):
#     title = models.CharField(max_length=25)
#     description = models.CharField(max_length=200)
#     link = models.CharField(max_length=200)
#     category = models.ForeignKey(Category, on_delete=models.CASCADE)


# class Comment(models.Model):
#     date = models.DateField()
#     text = models.CharField(max_length=200)
#     trick = models.ForeignKey(to=Trick, on_delete=models.CASCADE, related_name='comments')
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     #user = models.IntegerField(default=0) #models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='comments') 


# class CompletedTrick(models.Model):
#     user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
#     trick = models.ForeignKey(Trick, on_delete=models.CASCADE)

# class UserProfile(AbstractUser):
#     USER_TYPES = (
#         ('player', 'Player'),
#         ('administrator', 'Administrator'),
#     )
#     user_type = models.CharField(max_length=15, choices=USER_TYPES, default='player')
#     points = models.IntegerField(default=0) 
#     password =  models.CharField(max_length=25)
#     email =  models.CharField(max_length=50)
#     nickname =  models.CharField(max_length=25)
   
# class UserProfileManager(BaseUserManager):
#     def create_user(self, username, password=None, **extra_fields):
#         if not username:
#             raise ValueError('The Username field must be set')
#         user = self.model(username=username, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, username, password=None, **extra_fields):
#         extra_fields.setdefault('user_type', 'administrator')

#         if extra_fields.get('user_type') != 'administrator':
#             raise ValueError('Superuser must have user_type="administrator"')

#         return self.create_user(username, password, **extra_fields)

# @receiver(post_save, sender=CustomUser)
# def assign_default_group(sender, instance, created, **kwargs):
#     if created:
#         if instance.is_superuser:
#             group = Group.objects.get(name='admin')
#         elif instance.is_staff:
#             group = Group.objects.get(name='psychiatrist')
#         else:
#             group = Group.objects.get(name='patient')
#         instance.groups.add(group)