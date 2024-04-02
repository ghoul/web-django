from django.test import TestCase
from homework_app.factory import *
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.urls import reverse
from datetime import datetime, timedelta

class LoginViewUserTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        school = School.objects.create(title="school", license_end = datetime.today())
        self.user = CustomUser.objects.create_user(username ='test@example.com', email='test@example.com', 
                                                    password ='testpassword', role=1, gender=1, school=school)
        self.login_url = reverse('login') 

    def test_login_successful(self):
        data = {'email': 'test@example.com', 'password': 'testpassword'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertIn('csrf_token', response.data)

    def test_login_invalid_credentials(self):
        data = {'email': 'test@example.com', 'password': 'wrongpassword'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Neteisingas el. paštas arba slaptažodis')

    def test_login_expired_license(self):
        self.user.school.license_end = datetime.today().date() - timedelta(days=3)
        self.user.school.save()
        self.user.save()
        data = {'email': 'test@example.com', 'password': 'testpassword'}
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['error'], 'Jūsų licenzija nebegalioja')


class PasswordViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUserFactory.create()
        self.client.force_authenticate(user=self.user)

    def test_update_password(self):
        data = {'password': 'changed_password'}
        response = self.client.put(f'/password/{self.user.pk}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_data(self):
        data = {}
        response = self.client.put(f'/password/{self.user.pk}/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_permission_denied(self):
        another_user =  CustomUserFactory.create()
        data = {'password': 'changed_password'}
        response = self.client.put(f'/password/{another_user.pk}/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


        