from django.test import TestCase
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser
from homework_app.factory import AssignmentFactory, AssignmentResultFactory, CustomUserFactory
from homework_app.utils import *
from homework_app.models import *
from datetime import date

class GenerateCsrfTokenTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_generate_csrf_token(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        csrf_token = generate_csrf_token(request)
        self.assertIsNotNone(csrf_token)


class GenerateEmailPasswordTestCase(TestCase):
    def test_generate_email_password(self):
        first_name = "Jonas"
        last_name = "Jonaitis"
        email, password = generate_email_password(first_name, last_name)

        self.assertTrue(email.endswith('@goose.lt'))
        self.assertTrue(len(password) >= 8)

        self.assertFalse(CustomUser.objects.filter(email=email).exists())


class GetCurrentSchoolYearTestCase(TestCase):
    def test_get_current_school_year(self):
        start_date, end_date = get_current_school_year()
        self.assertIsInstance(start_date, date)
        self.assertIsInstance(end_date, date)


class GetAssignmentStatusTestCase(TestCase):
    def setUp(self):
        self.assignment = AssignmentFactory.create()
        self.classs = self.assignment.classs
        self.student1 = CustomUserFactory.create(classs=self.classs)
        self.student2 = CustomUserFactory.create(classs=self.classs)
        self.student3 = CustomUserFactory.create(classs=self.classs)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student1)
    
    def test_get_completed_students_count(self):
        count = get_completed_students_count(self.assignment)
        self.assertEqual(count, 1)
    
    def test_get_assignment_status_average(self):
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student1)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student3)
        status = get_assignment_status(self.assignment)
        self.assertEqual(status, 'Average')
    
    def test_get_assignment_status_good(self):
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student1)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student2)
        AssignmentResultFactory.create(assignment=self.assignment, student=self.student3)
        status = get_assignment_status(self.assignment)
        self.assertEqual(status, 'Good')

    def test_get_assignment_status_bad(self):
        status = get_assignment_status(self.assignment)
        self.assertEqual(status, 'Bad')        